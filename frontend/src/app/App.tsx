import { useState, useEffect } from 'react';
import AppRouter from './router';
import { ThemeMode } from '@app-types/theme';
import '@styles/global.css';

export default function App() {
  // Giao diện thực tế đang kích hoạt: Mặc định Clean Light cho người dùng mở web lần đầu
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('tlbm_theme');
    return saved === 'dark' ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('data-ui-style', 'modern');
    localStorage.setItem('tlbm_theme', theme);
  }, [theme]);

  // Chuyển đổi nhanh 1-chạm giữa Sáng và Tối (dùng cho nút trên Header)
  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  // Chọn trực tiếp 1 theme cụ thể
  const handleSelectTheme = (newTheme: ThemeMode) => {
    const validTheme: ThemeMode = newTheme === 'light' ? 'light' : 'dark';
    setTheme(validTheme);
  };

  return (
    <AppRouter
      currentTheme={theme}
      onSelectTheme={handleSelectTheme}
      onToggleTheme={handleToggleTheme}
      preferredLightTheme="light"
      preferredDarkTheme="dark"
    />
  );
}


