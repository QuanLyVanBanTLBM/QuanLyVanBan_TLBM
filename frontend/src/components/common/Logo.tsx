import React, { useState } from 'react';

export type LogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
export type LogoVariant = 'auto' | 'white' | 'dark' | 'color';
export type LogoType = 'full' | 'icon';

export interface LogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  /** Kích thước của Logo (chiều cao và tỉ lệ tương ứng) */
  size?: LogoSize;
  /** Biến thể màu sắc: auto (tự thích ứng theme sáng/tối), white (trắng cho dark mode), color/dark (xanh vàng cho light mode) */
  variant?: LogoVariant;
  /** Kiểu hiển thị: 'full' (logo đầy đủ chữ + biểu tượng) hoặc 'icon' (chỉ biểu tượng rồng) */
  type?: LogoType;
  /** Cờ tiện dụng, tương đương type="icon" */
  iconOnly?: boolean;
}

const LOGO_ASSETS = {
  full: {
    white: '/baolong-logo.png',
    dark: '/baolong-logo-color.png',
    color: '/baolong-logo-color.png',
  },
  icon: {
    white: '/baolong-icon.png',
    dark: '/baolong-icon.png',
    color: '/baolong-icon.png',
  },
} as const;

const SIZE_MAP: Record<LogoSize, { full: string; icon: string }> = {
  xs: { full: 'h-5', icon: 'h-5 w-5' },
  sm: { full: 'h-6', icon: 'h-6 w-6' },
  md: { full: 'h-8', icon: 'h-8 w-8' },
  lg: { full: 'h-10', icon: 'h-10 w-10' },
  xl: { full: 'h-12', icon: 'h-12 w-12' },
  '2xl': { full: 'h-14', icon: 'h-14 w-14' },
};

export const Logo: React.FC<LogoProps> = React.memo(({
  size = 'md',
  variant = 'auto',
  type = 'full',
  iconOnly = false,
  className = '',
  alt = 'Bảo Long Insurance',
  loading = 'lazy',
  decoding = 'async',
  onError,
  ...props
}) => {
  const [hasError, setHasError] = useState(false);

  const isIcon = iconOnly || type === 'icon';
  const assets = LOGO_ASSETS[isIcon ? 'icon' : 'full'];
  const sizeConfig = SIZE_MAP[size] || SIZE_MAP.md;
  const dimensionClass = isIcon ? sizeConfig.icon : `${sizeConfig.full} w-auto`;
  const baseImgClass = `${dimensionClass} object-contain transition-opacity duration-200`;

  const handleError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    setHasError(true);
    onError?.(e);
  };

  if (hasError) {
    return (
      <span
        className={`inline-flex items-center justify-center font-bold text-primary select-none ${dimensionClass} ${className}`}
        title={alt}
      >
        BL
      </span>
    );
  }

  // Trường hợp variant cố định: chỉ render 1 thẻ img duy nhất để tối ưu DOM & network
  if (variant === 'white' || variant === 'dark' || variant === 'color') {
    const src = variant === 'white' ? assets.white : assets.color;
    return (
      <img
        src={src}
        alt={alt}
        loading={loading}
        decoding={decoding}
        onError={handleError}
        className={`${baseImgClass} ${className}`}
        {...props}
      />
    );
  }

  // Trường hợp variant === 'auto': Tự thích ứng theo chế độ theme của ứng dụng (Dark/Light)
  return (
    <span className="inline-flex items-center shrink-0 select-none">
      <img
        src={assets.white}
        alt={alt}
        loading={loading}
        decoding={decoding}
        onError={handleError}
        className={`${baseImgClass} hidden dark:block ${className}`}
        {...props}
      />
      <img
        src={assets.dark}
        alt={alt}
        loading={loading}
        decoding={decoding}
        onError={handleError}
        className={`${baseImgClass} block dark:hidden ${className}`}
        {...props}
      />
    </span>
  );
});

Logo.displayName = 'Logo';

export default Logo;

