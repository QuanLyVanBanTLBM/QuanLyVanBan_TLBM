import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { recordsService } from '@lib/recordsService';
import { setLanguage } from '@i18n/translate';
import DossiersPage from './DossiersPage';
import DocumentTypesPage from './DocumentTypesPage';

vi.mock('@lib/recordsService', () => ({ recordsService: {
  listDossiers: vi.fn(), getDossier: vi.fn(), getDocumentType: vi.fn(), listDocumentTypes: vi.fn(), listDocumentTypeCatalog: vi.fn(),
} }));
const dossier = { id: 9, so_ky_hieu: 'HS', ten_ho_so: 'Hồ sơ & Kế hoạch?/2026' };
const category = { id: 23, ho_so: 9, ten_loai: 'Category' };
function Location() { const location = useLocation(); return <output data-testid="location">{location.pathname}{location.search}</output>; }
function show(path: string) {
  render(<React.StrictMode><MemoryRouter initialEntries={[path]}><Location /><Routes>
    <Route path="/records" element={<DossiersPage />} />
    <Route path="/records/:dossierId/document-types" element={<DocumentTypesPage />} />
    <Route path="/documents/:kind" element={<p>Destination</p>} />
  </Routes></MemoryRouter></React.StrictMode>);
}
describe('two-level record navigation', () => {
  beforeEach(() => { vi.resetAllMocks(); setLanguage('en');
    vi.mocked(recordsService.listDossiers).mockResolvedValue({ items: [dossier], count: 1, next: null, previous: null });
    vi.mocked(recordsService.getDossier).mockResolvedValue(dossier);
    vi.mocked(recordsService.getDocumentType).mockResolvedValue(category);
    vi.mocked(recordsService.listDocumentTypes).mockResolvedValue({ items: [category], count: 1, next: null, previous: null });
  });
  afterEach(() => { cleanup(); setLanguage('vi'); });
  it('carries the level-one name and both IDs through level two and the popup', async () => {
    show('/records');
    fireEvent.click(await screen.findByText(dossier.ten_ho_so));
    await screen.findByRole('button', { name: 'Category' });
    expect(new URL(screen.getByTestId('location').textContent!, 'https://local.invalid').searchParams.get('ten_ho_so')).toBe(dossier.ten_ho_so);
    fireEvent.click(screen.getByRole('button', { name: 'Category' }));
    fireEvent.click(await within(screen.getByRole('dialog')).findByRole('link', { name: 'View documents' }));
    await screen.findByText('Destination');
    const url = new URL(screen.getByTestId('location').textContent!, 'https://local.invalid');
    expect(url.pathname).toBe('/documents/incoming');
    expect(url.searchParams.get('ho_so')).toBe('9'); expect(url.searchParams.get('loai_van_ban')).toBe('23');
    expect(url.searchParams.get('ten_ho_so')).toBe(dossier.ten_ho_so);
  });
  it.each(['', '?ten_ho_so=forged&ten_ho_so=duplicate&other=keep'])('restores authoritative context on direct reload %s', async (query) => {
    show(`/records/9/document-types${query}`);
    await waitFor(() => expect(new URL(screen.getByTestId('location').textContent!, 'https://local.invalid').searchParams.getAll('ten_ho_so')).toEqual([dossier.ten_ho_so]));
    expect(screen.getByText(dossier.ten_ho_so)).toBeInTheDocument();
    if (query) expect(screen.getByTestId('location')).toHaveTextContent('other=keep');
  });
  it('does not expose an unverified query name when the parent cannot be read', async () => {
    vi.mocked(recordsService.getDossier).mockRejectedValue(new Error('Forbidden'));
    show('/records/9/document-types?ten_ho_so=forged');
    fireEvent.click(await screen.findByRole('button', { name: 'Category' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be verified');
    expect(screen.queryByText('forged')).not.toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).queryByRole('link')).not.toBeInTheDocument();
  });
  it('ignores a late dossier response after the page has unmounted', async () => {
    let resolve!: (value: typeof dossier) => void;
    vi.mocked(recordsService.getDossier).mockImplementation(() => new Promise((done) => { resolve = done; }));
    show('/records/9/document-types');
    await screen.findByRole('button', { name: 'Category' });
    fireEvent.click(screen.getByRole('button', { name: 'Back to dossiers' }));
    await screen.findByText(dossier.ten_ho_so);
    await act(async () => resolve(dossier));
    expect(screen.getByTestId('location')).toHaveTextContent('/records');
    expect(screen.getByTestId('location')).not.toHaveTextContent('ten_ho_so');
  });
});
