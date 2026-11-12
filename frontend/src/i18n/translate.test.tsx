import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { setLanguage, t, useTranslation } from './translate';
import layoutEn from './layout/en.json';
import recordsVi from './records/vi.json';
import workEn from './work/en.json';
import workVi from './work/vi.json';

afterEach(() => {
  act(() => setLanguage('vi'));
});

describe('translation hook used by catalog loading effects', () => {
  it('keeps the translator stable across unrelated renders', () => {
    const { result, rerender } = renderHook(() => useTranslation());
    const initialTranslate = result.current.t;
    rerender();
    expect(result.current.t).toBe(initialTranslate);
  });

  it('updates the translator and text when the language changes', () => {
    act(() => setLanguage('vi'));
    const { result } = renderHook(() => useTranslation());
    const vietnameseTranslate = result.current.t;
    const vietnameseText = result.current.t('records.dossiers.title');
    act(() => setLanguage('en'));
    expect(result.current.t).not.toBe(vietnameseTranslate);
    expect(result.current.t('records.dossiers.title')).not.toBe(vietnameseText);
    expect(result.current.currentLang).toBe('en');
  });

  it('accepts numeric interpolation while keeping string translations', () => {
    expect(t('{count}', { count: 3 }, 'en')).toBe('3');
  });

  it('merges namespaces shared by several module dictionaries', () => {
    expect(t('pages.tasks.title', undefined, 'vi')).toBe(workVi.pages.tasks.title);
    expect(t('pages.tasks.title', undefined, 'en')).toBe(workEn.pages.tasks.title);
    expect(t('pages.records.title', undefined, 'vi')).toBe(recordsVi.pages.records.title);
    expect(t('navigation.tasks', undefined, 'en')).toBe(workEn.navigation.tasks);
    expect(t('navigation.workflow', undefined, 'en')).toBe(layoutEn.navigation.workflow);
  });
});
