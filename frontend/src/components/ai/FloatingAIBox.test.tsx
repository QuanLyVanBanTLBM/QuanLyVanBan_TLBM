import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { askQuestion, askQuestionStream, getAISettings, getDocuments } from '../../api';
import FloatingAIBox from './FloatingAIBox';

vi.mock('../../api', () => ({
  askQuestion: vi.fn(),
  askQuestionStream: vi.fn(),
  getAISettings: vi.fn(),
  getDocuments: vi.fn(),
}));

vi.mock('@i18n/translate', () => ({
  t: (key: string) => key,
  useTranslation: () => ({
    t: (key: string) => key,
    currentLang: 'en',
  }),
}));

const mockedAskQuestion = vi.mocked(askQuestion);
const mockedAskQuestionStream = vi.mocked(askQuestionStream);
const mockedGetAISettings = vi.mocked(getAISettings);
const mockedGetDocuments = vi.mocked(getDocuments);

describe('FloatingAIBox', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    mockedGetAISettings.mockResolvedValue({
      provider: 'openai',
      llm_model: 'gpt-6-luna',
    });
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'policy.pdf', category: 'Policy' },
        { filename: 'guide.docx', category: 'Guide' },
      ],
    });
  });

  it('uses the configured model and streams chat responses to the UI', async () => {
    mockedAskQuestionStream.mockImplementation(async (_text, options?: { onDelta?: (d: string, a: string) => void; onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      options?.onDelta?.('**A backend answer**', '**A backend answer**');
      options?.onDone?.({ answer: '**A backend answer**', sources: [] });
      return { answer: '**A backend answer**', sources: [] };
    });

    render(<FloatingAIBox />);
    await waitFor(() => expect(mockedGetAISettings).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    expect(await screen.findByText('gpt-6-luna')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Test question' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await waitFor(() => expect(mockedAskQuestionStream).toHaveBeenCalled());
    expect(await screen.findByText('A backend answer', { selector: 'strong' })).toBeInTheDocument();
  });

  it('falls back to askQuestion when streaming fails before first chunk', async () => {
    mockedAskQuestionStream.mockRejectedValue(new Error('Stream network error'));
    mockedAskQuestion.mockResolvedValue({
      answer: '**Fallback answer**',
      sources: [],
    });

    render(<FloatingAIBox />);
    await waitFor(() => expect(mockedGetAISettings).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));

    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Fallback question' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await waitFor(() => expect(mockedAskQuestion).toHaveBeenCalledWith('Fallback question', [], null, null, 'en'));
    expect(await screen.findByText('Fallback answer', { selector: 'strong' })).toBeInTheDocument();
  });

  it('does not show a hard-coded model when settings cannot be loaded', async () => {
    mockedGetAISettings.mockRejectedValue(new Error('Settings unavailable'));

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));

    await waitFor(() => expect(mockedGetAISettings).toHaveBeenCalled());
    expect(screen.queryByText('gpt-6-luna')).not.toBeInTheDocument();
  });

  it('allows dragging the chat box window and resets on double click', async () => {
    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));

    const header = screen.getByTitle('floatingAI.dragTooltip');
    expect(header).toBeInTheDocument();

    const win = header.closest('div.fixed') as HTMLElement;
    vi.spyOn(win, 'getBoundingClientRect').mockReturnValue({
      left: 100,
      top: 100,
      width: 390,
      height: 400,
      right: 490,
      bottom: 500,
      x: 100,
      y: 100,
      toJSON: () => {},
    });

    act(() => {
      fireEvent.mouseDown(header, { clientX: 120, clientY: 120 });
    });
    act(() => {
      fireEvent.mouseMove(window, { clientX: 220, clientY: 260 });
    });
    act(() => {
      fireEvent.mouseUp(window);
    });

    expect(win.style.left).toBe('200px');
    expect(win.style.top).toBe('240px');

    act(() => {
      fireEvent.doubleClick(header);
    });
    expect(win.style.left).toBe('');
    expect(win.style.top).toBe('');
  });

  it('renders clickable citation buttons that navigate with detail id or module page', async () => {
    const onNavigate = vi.fn();
    const onNavigateUrl = vi.fn();
    mockedAskQuestion.mockResolvedValue({
      answer: 'Thông tin văn bản',
      sources: [
        { file_name: 'CV 123', source_type: 'vanbanden', source_id: 42, page: 1 },
        { file_name: 'CV 123', source_type: 'vanbanden', source_id: 42, page: 2 },
        { file_name: 'Nghiệp vụ Ký số', source_type: 'business_spec', source_id: 'branch-05-signing' },
      ],
    });

    render(<FloatingAIBox onNavigate={onNavigate} onNavigateUrl={onNavigateUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Hỏi về CV 123' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await screen.findByText('Thông tin văn bản');
    expect(screen.queryByRole('button', { name: /CV 123/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));

    const incomingBtn = await screen.findByRole('button', { name: /CV 123/ });
    expect(screen.getAllByRole('button', { name: /CV 123/ })).toHaveLength(1);
    fireEvent.click(incomingBtn);
    expect(onNavigateUrl).toHaveBeenCalledWith('/documents/incoming?detail=42');

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.click(await screen.findByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));
    const specBtn = await screen.findByRole('button', { name: /Nghiệp vụ Ký số/ });
    fireEvent.click(specBtn);
    expect(onNavigate).toHaveBeenCalledWith('approvals');
  });

  it('allows targeting a specific document and clearing the selection', async () => {
    mockedAskQuestionStream.mockImplementation(async (_text, options?: { onDelta?: (d: string, a: string) => void; onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      options?.onDelta?.('Trả lời theo tệp chỉ định', 'Trả lời theo tệp chỉ định');
      options?.onDone?.({ answer: 'Trả lời theo tệp chỉ định', sources: [] });
      return { answer: 'Trả lời theo tệp chỉ định', sources: [] };
    });

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.selectDocument' }));
    const searchInput = await screen.findByRole('textbox', { name: 'floatingAI.searchDocuments' });
    fireEvent.change(searchInput, { target: { value: 'policy' } });
    fireEvent.click(screen.getByRole('button', { name: 'policy.pdf' }));

    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Tóm tắt chính' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await waitFor(() => expect(mockedAskQuestionStream).toHaveBeenCalledWith('Tóm tắt chính', expect.objectContaining({ filename: 'policy.pdf' })));
    expect(await screen.findByText('Trả lời theo tệp chỉ định')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.clearTarget' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Câu hỏi chung' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await waitFor(() =>
      expect(mockedAskQuestionStream).toHaveBeenLastCalledWith('Câu hỏi chung', expect.objectContaining({
        filename: null,
        history: [
          { role: 'user', content: 'Tóm tắt chính' },
          { role: 'assistant', content: 'Trả lời theo tệp chỉ định' },
        ],
      })),
    );
  });

  it('renders answer when onDone arrives without prior onDelta', async () => {
    mockedAskQuestionStream.mockImplementation(async (_text, options?: { onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      options?.onDone?.({ answer: 'Chỉ có sự kiện done', sources: [] });
      return { answer: 'Chỉ có sự kiện done', sources: [] };
    });

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Hỏi done-only' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    expect(await screen.findByText('Chỉ có sự kiện done')).toBeInTheDocument();
    expect(mockedAskQuestion).not.toHaveBeenCalled();
  });

  it('hides thinking dots on first delta while keeping send disabled until stream finishes', async () => {
    let finishStream!: () => void;
    mockedAskQuestionStream.mockImplementation((_text, options?: { onDelta?: (d: string, a: string) => void; onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      return new Promise((resolve) => {
        setTimeout(() => {
          options?.onDelta?.('Đang trả lời...', 'Đang trả lời...');
        }, 0);
        finishStream = () => {
          options?.onDone?.({ answer: 'Đang trả lời... xong', sources: [] });
          resolve({ answer: 'Đang trả lời... xong', sources: [] });
        };
      });
    });

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Kiểm tra streaming' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    expect(screen.getByRole('status', { name: 'floatingAI.thinking' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'floatingAI.send' })).toBeDisabled();

    await screen.findByText('Đang trả lời...');
    expect(screen.queryByRole('status', { name: 'floatingAI.thinking' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'floatingAI.send' })).toBeDisabled();

    await act(async () => {
      finishStream();
    });
    expect(await screen.findByText('Đang trả lời... xong')).toBeInTheDocument();
  });

  it('displays safe backend detail message on API failure', async () => {
    mockedAskQuestionStream.mockRejectedValue(new Error('Stream error'));
    mockedAskQuestion.mockRejectedValue({ data: { detail: 'Không thể truy cập nguồn dữ liệu AI lúc này.' } });

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Hỏi lỗi API' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể truy cập nguồn dữ liệu AI lúc này.');
  });

  it('renders validity badges on expired citations and document picker items', async () => {
    mockedGetDocuments.mockResolvedValue({
      documents: [
        { filename: 'old_policy.pdf', category: 'Policy', hieu_luc: 'HET_HIEU_LUC' },
      ],
    });
    mockedAskQuestionStream.mockImplementation(async (_text, options?: { onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      options?.onDone?.({
        answer: 'Văn bản đã hết hiệu lực.',
        sources: [
          {
            file_name: '01/QD-CU',
            source_type: 'vanbanden',
            source_id: 9,
            hieu_luc: 'HET_HIEU_LUC',
          },
        ],
      });
      return { answer: 'Văn bản đã hết hiệu lực.', sources: [] };
    });

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    await waitFor(() => expect(mockedGetDocuments).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.selectDocument' }));
    expect(await screen.findByText('floatingAI.validity.expired')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Kiểm tra quy chế cũ' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await screen.findByText('Văn bản đã hết hiệu lực.');
    fireEvent.click(screen.getByRole('button', { name: 'aiAssistant.toggleCitationsExpand' }));
    expect(screen.getByText('floatingAI.validity.expired')).toBeInTheDocument();
  });

  it('renders allowed internal markdown links and neutralizes external or script links', async () => {
    mockedAskQuestionStream.mockImplementation(async (_text, options?: { onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      options?.onDone?.({
        answer:
          'Mở [Kho Tài Liệu](/resources), nhưng bỏ qua [Phishing](https://evil.example/steal) và [XSS](javascript:alert(1)).',
        sources: [],
      });
      return { answer: '', sources: [] };
    });

    render(<FloatingAIBox onNavigateUrl={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Kiểm tra link' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    const link = await screen.findByRole('link', { name: 'Kho Tài Liệu' });
    expect(link).toHaveAttribute('href', '/resources');
    expect(screen.queryByRole('link', { name: 'Phishing' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'XSS' })).not.toBeInTheDocument();
    expect(screen.getByText(/Phishing/)).toBeInTheDocument();
    expect(screen.getByText(/XSS/)).toBeInTheDocument();
  });

  it('renders hr and clickable internal links nested inside italic and bold emphasis', async () => {
    const onNavigateUrl = vi.fn();
    mockedAskQuestionStream.mockImplementation(async (_text, options?: { onDone?: (data: { answer: string; sources: unknown[] }) => void }) => {
      options?.onDone?.({
        answer:
          '---\n*Gợi ý: **[Kho Tài Liệu & Biểu Mẫu](/resources)** và **[XSS](javascript:alert(1))**.*',
        sources: [],
      });
      return { answer: '', sources: [] };
    });

    render(<FloatingAIBox onNavigateUrl={onNavigateUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Kiểm tra link lồng nhau' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    const link = await screen.findByRole('link', { name: 'Kho Tài Liệu & Biểu Mẫu' });
    expect(screen.getByRole('separator')).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/resources');
    expect(screen.queryByRole('link', { name: 'XSS' })).not.toBeInTheDocument();
    fireEvent.click(link);
    expect(onNavigateUrl).toHaveBeenCalledWith('/resources');
  });
});
