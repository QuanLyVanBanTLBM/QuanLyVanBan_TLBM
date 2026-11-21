import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  askQuestion,
  askQuestionStream,
  getAISettings,
  getAISyncStatus,
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
  askQuestionStream: vi.fn(),
  getDocuments: vi.fn(),
  getCategories: vi.fn(),
  getDocumentFile: vi.fn(),
  deleteDocuments: vi.fn(),
  deleteDocument: vi.fn(),
  previewDocument: vi.fn(),
  reclassifyDocument: vi.fn(),
  getAISettings: vi.fn(),
  updateAISettings: vi.fn(),
  getAISyncStatus: vi.fn(),
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
const mockedAskQuestionStream = vi.mocked(askQuestionStream);
const mockedGetDocuments = vi.mocked(getDocuments);
const mockedGetCategories = vi.mocked(getCategories);
const mockedGetAISettings = vi.mocked(getAISettings);
const mockedGetAISyncStatus = vi.mocked(getAISyncStatus);
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
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1280,
    });
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
    mockedGetAISyncStatus.mockResolvedValue({
      configured: true,
      schema: { status: 'ok' },
      sql_eligible: { total: 4 },
      sql_indexed: { total: 4 },
      sql_pending_extraction: 0,
      kb_registered: 2,
      kb_indexed: 2,
      kb_orphans: 0,
      kb_orphan_names: [],
      total_chunks: 18,
      schedule: {
        enabled: true,
        mode: 'event_and_scheduled',
        task: 'sync_all_ai_documents',
        cron: '0 2 * * *',
        hour: 2,
        minute: 0,
        time: '02:00',
        timezone: 'Asia/Ho_Chi_Minh',
        next_run_at: '2026-11-20T02:00:00+07:00',
      },
    });
    mockedGetCategories.mockResolvedValue({ categories: [] });
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'quy_trinh.pdf', category: 'Quy trình' },
        { filename: 'sub_item.docx', category: 'Folder / folder1' },
      ],
    });
    mockedAskQuestionStream.mockRejectedValue(new Error('stream disabled in fallback tests'));
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
    const docsTabBtn = screen.getByRole('button', { name: /aiAssistant\.tabDocs/ });
    fireEvent.click(docsTabBtn);
    await waitFor(() => expect(screen.getByText('uploaded_guide.pdf')).toBeInTheDocument());
    expect(screen.getByText('01/QD — Quy chế máy chủ')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.inline.systemDocsSection')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.inline.uploadedDocsSection')).toBeInTheDocument();

    fireEvent.click(docsTabBtn);
    fireEvent.click(screen.getByRole('option', { name: /aiAssistant\.inline\.serverDocSource/ }));

    expect(screen.queryByText('uploaded_guide.pdf')).not.toBeInTheDocument();
    expect(screen.getByText('01/QD — Quy chế máy chủ')).toBeInTheDocument();
    expect(screen.queryByText('aiAssistant.inline.systemDocsSection')).not.toBeInTheDocument();

    fireEvent.click(docsTabBtn);
    fireEvent.click(screen.getByRole('option', { name: /aiAssistant\.inline\.aiUploadedDocSource/ }));

    expect(screen.getByText('uploaded_guide.pdf')).toBeInTheDocument();
    expect(screen.queryByText('01/QD — Quy chế máy chủ')).not.toBeInTheDocument();
    expect(screen.queryByText('aiAssistant.inline.uploadedDocsSection')).not.toBeInTheDocument();
  });

  it('renders mobile sidebar open button below 860px and opens drawer dialog on click', async () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 390,
    });
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const openBtn = screen.getByRole('button', { name: 'aiAssistant.expandSidebar' });
    expect(openBtn).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(openBtn);
    expect(await screen.findByRole('dialog', { name: 'aiAssistant.inline.chatHistory' })).toBeInTheDocument();
  });

  it('reflects configured and has_api_key status on the AI status badge', async () => {
    mockedGetAISettings.mockResolvedValueOnce({ provider: 'openai', llm_model: 'gpt-6-luna', configured: false });
    const { unmount } = renderAiPage();
    expect(await screen.findByText('aiAssistant.statusDisconnected')).toBeInTheDocument();
    unmount();

    mockedGetAISettings.mockResolvedValueOnce({ provider: 'openai', llm_model: 'gpt-6-luna', has_api_key: false });
    const second = renderAiPage();
    expect(await screen.findByText('aiAssistant.statusDisconnected')).toBeInTheDocument();
    second.unmount();

    mockedGetAISettings.mockResolvedValueOnce({ provider: 'openai', llm_model: 'gpt-6-luna', configured: true });
    renderAiPage();
    expect(await screen.findByText('aiAssistant.statusActive')).toBeInTheDocument();
  });

  it('syncs Kho tài liệu tab badge and chat history count badge with search filters', async () => {
    const { container } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    // Create a second session so we have 2 sessions before filtering
    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.newChat/ }));
    const sessionCountBadge = container.querySelector('.session-count-badge');
    expect(sessionCountBadge).toHaveTextContent('2');

    const sessionSearch = screen.getByPlaceholderText('aiAssistant.searchSessionsPlaceholder');
    fireEvent.change(sessionSearch, { target: { value: 'khong_khop_phien_nao' } });
    expect(sessionCountBadge).toHaveTextContent('0');

    const docsTabBtn = screen.getByRole('button', { name: /aiAssistant\.tabDocs/ });
    fireEvent.click(docsTabBtn);
    expect(docsTabBtn.querySelector('.sidebar-tab-badge')).toHaveTextContent('2');

    const docSearch = screen.getByPlaceholderText('aiAssistant.searchDocsPlaceholder');
    fireEvent.change(docSearch, { target: { value: 'quy_trinh' } });
    expect(docsTabBtn.querySelector('.sidebar-tab-badge')).toHaveTextContent('1');
  });

  it('hides thinking card on first delta, shows Stop button while streaming, and aborts cleanly', async () => {
    let resolveStream!: () => void;
    let capturedSignal: AbortSignal | null | undefined;
    mockedAskQuestionStream.mockImplementation(
      (_question: string, options?: { signal?: AbortSignal | null; onDelta?: (d: string, full: string) => void }) => {
        capturedSignal = options?.signal;
        return new Promise((resolve, reject) => {
          resolveStream = () => resolve({ answer: 'Xong', sources: [] });
          options?.signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
          setTimeout(() => {
            options?.onDelta?.('Đang stream...', 'Đang stream...');
          }, 0);
        });
      }
    );

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Test streaming stop' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    // Thinking indicator is shown before first delta and Stop button replaces Send
    expect(screen.getByText('aiAssistant.inline.aiAssistantIsSearchingThe')).toBeInTheDocument();
    const stopBtn = screen.getByRole('button', { name: 'aiAssistant.stop' });
    expect(stopBtn).toBeInTheDocument();

    // First delta arrives: thinking indicator hides, partial text appears, Stop button stays visible
    await screen.findByText('Đang stream...', { selector: 'p' });
    expect(screen.queryByText('aiAssistant.inline.aiAssistantIsSearchingThe')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'aiAssistant.stop' })).toBeInTheDocument();

    // Clicking Stop aborts cleanly without error bubble or askQuestion fallback
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.stop' }));
    expect(capturedSignal?.aborted).toBe(true);
    await waitFor(() => expect(screen.getByRole('button', { name: 'aiAssistant.send' })).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'aiAssistant.inline.retrySend' })).not.toBeInTheDocument();
    expect(mockedAskQuestion).not.toHaveBeenCalled();
    resolveStream?.();
  });

  it('renders document validity badges in sidebar and expanded citations', async () => {
    mockedGetDocuments.mockResolvedValue({
      documents: [
        {
          filename: '01/QC-CU — Quy chế cũ',
          category: 'Văn bản đến',
          is_managed: true,
          source_type: 'vanbanden',
          source_id: 1,
          hieu_luc: 'HET_HIEU_LUC',
        },
      ],
    });
    mockedAskQuestion.mockResolvedValue({
      answer: 'Văn bản đã sửa đổi',
      sources: [
        {
          file_name: '02/QC-SUA — Quy chế sửa đổi',
          source_type: 'vanbandi',
          source_id: 2,
          hieu_luc: 'CON_HIEU_LUC_1_PHAN',
        },
      ],
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    expect(await screen.findByText('aiAssistant.validity.expired')).toBeInTheDocument();

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Kiểm tra hiệu lực' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    await screen.findByText('Văn bản đã sửa đổi', { selector: 'p' });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));
    expect(await screen.findByText('aiAssistant.validity.partial')).toBeInTheDocument();
  });

  it('shows Admin AI Sync schedule modal only for admins without manual trigger button', async () => {
    const { unmount } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: 'aiAssistant.sync.openBtn' })).not.toBeInTheDocument();
    unmount();

    mockedUsePermissions.mockReturnValue({
      loaded: true,
      can: (perm: string) => perm === 'use_aiassistant',
      isSuperuser: true,
      isSystemAdmin: true,
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof usePermissions>);
    mockedGetAISyncStatus.mockResolvedValueOnce({
      configured: true,
      schema: { status: 'ok' },
      sql_eligible: { total: 5 },
      sql_indexed: { total: 5 },
      sql_pending_extraction: 0,
      kb_registered: 6,
      kb_indexed: 6,
      kb_orphans: 0,
      kb_orphan_names: [],
      total_chunks: 44,
      schedule: {
        enabled: true,
        mode: 'event_and_scheduled',
        task: 'sync_all_ai_documents',
        cron: '0 2 * * *',
        hour: 2,
        minute: 0,
        time: '02:00',
        timezone: 'Asia/Ho_Chi_Minh',
        next_run_at: '2026-11-20T02:00:00+07:00',
      },
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const syncOpenBtn = screen.getByRole('button', { name: 'aiAssistant.sync.openBtn' });
    fireEvent.click(syncOpenBtn);

    const dialog = await screen.findByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(await screen.findByText('5 / 5')).toBeInTheDocument();
    expect(screen.getByText('6 / 6')).toBeInTheDocument();
    expect(screen.getByText('44')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.sync.schemaOk')).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.sync.eventModeActive')).toBeInTheDocument();
    expect(screen.getByText(/aiAssistant\.sync\.scheduleDaily/)).toBeInTheDocument();
    expect(screen.getByText('aiAssistant.sync.nextRunLabel')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'aiAssistant.sync.syncNow' })).not.toBeInTheDocument();
  });

  it('allows safe internal links while stripping external and javascript markdown links', async () => {
    mockedAskQuestion.mockResolvedValue({
      answer:
        'Tham khảo [Kho Tài Liệu](/resources) hoặc [Xem VB](/documents/incoming?detail=5). Không mở [Phishing](https://evil.example/steal) và [XSS](javascript:alert(1)).',
      sources: [],
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Kiểm tra liên kết' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    const resourcesLink = await screen.findByRole('link', { name: 'Kho Tài Liệu' });
    expect(resourcesLink).toHaveAttribute('href', '/resources');
    const detailLink = screen.getByRole('link', { name: 'Xem VB' });
    expect(detailLink).toHaveAttribute('href', '/documents/incoming?detail=5');

    expect(screen.queryByRole('link', { name: 'Phishing' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'XSS' })).not.toBeInTheDocument();
    expect(screen.getByText(/Phishing/, { selector: 'p' })).toBeInTheDocument();
    expect(screen.getByText(/XSS/, { selector: 'p' })).toBeInTheDocument();

    fireEvent.click(resourcesLink);
    expect(await screen.findByTestId('location-probe')).toHaveTextContent('/resources');
  });

  it('renders horizontal rules and links nested inside italic and bold emphasis', async () => {
    mockedAskQuestion.mockResolvedValue({
      answer:
        '---\n*Gợi ý: Để đối chiếu văn bản, tham khảo **[Kho Tài Liệu & Biểu Mẫu](/resources)** hoặc **[Phishing](https://evil.example/steal)**.* Thêm `**[NotALink](/resources)**`.',
      sources: [],
    });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Kiểm tra nested markdown' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    const resourcesLink = await screen.findByRole('link', { name: 'Kho Tài Liệu & Biểu Mẫu' });
    expect(screen.getByRole('separator')).toBeInTheDocument();
    expect(resourcesLink).toHaveAttribute('href', '/resources');
    expect(resourcesLink.closest('strong')).not.toBeNull();
    expect(resourcesLink.closest('em')).not.toBeNull();
    expect(screen.queryByText(/\[Kho Tài Liệu & Biểu Mẫu\]\(\/resources\)/)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Phishing' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'NotALink' })).not.toBeInTheDocument();
    expect(screen.getByText(/Phishing/)).toBeInTheDocument();

    fireEvent.click(resourcesLink);
    expect(await screen.findByTestId('location-probe')).toHaveTextContent('/resources');
  });

  it('strips markdown links from chat history snippets', async () => {
    mockedAskQuestion.mockResolvedValueOnce({
      answer: 'Truy cập **[Kho Tài Liệu & Biểu Mẫu](/resources)** để tải biểu mẫu.',
      sources: [],
    });

    const { container } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Tìm biểu mẫu' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    await screen.findByRole('link', { name: 'Kho Tài Liệu & Biểu Mẫu' });
    const snippetEl = container.querySelector('.session-item-snippet');
    expect(snippetEl?.textContent).toContain('Kho Tài Liệu & Biểu Mẫu');
    expect(snippetEl?.textContent).not.toContain('(/resources)');
    expect(snippetEl?.textContent).not.toContain('[');
  });

  it('pins duplicate SQL document filenames independently by source_type and source_id', async () => {
    mockedGetDocuments.mockResolvedValue({
      documents: [
        {
          filename: '3667/AD — Văn bản trùng tên',
          category: 'Văn bản đến',
          is_managed: true,
          source_type: 'vanbanden',
          source_id: 101,
        },
        {
          filename: '3667/AD — Văn bản trùng tên',
          category: 'Văn bản đến',
          is_managed: true,
          source_type: 'vanbanden',
          source_id: 202,
        },
      ],
    });

    const { container } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    const pinButtons = await screen.findAllByTitle('aiAssistant.inline.targetThisDocumentForQ');
    expect(pinButtons).toHaveLength(2);

    fireEvent.click(pinButtons[0]);
    expect(container.querySelectorAll('.sidebar-doc-row.is-targeted')).toHaveLength(1);
    expect(container.querySelectorAll('.target-doc-pinned-badge')).toHaveLength(1);
  });

  it('blurs active sidebar focus before closing mobile drawer and displays total orphans in sync modal', async () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 390,
    });
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    });

    mockedUsePermissions.mockReturnValue({
      loaded: true,
      can: (perm: string) => perm === 'use_aiassistant',
      isSuperuser: true,
      isSystemAdmin: true,
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof usePermissions>);
    mockedGetAISyncStatus.mockResolvedValueOnce({
      configured: true,
      schema: { status: 'ok' },
      sql_eligible: { total: 147 },
      sql_indexed: { total: 146 },
      sql_pending_extraction: 1,
      sql_orphans: 5,
      kb_registered: 2,
      kb_indexed: 2,
      kb_orphans: 1,
      total_orphans: 6,
      kb_orphan_names: ['stale.pdf'],
      total_chunks: 471,
      schedule: { enabled: true, time: '02:00', timezone: 'Asia/Ho_Chi_Minh', next_run_at: '2026-11-22T02:00:00+07:00' },
    });

    const { container } = renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    const openBtn = screen.getByRole('button', { name: 'aiAssistant.expandSidebar' });
    fireEvent.click(openBtn);

    const sidebar = container.querySelector('aside.ai-chat-sidebar') as HTMLElement;
    const collapseBtn = screen.getByRole('button', { name: 'aiAssistant.collapseSidebar' });
    collapseBtn.focus();
    expect(sidebar.contains(document.activeElement)).toBe(true);

    fireEvent.click(collapseBtn);
    await waitFor(() => expect(sidebar).toHaveAttribute('aria-hidden', 'true'));
    expect(sidebar.contains(document.activeElement)).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.sync.openBtn' }));
    expect(await screen.findByText('146 / 147')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
  });
});
