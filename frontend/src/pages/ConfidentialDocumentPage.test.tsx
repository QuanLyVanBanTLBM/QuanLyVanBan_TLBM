import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ConfidentialDocumentPage from './ConfidentialDocumentPage';
import apiClient from '@lib/apiClient';
import * as crypto from '@lib/confidential/crypto';
import { setLanguage } from '@i18n/translate';

vi.mock('@lib/apiClient', () => ({ default: { get: vi.fn(), post: vi.fn(), put: vi.fn() }, ApiError: class extends Error {} }));
vi.mock('@lib/confidential/crypto', () => ({ createIdentity: vi.fn(), unlock: vi.fn(), recover: vi.fn(), seal: vi.fn(), open: vi.fn(), fingerprint: vi.fn(), b64: vi.fn(), unb64: vi.fn(), MAX_FILE_BYTES: 10 * 1024 * 1024 }));
const own = { id: 1, user_id: 1, username: 'sender', fingerprint: 'a'.repeat(64), encryption_public_key: '', signing_public_key: '', vault: {} };
const contact = { ...own, id: 2, user_id: 2, username: 'recipient', fingerprint: 'b'.repeat(64) };
const snapshot = { id: 'doc-id', author_id: 1, author_username: 'sender', created_at: '2026-10-12T00:00:00Z' };

describe('confidential page acceptance', () => {
  beforeEach(() => {
    vi.resetAllMocks(); localStorage.clear(); setLanguage('en');
    vi.mocked(apiClient.get).mockImplementation(async endpoint => {
      if (endpoint.includes('/key/')) return { user_id: 1, can_create: true, key: own };
      if (endpoint.includes('/directory/')) return [own, contact];
      if (endpoint.endsWith('/doc-id/')) return { ...snapshot, ciphertext: 'cipher-only', nonce: 'nonce', signature: 'sig', envelopes: [] };
      return { count: 1, results: [snapshot] };
    });
    vi.mocked(crypto.unlock).mockResolvedValue({ record: own } as never);
    vi.mocked(crypto.fingerprint).mockResolvedValue(contact.fingerprint);
    vi.mocked(crypto.open).mockResolvedValue({ number: 'SECRET-NUMBER', title: 'SECRET-TITLE', note: 'SECRET-NOTE', files: [] });
  });
  async function unlockPage() {
    render(<ConfidentialDocumentPage />);
    await screen.findByRole('button', { name: 'Unlock' });
    fireEvent.change(screen.getByLabelText(/Separate unlock passphrase/), { target: { value: 'separate long passphrase' } });
    fireEvent.click(screen.getByRole('button', { name: 'Unlock' }));
    await screen.findByRole('button', { name: 'Lock now' });
  }
  it('shows only opaque summaries while locked, and never auto-verifies a contact', async () => {
    render(<ConfidentialDocumentPage />);
    expect(await screen.findByRole('button', { name: 'Open document' })).toBeDisabled();
    expect(screen.queryByText('SECRET-TITLE')).not.toBeInTheDocument();
    expect(crypto.open).not.toHaveBeenCalled();
    expect(localStorage.getItem('confidential-pins-1')).toBeNull();
  });
  it('requires independent fingerprint verification and explicit selection', async () => {
    await unlockPage();
    const checkbox = screen.getByRole('checkbox', { name: 'Select recipient' });
    expect(checkbox).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Fingerprint received through an independent channel'), { target: { value: contact.fingerprint } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm fingerprint' }));
    await waitFor(() => expect(checkbox).not.toBeDisabled());
    expect(localStorage.getItem('confidential-pins-1')).toContain(contact.fingerprint);
    expect(localStorage.getItem('confidential-pins-1')).not.toContain('passphrase');
  });
  it('clears decrypted content and key on lock or account change', async () => {
    await unlockPage();
    fireEvent.click(screen.getByRole('button', { name: 'Open document' }));
    expect(await screen.findByText('SECRET-TITLE')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Lock now' }));
    expect(screen.queryByText('SECRET-TITLE')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open document' })).toBeDisabled();
    act(() => window.dispatchEvent(new Event('tlbm_auth_changed')));
    expect(screen.queryByText('doc-id')).not.toBeInTheDocument();
  });
  it('does not render a decryption that finishes after locking', async () => {
    let finish!: (value: never) => void;
    vi.mocked(crypto.open).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    await unlockPage();
    fireEvent.click(screen.getByRole('button', { name: 'Open document' }));
    await waitFor(() => expect(crypto.open).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: 'Lock now' }));
    await act(async () => finish({ number: '', title: 'LATE-SECRET', note: '', files: [] } as never));
    expect(screen.queryByText('LATE-SECRET')).not.toBeInTheDocument();
  });
  it('shows an error for a wrong passphrase without unlocking', async () => {
    vi.mocked(crypto.unlock).mockRejectedValue(new Error('decrypt failed'));
    render(<ConfidentialDocumentPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Unlock' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Operation failed');
    expect(screen.queryByRole('button', { name: 'Lock now' })).not.toBeInTheDocument();
  });
  it('requires recovery acknowledgement before registering a new key', async () => {
    vi.mocked(apiClient.get).mockImplementation(async endpoint => endpoint.includes('/key/') ? { user_id: 1, can_create: true, key: null } : endpoint.includes('/directory/') ? [] : { count: 0, results: [] });
    vi.mocked(crypto.createIdentity).mockResolvedValue({ record: own, recoveryCode: 'PRIVATE-RECOVERY', registration: {} } as never);
    render(<ConfidentialDocumentPage />);
    fireEvent.click(await screen.findByRole('button', { name: 'Create personal key' }));
    expect(await screen.findByText('PRIVATE-RECOVERY')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Register key' })).toBeDisabled();
    expect(apiClient.post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('checkbox', { name: 'I have stored the recovery code securely' }));
    expect(screen.getByRole('button', { name: 'Register key' })).not.toBeDisabled();
  });
  it('locks when the tab becomes hidden', async () => {
    await unlockPage();
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
    act(() => document.dispatchEvent(new Event('visibilitychange')));
    expect(screen.getByRole('button', { name: 'Open document' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Lock now' })).not.toBeInTheDocument();
    hidden.mockRestore();
  });
  it('locks automatically after ten minutes', async () => {
    await unlockPage();
    vi.useFakeTimers();
    try {
      // Unlock happened with real timers; explicitly lock and re-unlock to schedule the fake clock.
      fireEvent.click(screen.getByRole('button', { name: 'Lock now' }));
      await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Unlock' })); });
      act(() => vi.advanceTimersByTime(10 * 60 * 1000));
      expect(screen.getByRole('button', { name: 'Open document' })).toBeDisabled();
    } finally { vi.useRealTimers(); }
  });
});
