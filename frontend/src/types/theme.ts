export type ThemeMode = 'dark' | 'light';

export interface ThemeOption {
  id: ThemeMode;
  name: string;
  icon: string;
  category: 'modern';
  categoryLabel: string;
  description: string;
  previewGradient: string;
  borderPreview?: string;
}


