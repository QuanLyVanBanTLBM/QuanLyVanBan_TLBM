import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom';
import { apiClient } from '@lib/apiClient';
import { setLanguage } from '@i18n/translate';
import InboundDocumentPage from './InboundDocumentPage';
import OutboundDocumentPage from './OutboundDocumentPage';

vi.mock('@lib/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@lib/apiClient')>();
  const client = Object.assign(vi.fn(), { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() });
  return { ...actual, apiClient: client, default: client, downloadBlob: vi.fn() };
});

const dossierName = 'Hồ sơ & Kế hoạch?/2026';
const nextDossierName = 'Hồ sơ khác & phụ lục';
function contextUrl(direction: 'DEN' | 'DI', scope = 'HAN_CHE', parent = '9', name = dossierName) {
  return `/documents/${direction === 'DEN' ? 'incoming' : 'outgoing'}?${new URLSearchParams({
    ho_so: parent, ten_ho_so: name, loai_van_ban: '23', pham_vi: scope,
  })}`;
}
function LocationProbe({ direction }: { direction: 'DEN' | 'DI' }) {
  const location = useLocation();
  const navigate = useNavigate();
  return <>
    <output data-testid="location">{location.pathname}{location.search}</output>
    <button onClick={() => navigate(contextUrl(direction, 'HAN_CHE', '10', nextDossierName))}>Next context</button>
  </>;
}
function query() { return new URL(screen.getByTestId('location').textContent!, 'https://local.invalid').searchParams; }
function listRequests() {
  return vi.mocked(apiClient.get).mock.calls.map(([path]) => new URL(String(path), 'https://local.invalid'))
    .filter((url) => url.pathname === '/api/documents/' && url.searchParams.get('page_size') !== '1000');
}

describe.each([{ direction: 'DEN' as const, Page: InboundDocumentPage }, { direction: 'DI' as const, Page: OutboundDocumentPage }])(
  'document record context: $direction', ({ direction, Page }) => {
    beforeEach(() => {
      vi.resetAllMocks(); setLanguage('vi');
      vi.mocked(apiClient.get).mockImplementation(async (path) => String(path).includes('/years/') ? [] : { results: [], count: 0 });
    });
    afterEach(() => { cleanup(); setLanguage('vi'); });
    function show(path = contextUrl(direction)) {
      render(<React.StrictMode><MemoryRouter initialEntries={[path]}><LocationProbe direction={direction} /><Page /></MemoryRouter></React.StrictMode>);
    }
    async function loaded() { await waitFor(() => expect(listRequests().length).toBeGreaterThan(0)); }

    it.each(['NOI_BO', 'HAN_CHE'])('sends all IDs and %s scope from the first list request', async (scope) => {
      show(contextUrl(direction, scope)); await loaded();
      for (const request of listRequests()) {
        expect(request.searchParams.get('loai')).toBe(direction);
        expect(request.searchParams.get('ho_so')).toBe('9');
        expect(request.searchParams.get('loai_van_ban')).toBe('23');
        expect(request.searchParams.get('pham_vi')).toBe(scope);
        expect(request.searchParams.has('ten_ho_so')).toBe(false);
      }
    });
    it('retains the encoded name when changing scope', async () => {
      show(); await loaded(); fireEvent.click(screen.getByTitle('Xóa bộ lọc phạm vi'));
      await waitFor(() => expect(query().get('pham_vi')).toBe('NOI_BO'));
      expect(query().get('ho_so')).toBe('9'); expect(query().get('ten_ho_so')).toBe(dossierName);
      expect(query().get('loai_van_ban')).toBe('23');
    });
    it('retains dossier context when clearing only the category', async () => {
      show(); await loaded(); fireEvent.click(screen.getByTitle('Xóa bộ lọc loại văn bản'));
      await waitFor(() => expect(query().has('loai_van_ban')).toBe(false));
      expect(query().get('ho_so')).toBe('9'); expect(query().get('ten_ho_so')).toBe(dossierName);
    });
    it('drops the old name when clearing the dossier', async () => {
      show(); await loaded();
      fireEvent.change(screen.getByTitle('Chọn danh mục hồ sơ để lọc văn bản'), { target: { value: '' } });
      await waitFor(() => expect(query().has('ho_so')).toBe(false));
      expect(query().has('ten_ho_so')).toBe(false); expect(query().has('loai_van_ban')).toBe(false);
    });
    it('does not reuse the old name for a different dossier filter', async () => {
      show(); await loaded();
      const select = screen.getByTitle('Chọn danh mục hồ sơ để lọc văn bản') as HTMLSelectElement;
      const other = Array.from(select.options).find((option) => option.value)!.value;
      fireEvent.change(select, { target: { value: other } });
      await waitFor(() => expect(query().get('ho_so')).toBe(other));
      expect(query().has('ten_ho_so')).toBe(false);
    });
    it('updates both ID and name after navigation within the same mounted page', async () => {
      show(); await loaded(); fireEvent.click(screen.getByRole('button', { name: 'Next context' }));
      await waitFor(() => expect(listRequests().at(-1)!.searchParams.get('ho_so')).toBe('10'));
      fireEvent.click(screen.getByTitle('Xóa bộ lọc phạm vi'));
      await waitFor(() => expect(query().get('pham_vi')).toBe('NOI_BO'));
      expect(query().get('ho_so')).toBe('10'); expect(query().get('ten_ho_so')).toBe(nextDossierName);
    });
    it('does not keep a name without a selected dossier ID', async () => {
      show(`/documents/${direction === 'DEN' ? 'incoming' : 'outgoing'}?ten_ho_so=orphan&pham_vi=HAN_CHE`);
      await loaded(); fireEvent.click(screen.getByTitle('Xóa bộ lọc phạm vi'));
      await waitFor(() => expect(query().get('pham_vi')).toBe('NOI_BO'));
      expect(query().has('ten_ho_so')).toBe(false);
    });
  },
);
