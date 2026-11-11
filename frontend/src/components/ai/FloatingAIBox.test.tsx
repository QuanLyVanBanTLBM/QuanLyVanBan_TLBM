import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { askQuestion, askQuestionStream, getAISettings } from '../../api';
import FloatingAIBox from './FloatingAIBox';

vi.mock('../../api', () => ({
  askQuestion: vi.fn(),
  askQuestionStream: vi.fn(),
  getAISettings: vi.fn(),
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

describe('FloatingAIBox', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    mockedGetAISettings.mockResolvedValue({
      provider: 'openai',
      llm_model: 'gpt-6-luna',
    });
  });

  it('uses the configured model and streams chat responses to the UI', async () => {
    mockedAskQuestionStream.mockImplementation(async (_text, options: any) => {
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

    await waitFor(() => expect(mockedAskQuestion).toHaveBeenCalledWith('Fallback question', []));
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
});
