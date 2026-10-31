import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { askQuestion, getAISettings } from '../../api';
import FloatingAIBox from './FloatingAIBox';

vi.mock('../../api', () => ({
  askQuestion: vi.fn(),
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
const mockedGetAISettings = vi.mocked(getAISettings);

describe('FloatingAIBox', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    mockedGetAISettings.mockResolvedValue({
      provider: 'gemini',
      llm_model: 'gemini-3.8-flash',
    });
  });

  it('uses the configured model and sends chat requests to the backend', async () => {
    mockedAskQuestion.mockResolvedValue({
      answer: '**A backend answer**',
      sources: [],
    });

    render(<FloatingAIBox />);
    await waitFor(() => expect(mockedGetAISettings).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));
    expect(await screen.findByText('gemini-3.8-flash')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }), {
      target: { value: 'Test question' },
    });
    fireEvent.submit(screen.getByRole('textbox', { name: 'floatingAI.placeholder' }).closest('form')!);

    await waitFor(() => expect(mockedAskQuestion).toHaveBeenCalledWith('Test question', []));
    expect(await screen.findByText('A backend answer', { selector: 'strong' })).toBeInTheDocument();
  });

  it('does not show a hard-coded model when settings cannot be loaded', async () => {
    mockedGetAISettings.mockRejectedValue(new Error('Settings unavailable'));

    render(<FloatingAIBox />);
    fireEvent.click(screen.getByRole('button', { name: 'floatingAI.openTitle' }));

    await waitFor(() => expect(mockedGetAISettings).toHaveBeenCalled());
    expect(screen.queryByText('gemini-3.8-flash')).not.toBeInTheDocument();
    expect(screen.queryByText('gpt-4o')).not.toBeInTheDocument();
  });
});
