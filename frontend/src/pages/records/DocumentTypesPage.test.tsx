import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { recordsService } from '@lib/recordsService';
import { setLanguage } from '@i18n/translate';
import { ApiError } from '@lib/apiClient';
import DocumentTypesPage from './DocumentTypesPage';

vi.mock('@lib/recordsService', () => ({ recordsService: {
  getDossier: vi.fn(), getDocumentType: vi.fn(), listDocumentTypes: vi.fn(), listDocumentTypeCatalog: vi.fn(),
  listDossiers: vi.fn(), createDocumentType: vi.fn(), updateDocumentType: vi.fn(), deleteDocumentType: vi.fn(),
} }));
const categories = { items: [{ id: 23, ho_so: 9, ten_ho_so: 'Parent', ten_loai: 'Category A' }], count: 1, next: null, previous: null };
function Destination() { const location = useLocation(); return <div data-testid="destination">{location.pathname}{location.search}</div>; }
async function show(path = '/records/document-types') {
  await act(async () => { render(<MemoryRouter initialEntries={[path]}><Routes>
    <Route path="/records/document-types" element={<DocumentTypesPage />} />
    <Route path="/records/:dossierId/document-types" element={<DocumentTypesPage />} />
    <Route path="/documents/:kind" element={<Destination />} />
  </Routes></MemoryRouter>); });
}
describe('DocumentTypesPage shared-list handoff', () => {
  beforeEach(() => { vi.clearAllMocks(); setLanguage('en');
    vi.mocked(recordsService.listDocumentTypeCatalog).mockResolvedValue(categories);
    vi.mocked(recordsService.listDocumentTypes).mockResolvedValue(categories);
    vi.mocked(recordsService.getDossier).mockResolvedValue({ id: 9, ten_ho_so: 'Parent', so_ky_hieu: 'HS' });
    vi.mocked(recordsService.getDocumentType).mockResolvedValue(categories.items[0]);
    vi.mocked(recordsService.listDossiers).mockResolvedValue({ items: [{ id: 9, ten_ho_so: 'Parent', so_ky_hieu: 'HS' }], count: 1, next: null, previous: null });
    vi.mocked(recordsService.createDocumentType).mockResolvedValue(categories.items[0]);
    vi.mocked(recordsService.updateDocumentType).mockResolvedValue(categories.items[0]);
    vi.mocked(recordsService.deleteDocumentType).mockResolvedValue(undefined);
  });
  afterEach(() => { cleanup(); setLanguage('vi'); });
  it('waits for filter submission before changing the year in a dossier', async () => {
    await show('/records/9/document-types');
    const request = vi.mocked(recordsService.listDocumentTypes);
    request.mockClear();
    const year = String(new Date().getFullYear() - 1);
    await act(async () => {
      fireEvent.change(screen.getByRole('combobox', { name: 'Filter by year' }), { target: { value: year } });
    });
    expect(request).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Category A' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));
    await waitFor(() => expect(request).toHaveBeenCalledWith('9', expect.objectContaining({ year, page: 1 })));
    request.mockClear();
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by year' }), { target: { value: '' } });
    expect(request).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));
    await waitFor(() => expect(request).toHaveBeenCalledWith('9', expect.objectContaining({ year: '', page: 1 })));
  });

  it('shows an independent catalog and forwards the clicked category to incoming', async () => {
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Category A' }));
    expect(screen.getByRole('dialog', { name: 'Choose document list' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Restricted documents only' })).toBeInTheDocument();
    fireEvent.click(await within(screen.getByRole('dialog')).findByRole('link', { name: 'View documents' }));
    expect(await screen.findByTestId('destination')).toHaveTextContent('/documents/incoming?ho_so=9&ten_ho_so=Parent&loai_van_ban=23&pham_vi=NOI_BO');
    expect(recordsService.listDocumentTypes).not.toHaveBeenCalled();
  });
  it('keeps outgoing confidential documents in the same kind with HAN_CHE scope', async () => {
    await show('/records/9/document-types');
    fireEvent.click(await screen.findByRole('button', { name: 'Category A' }));
    fireEvent.change(within(screen.getByRole('dialog')).getByRole('combobox'), { target: { value: 'DI' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(await within(screen.getByRole('dialog')).findByRole('link', { name: 'View documents' }));
    expect(await screen.findByTestId('destination')).toHaveTextContent('/documents/outgoing?ho_so=9&ten_ho_so=Parent&loai_van_ban=23&pham_vi=HAN_CHE');
    expect(recordsService.listDocumentTypeCatalog).not.toHaveBeenCalled();
  });
  it('allows Escape to close selection without opening a private list', async () => {
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Category A' }));
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.queryByTestId('destination')).not.toBeInTheDocument();
  });

  it('requires a name before creating within the current dossier', async () => {
    await show('/records/9/document-types');
    fireEvent.click(await screen.findByRole('button', { name: 'Add document type' }));
    fireEvent.change(screen.getByLabelText(/Document type name/), { target: { value: '   ' } });
    fireEvent.submit(screen.getByRole('dialog'));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a document type name.');
    expect(recordsService.createDocumentType).not.toHaveBeenCalled();
  });

  it('creates a trimmed type with the selected dossier and reloads the catalog', async () => {
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Add document type' }));
    await waitFor(() => expect(screen.getByRole('combobox', { name: /Dossier/ })).toBeEnabled());
    fireEvent.change(screen.getByLabelText(/Document type name/), { target: { value: '  New category  ' } });
    fireEvent.submit(screen.getByRole('dialog'));
    expect(screen.getByRole('alert')).toHaveTextContent('Please choose a dossier');
    expect(recordsService.createDocumentType).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole('combobox', { name: /Dossier/ }), { target: { value: '9' } });
    fireEvent.submit(screen.getByRole('dialog'));
    await waitFor(() => expect(recordsService.createDocumentType).toHaveBeenCalledWith('9', { ten_loai: 'New category', ngay_lap: null, ghi_chu: '' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Document type added successfully.');
    await waitFor(() => expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('loads every dossier page for the create selector', async () => {
    vi.mocked(recordsService.listDossiers)
      .mockResolvedValueOnce({ items: [{ id: 9, ten_ho_so: 'Parent', so_ky_hieu: 'HS' }], count: 2, next: '/api/records/dossiers/?page=2', previous: null })
      .mockResolvedValueOnce({ items: [{ id: 10, ten_ho_so: 'Other parent', so_ky_hieu: 'HS-2' }], count: 2, next: null, previous: '/api/records/dossiers/' });
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Add document type' }));
    expect(await screen.findByRole('option', { name: /Other parent/ })).toBeInTheDocument();
    expect(recordsService.listDossiers).toHaveBeenNthCalledWith(2, { page: 2, pageSize: 100 });
  });

  it('edits without opening the document destination and retains input on validation errors', async () => {
    vi.mocked(recordsService.updateDocumentType).mockRejectedValueOnce(new ApiError(400, { ten_loai: ['Duplicate category.'] }));
    await show('/records/9/document-types');
    fireEvent.click(await screen.findByRole('button', { name: 'Edit Category A' }));
    expect(screen.queryByRole('dialog', { name: 'Choose document list' })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Document type name/)).toHaveValue('Category A');
    fireEvent.change(screen.getByLabelText(/Document type name/), { target: { value: 'Renamed category' } });
    fireEvent.submit(screen.getByRole('dialog'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Duplicate category.');
    expect(screen.getByLabelText(/Document type name/)).toHaveValue('Renamed category');
    fireEvent.submit(screen.getByRole('dialog'));
    expect(await screen.findByRole('status')).toHaveTextContent('Document type updated successfully.');
    expect(recordsService.updateDocumentType).toHaveBeenLastCalledWith(23, { ten_loai: 'Renamed category', ngay_lap: null, ghi_chu: '' });
  });

  it('cancels deletion without calling the API, then confirms and refreshes the list', async () => {
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Category A' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(recordsService.deleteDocumentType).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Delete Category A' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Document type deleted successfully.');
    expect(recordsService.deleteDocumentType).toHaveBeenCalledWith(23);
    await waitFor(() => expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(2));
  });

  it('keeps the row and confirmation when referenced documents block deletion', async () => {
    vi.mocked(recordsService.deleteDocumentType).mockRejectedValue(new ApiError(409, { detail: 'Documents still reference this type.' }));
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Category A' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Documents still reference this type.');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Category A' })).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('blocks double submission while saving and shows a permission failure', async () => {
    let rejectRequest!: (error: unknown) => void;
    vi.mocked(recordsService.createDocumentType).mockImplementationOnce(() => new Promise((_, reject) => { rejectRequest = reject; }));
    await show('/records/9/document-types');
    fireEvent.click(await screen.findByRole('button', { name: 'Add document type' }));
    fireEvent.change(screen.getByLabelText(/Document type name/), { target: { value: 'New category' } });
    fireEvent.submit(screen.getByRole('dialog'));
    fireEvent.submit(screen.getByRole('dialog'));
    expect(recordsService.createDocumentType).toHaveBeenCalledTimes(1);
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: 'Add new' })).toBeDisabled();
    expect(screen.getByLabelText(/Document type name/)).toBeDisabled();
    await act(async () => rejectRequest(new ApiError(403, { detail: 'Forbidden' })));
    expect(screen.getByRole('alert')).toHaveTextContent('You do not have permission');
    expect(screen.getByLabelText(/Document type name/)).toHaveValue('New category');
  });

  it('moves back when deleting the last row on a later page', async () => {
    vi.mocked(recordsService.listDocumentTypeCatalog).mockResolvedValue({ ...categories, count: 11 });
    await show();
    fireEvent.click(await screen.findByRole('button', { name: /Next/ }));
    await waitFor(() => expect(recordsService.listDocumentTypeCatalog).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Category A' }));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(recordsService.listDocumentTypeCatalog).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1 })));
  });

  it('allows editing after cancelling a create form while its dossiers are loading', async () => {
    vi.mocked(recordsService.listDossiers).mockImplementationOnce(() => new Promise(() => undefined));
    await show();
    fireEvent.click(await screen.findByRole('button', { name: 'Add document type' }));
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: 'Add new' })).toBeDisabled();
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    fireEvent.click(screen.getByRole('button', { name: 'Edit Category A' }));
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: 'Save changes' })).toBeEnabled();
  });

  it('debounces search input by 250ms and queries catalog', async () => {
    vi.useFakeTimers();
    await show();
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);

    const input = screen.getByPlaceholderText('Search by document category name...');
    fireEvent.change(input, { target: { value: 'Category' } });

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(200);
      await Promise.resolve();
    });

    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(2);
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: 'Category', page: 1 })
    );

    vi.useRealTimers();
  });

  it('does not enter loading state or initiate extra request when clearing search before debounce', async () => {
    vi.useFakeTimers();
    await show();
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);

    const input = screen.getByPlaceholderText('Search by document category name...');
    fireEvent.change(input, { target: { value: 'Cat' } });

    const clearBtn = screen.getByLabelText('Reset');
    act(() => {
      fireEvent.click(clearBtn);
    });

    expect(input).toHaveValue('');
    expect(screen.queryByLabelText('Loading document types')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Category A' })).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });

    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);
    expect(screen.queryByLabelText('Loading document types')).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it('does not enter loading state when typing only whitespace and clearing', async () => {
    vi.useFakeTimers();
    await show();
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);

    const input = screen.getByPlaceholderText('Search by document category name...');
    fireEvent.change(input, { target: { value: '   ' } });

    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);

    const clearBtn = screen.getByLabelText('Reset');
    act(() => {
      fireEvent.click(clearBtn);
    });

    expect(input).toHaveValue('');
    expect(screen.queryByLabelText('Loading document types')).not.toBeInTheDocument();
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('reloads with empty search and resets to page 1 when clearing active search', async () => {
    vi.useFakeTimers();
    await show();

    const input = screen.getByPlaceholderText('Search by document category name...');
    fireEvent.change(input, { target: { value: 'Category A' } });

    await act(async () => {
      vi.advanceTimersByTime(300);
      await Promise.resolve();
    });

    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(2);

    const clearBtn = screen.getByLabelText('Reset');
    await act(async () => {
      fireEvent.click(clearBtn);
      await Promise.resolve();
    });

    expect(input).toHaveValue('');
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenCalledTimes(3);
    expect(recordsService.listDocumentTypeCatalog).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: '', page: 1 })
    );
    expect(screen.queryByLabelText('Loading document types')).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});
