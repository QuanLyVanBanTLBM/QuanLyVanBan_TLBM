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
  updateAISettings,
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
const mockedUpdateAISettings = vi.mocked(updateAISettings);
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
        'vi'
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
        'vi'
      )
    );
  });

  it('hides delete, reclassify, and AI settings controls from non-admin users and shows them to admins', async () => {
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
    mockedUpdateAISettings.mockResolvedValue({ provider: 'openai', llm_model: 'gpt-6-luna' });

    renderAiPage();
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.tabDocs/ }));
    const deleteBtns = await screen.findAllByTitle('aiAssistant.deleteDoc');
    expect(deleteBtns.length).toBeGreaterThan(0);
    expect(screen.getAllByTitle('aiAssistant.inline.reclassifyDoc').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.inline.aiSettings' }));
    fireEvent.change(screen.getByLabelText('aiAssistant.settingsModal.apiKeyLabel'), {
      target: { value: 'sk-test-new-key-999' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.settingsModal.save' }));

    await waitFor(() =>
      expect(mockedUpdateAISettings).toHaveBeenCalledWith({
        provider: 'openai',
        api_key: 'sk-test-new-key-999',
        llm_model: 'gpt-6-luna',
      })
    );
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

    const sqlButtons = await screen.findAllByTitle('aiAssistant.viewDocument: VB-99');
    expect(sqlButtons).toHaveLength(1);

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
    expect(screen.getByText('aiAssistant.inline.targeted')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /aiAssistant\.newChat/ }));
    expect(screen.queryByText('aiAssistant.inline.targeted')).not.toBeInTheDocument();

    const textarea = screen.getByRole('textbox', { name: 'aiAssistant.inputPlaceholder' });
    fireEvent.change(textarea, { target: { value: 'Hỏi thử nghiệm' } });
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.send' }));

    const retryBtn = await screen.findByRole('button', { name: 'aiAssistant.inline.retrySend' });
    fireEvent.click(retryBtn);

    expect(await screen.findByText('Đã khôi phục câu trả lời', { selector: 'p' })).toBeInTheDocument();
  });
});
