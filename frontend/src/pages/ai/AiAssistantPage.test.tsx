import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  askQuestion,
  getAISettings,
  getCategories,
  getDocuments,
  previewDocument,
  reclassifyDocument,
} from '../../api';
import { usePermissions } from '@lib/permissions';
import AiAssistantPage from './AiAssistantPage';

vi.mock('../../api', () => ({
  uploadDocumentAsync: vi.fn(),
  getUploadProgress: vi.fn(),
  askQuestion: vi.fn(),
  getDocuments: vi.fn(),
  getCategories: vi.fn(),
  getDocumentFile: vi.fn(),
  deleteDocuments: vi.fn(),
  deleteDocument: vi.fn(),
  previewDocument: vi.fn(),
  reclassifyDocument: vi.fn(),
  getAISettings: vi.fn(),
  updateAISettings: vi.fn(),
}));

vi.mock('@lib/permissions', () => ({
  usePermissions: vi.fn(),
}));

vi.mock('@i18n/translate', () => ({
  t: (key: string, params?: Record<string, unknown>) =>
    params ? `${key}:${JSON.stringify(params)}` : key,
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}:${JSON.stringify(params)}` : key,
    currentLang: 'vi',
  }),
}));

const mockedAskQuestion = vi.mocked(askQuestion);
const mockedGetDocuments = vi.mocked(getDocuments);
const mockedGetCategories = vi.mocked(getCategories);
const mockedGetAISettings = vi.mocked(getAISettings);
const mockedPreviewDocument = vi.mocked(previewDocument);
const mockedReclassifyDocument = vi.mocked(reclassifyDocument);
const mockedUsePermissions = vi.mocked(usePermissions);

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="location-probe">{`${loc.pathname}${loc.search}`}</div>;
}

function renderAiPage(initialEntry = '/ai-assistant') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/ai-assistant" element={<AiAssistantPage />} />
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AiAssistantPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({ username: 'tester', fullName: 'Test Officer' })
    );
    Element.prototype.scrollIntoView = vi.fn();
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    mockedUsePermissions.mockReturnValue({
      loaded: true,
      can: (perm: string) => perm === 'use_aiassistant',
      isSuperuser: false,
      isSystemAdmin: false,
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof usePermissions>);

    mockedGetAISettings.mockResolvedValue({
      provider: 'openai',
      llm_model: 'gpt-6-luna',
      api_key_masked: 'sk-...abcd',
      model_options: { openai: { llm_models: ['gpt-6-luna'] } },
    });
    mockedGetCategories.mockResolvedValue({ categories: [] });
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'quy_trinh.pdf', category: 'Quy trình' },
        { filename: 'sub_item.docx', category: 'Folder / folder1' },
      ],
    });
    mockedAskQuestion.mockResolvedValue({
      answer: 'Câu trả lời hợp lệ',
      sources: [],
    });
  });

  it('sends empty history on first turn and excludes current user message on subsequent turns', async () => {
    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Câu hỏi đầu tiên?' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    await waitFor(() =>
      expect(mockedAskQuestion).toHaveBeenNthCalledWith(
        1,
        'Câu hỏi đầu tiên?',
        [],
        null,
        null,
        'vi',
        null
      )
    );

    await screen.findByText('Câu trả lời hợp lệ', { selector: 'p' });

    fireEvent.change(textarea, { target: { value: 'Câu hỏi thứ hai?' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    await waitFor(() =>
      expect(mockedAskQuestion).toHaveBeenNthCalledWith(
        2,
        'Câu hỏi thứ hai?',
        [
          { role: 'user', content: 'Câu hỏi đầu tiên?' },
          { role: 'assistant', content: 'Câu trả lời hợp lệ' },
        ],
        null,
        null,
        'vi',
        null
      )
    );
  });

  it('hides delete and reclassify controls from non-admin users, shows them to admins, and never renders AI settings button', async () => {
    const { unmount } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    expect(await screen.findByText('quy_trinh.pdf')).toBeInTheDocument();
    expect(screen.getByText('folder1')).toBeInTheDocument();
    expect(screen.queryByTitle('aiAssistant.deleteDoc')).not.toBeInTheDocument();
    expect(screen.queryByTitle('aiAssistant.inline.reclassifyDoc')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'aiAssistant.inline.aiSettings' })).not.toBeInTheDocument();

    unmount();

    mockedUsePermissions.mockReturnValue({
      loaded: true,
      can: (perm: string) => perm === 'use_aiassistant',
      isSuperuser: true,
      isSystemAdmin: true,
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof usePermissions>);
    mockedReclassifyDocument.mockResolvedValue({ category: 'Hành chính' });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    const deleteBtns = await screen.findAllByTitle('aiAssistant.deleteDoc');
    expect(deleteBtns.length).toBeGreaterThan(0);
    expect(screen.getAllByTitle('aiAssistant.inline.reclassifyDoc').length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'aiAssistant.inline.aiSettings' })).not.toBeInTheDocument();
  });

  it('deduplicates SQL citations, navigates with ?detail=id, and skips preview on business_spec', async () => {
    mockedAskQuestion.mockResolvedValue({
      answer: 'Kết quả tra cứu',
      sources: [
        { file_name: 'VB-99', source_type: 'vanbanden', source_id: 99, page: 1 },
        { file_name: 'VB-99', source_type: 'vanbanden', source_id: 99, page: 2 },
        { file_name: 'Nghiệp vụ Văn bản', source_type: 'business_spec', source_id: 'branch-02-documents' },
      ],
    });

    const { unmount } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Tìm VB-99' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    await screen.findByText('Kết quả tra cứu', { selector: 'p' });
    expect(screen.queryByTitle('aiAssistant.viewDocument: VB-99')).not.toBeInTheDocument();

    // Kiểm tra nút mở rộng / thu nhỏ nguồn trích dẫn (mặc định đóng)
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));
    const sqlButtons = await screen.findAllByTitle('aiAssistant.viewDocument: VB-99');
    expect(sqlButtons).toHaveLength(1);

    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.toggleCitationsCollapse' }));
    expect(screen.queryByTitle('aiAssistant.viewDocument: VB-99')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));
    expect(screen.getByTitle('aiAssistant.viewDocument: VB-99')).toBeInTheDocument();

    fireEvent.click(screen.getByTitle('aiAssistant.viewDocument: Nghiệp vụ Văn bản'));
    expect(mockedPreviewDocument).not.toHaveBeenCalled();
    expect(await screen.findByTestId('location-probe')).toHaveTextContent('/documents/incoming');

    unmount();
    localStorage.clear();
    localStorage.setItem(
      'tlbm_session',
      JSON.stringify({ username: 'tester2', fullName: 'Test Officer 2' })
    );
    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());
    const textarea2 = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea2, { target: { value: 'Tìm VB-99' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));
    fireEvent.click(await screen.findByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));
    fireEvent.click(await screen.findByTitle('aiAssistant.viewDocument: VB-99'));
    expect(await screen.findByTestId('location-probe')).toHaveTextContent('/documents/incoming?detail=99');
  });

  it('clears targetDocument on New Chat and renders inline Retry on API failure', async () => {
    mockedAskQuestion
      .mockRejectedValueOnce(new Error('Network down'))
      .mockResolvedValueOnce({ answer: 'Đã khôi phục câu trả lời', sources: [] });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    await screen.findByText('quy_trinh.pdf');
    fireEvent.click(screen.getAllByTitle('aiAssistant.inline.targetThisDocumentForQ')[0]);
    expect(screen.getByText(/aiAssistant\.inline\.targetedCount/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.newChat/ }));
    expect(screen.queryByText(/aiAssistant\.inline\.targetedCount/)).not.toBeInTheDocument();

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Hỏi thử nghiệm' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    const retryBtn = await screen.findByRole('button', { name: 'aiAssistant.inline.retrySend' });
    fireEvent.click(retryBtn);

    expect(await screen.findByText('Đã khôi phục câu trả lời', { selector: 'p' })).toBeInTheDocument();
  });

  it('allows pinning up to 5 documents simultaneously and blocks the 6th', async () => {
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'doc1.pdf', category: 'folder1', size: 100, chunk_count: 1 },
        { filename: 'doc2.pdf', category: 'folder1', size: 100, chunk_count: 1 },
        { filename: 'doc3.pdf', category: 'folder1', size: 100, chunk_count: 1 },
        { filename: 'doc4.pdf', category: 'folder1', size: 100, chunk_count: 1 },
        { filename: 'doc5.pdf', category: 'folder1', size: 100, chunk_count: 1 },
        { filename: 'doc6.pdf', category: 'folder1', size: 100, chunk_count: 1 },
      ],
    });
    mockedAskQuestion.mockResolvedValue({ answer: 'Đã đối chiếu 5 tài liệu', sources: [] });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    await screen.findByText('doc1.pdf');

    const pinButtons = screen.getAllByTitle('aiAssistant.inline.targetThisDocumentForQ');
    expect(pinButtons).toHaveLength(6);

    for (let i = 0; i < 6; i += 1) {
      fireEvent.click(pinButtons[i]);
    }

    expect(await screen.findByText(/aiAssistant\.inline\.maxPinnedDocuments/)).toBeInTheDocument();

    const textarea = screen.getByRole('textbox', { name: /aiAssistant\.inline\.askAboutMultipleValue/ });
    fireEvent.change(textarea, { target: { value: 'So sánh 5 văn bản' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    await waitFor(() =>
      expect(mockedAskQuestion).toHaveBeenCalledWith(
        'So sánh 5 văn bản',
        [],
        null,
        null,
        'vi',
        ['doc1.pdf', 'doc2.pdf', 'doc3.pdf', 'doc4.pdf', 'doc5.pdf']
      )
    );
  });

  it('separates uploaded documents from managed PostgreSQL documents (view & pin only)', async () => {
    mockedUsePermissions.mockReturnValue({
      loaded: true,
      can: (perm: string) => perm === 'use_aiassistant',
      isSuperuser: true,
      isSystemAdmin: true,
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof usePermissions>);
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'uploaded_guide.pdf', category: 'Hướng dẫn', size: 120 },
        {
          filename: '12/CV-UBND — Công văn mẫu',
          category: 'Văn bản đến',
          is_managed: true,
          source_type: 'vanbanden',
          source_id: 12,
        },
      ],
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    expect(await screen.findByText('aiAssistant.inline.uploadedDocsSection')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.inline.systemDocsSection')).toBeInTheDocument();
    expect(screen.getByText('uploaded_guide.pdf')).toBeInTheDocument();
    expect(screen.getByText('12/CV-UBND — Công văn mẫu')).toBeInTheDocument();

    // Chỉ tài liệu tải lên mới có nút xóa/phân loại/xem trước; tài liệu hệ thống chỉ có nút ghim
    expect(screen.getAllByTitle('aiAssistant.deleteDoc')).toHaveLength(1);
    expect(screen.getAllByTitle('aiAssistant.preview')).toHaveLength(1);
    expect(screen.getAllByTitle('aiAssistant.inline.targetThisDocumentForQ')).toHaveLength(2);
  });

  it('moves soft-fallback note to the bottom and excludes it from clipboard copy', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    mockedAskQuestion.mockResolvedValue({
      answer:
        '(Không có tài liệu cụ thể được ghim. Phản hồi dựa trên nghiệp vụ hành chính tổng hợp)\n\nNội dung hướng dẫn chính.',
      sources: [],
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Hỏi quy trình' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    const bodyPara = await screen.findByText('Nội dung hướng dẫn chính.', { selector: 'p' });
    const noteEl = screen.getByText('(Không có tài liệu cụ thể được ghim. Phản hồi dựa trên nghiệp vụ hành chính tổng hợp)');
    expect(noteEl).toHaveClass('ai-soft-fallback-note');
    expect(bodyPara.compareDocumentPosition(noteEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const copyButtons = screen.getAllByTitle('aiAssistant.copy');
    fireEvent.click(copyButtons[copyButtons.length - 1]);
    expect(writeText).toHaveBeenCalledWith('Nội dung hướng dẫn chính.');
  });

  it('filters sidebar documents by server repository vs AI uploaded source dropdown', async () => {
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'uploaded_guide.pdf', category: 'Hành chính', is_managed: false },
        { filename: '01/QD — Quy chế máy chủ', category: 'Văn bản đến', is_managed: true },
      ],
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    await waitFor(() => expect(screen.getByText('uploaded_guide.pdf')).toBeInTheDocument());
    expect(screen.getByText('01/QD — Quy chế máy chủ')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.inline.systemDocsSection')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.inline.uploadedDocsSection')).toBeInTheDocument();

    const trigger = screen.getByRole('button', { name: 'aiAssistant.inline.filterDocSource' });
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole('option', { name: /aiAssistant\.inline\.serverDocSource/ }));

    expect(screen.queryByText('uploaded_guide.pdf')).not.toBeInTheDocument();
    expect(screen.getByText('01/QD — Quy chế máy chủ')).toBeInTheDocument();
    expect(screen.queryByText('aiAssistant.inline.systemDocsSection')).not.toBeInTheDocument();

    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole('option', { name: /aiAssistant\.inline\.aiUploadedDocSource/ }));

    expect(screen.getByText('uploaded_guide.pdf')).toBeInTheDocument();
    expect(screen.queryByText('01/QD — Quy chế máy chủ')).not.toBeInTheDocument();
    expect(screen.queryByText('aiAssistant.inline.uploadedDocsSection')).not.toBeInTheDocument();
  });
});
