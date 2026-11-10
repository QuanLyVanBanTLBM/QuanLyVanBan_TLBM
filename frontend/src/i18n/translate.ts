import { useCallback, useSyncExternalStore } from 'react';

export type SupportedLanguage = 'vi' | 'en';
export type TranslationSchema = Record<string, unknown>;

// Mỗi module giữ từ điển riêng tại ./<module>/vi.json và ./<module>/en.json; từ điển đầy đủ là phép ghép đệ quy.
// Key trùng giữa hai module bị `pnpm check:i18n` chặn, nên thứ tự ghép không ảnh hưởng kết quả.
const VI_MODULES = import.meta.glob<TranslationSchema>('./*/vi.json', { eager: true, import: 'default' });
const EN_MODULES = import.meta.glob<TranslationSchema>('./*/en.json', { eager: true, import: 'default' });

function mergeInto(target: TranslationSchema, source: TranslationSchema): TranslationSchema {
  for (const [key, value] of Object.entries(source)) {
    const current = target[key];
    if (value && typeof value === 'object' && current && typeof current === 'object') {
      mergeInto(current as TranslationSchema, value as TranslationSchema);
    } else {
      target[key] = value && typeof value === 'object' ? mergeInto({}, value as TranslationSchema) : value;
    }
  }
  return target;
}

const mergeModules = (modules: Record<string, TranslationSchema>): TranslationSchema =>
  Object.values(modules).reduce<TranslationSchema>((dict, module) => mergeInto(dict, module), {});

const DICTIONARIES: Record<SupportedLanguage, TranslationSchema> = {
  vi: mergeModules(VI_MODULES),
  en: mergeModules(EN_MODULES),
};

const STORAGE_KEY = 'tlbm_lang';

// Trạng thái ngôn ngữ hiện tại
let currentLang: SupportedLanguage = (() => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY) as SupportedLanguage;
    if (saved === 'vi' || saved === 'en') {
      return saved;
    }
  }
  return 'vi';
})();

// Đồng bộ thuộc tính HTML lang ngay khi khởi tạo
if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', currentLang);
}

// Bộ lắng nghe sự kiện thay đổi ngôn ngữ
const listeners = new Set<() => void>();

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function getSnapshot(): SupportedLanguage {
  return currentLang;
}

/**
 * Lấy mã ngôn ngữ hiện tại ('vi' | 'en')
 */
export function getLanguage(): SupportedLanguage {
  return currentLang;
}

/**
 * Đổi ngôn ngữ hệ thống ('vi' | 'en'), lưu vào localStorage và thông báo đến toàn bộ component
 */
export function setLanguage(lang: SupportedLanguage): void {
  if (lang === currentLang) return;
  currentLang = lang;
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.setAttribute('lang', lang);
    window.dispatchEvent(new CustomEvent('tlbm_lang_changed', { detail: lang }));
    window.dispatchEvent(new Event('storage'));
  }
  // Kích hoạt re-render cho tất cả subscribers
  listeners.forEach((listener) => listener());
}

/**
 * Tra cứu chuỗi dịch theo dot notation (ví dụ: 'header.searchPlaceholder', 'pages.dashboard.title')
 */
export function t(
  key: string,
  replacements?: Record<string, string | number>,
  langOverride?: SupportedLanguage
): string {
  const lang = langOverride || currentLang;
  const dict = DICTIONARIES[lang] || DICTIONARIES.vi;
  const fallbackDict = DICTIONARIES.vi;

  const resolvePath = (obj: Record<string, unknown>, path: string) => {
    const parts = path.split('.');
    let cur: unknown = obj;
    for (const p of parts) {
      if (cur && typeof cur === 'object' && p in (cur as Record<string, unknown>)) {
        cur = (cur as Record<string, unknown>)[p];
      } else {
        return undefined;
      }
    }
    return typeof cur === 'string' ? cur : undefined;
  };

  let result = resolvePath(dict, key) ?? resolvePath(fallbackDict, key) ?? key;

  if (replacements && typeof result === 'string') {
    Object.entries(replacements).forEach(([k, v]) => {
      result = result.replace(new RegExp(`{${k}}`, 'g'), String(v));
    });
  }

  return result;
}

function getServerSnapshot(): SupportedLanguage {
  return 'vi';
}

/**
 * Custom React Hook phản ứng tức thì khi người dùng bấm chuyển đổi giữa Tiếng Việt và Tiếng Anh
 */
export function useTranslation() {
  const lang: SupportedLanguage = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const translations = DICTIONARIES[lang];
  const translate = useCallback(
    (key: string, replacements?: Record<string, string | number>) => t(key, replacements, lang),
    [lang]
  );

  return {
    currentLang: lang,
    setLanguage,
    t: translate,
    translations,
  };
}

export default DICTIONARIES.vi;

