import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'excel';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
  iconPosition?: 'left' | 'right';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  isLoading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-bold transition-all duration-fast rounded-lg cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-primary hover:bg-primary-hover text-white shadow-sm hover:shadow-glow hover:-translate-y-0.5 border border-primary',
    secondary:
      'bg-surface-elevated hover:bg-surface-hover text-main border border-border-subtle hover:border-primary/40',
    outline:
      'bg-transparent hover:bg-primary-subtle text-primary border border-primary hover:border-primary-hover',
    ghost:
      'bg-transparent hover:bg-surface-hover text-secondary hover:text-main border border-transparent',
    danger:
      'bg-danger hover:bg-danger-hover text-white shadow-sm hover:-translate-y-0.5 border border-danger',
    success:
      'bg-success hover:bg-success-hover text-white shadow-sm hover:-translate-y-0.5 border border-success',
    excel:
      'bg-emerald-50 hover:bg-emerald-100/90 text-[#107C41] dark:bg-emerald-950/40 dark:hover:bg-emerald-900/50 dark:text-emerald-400 border border-emerald-600/40 hover:border-emerald-600 shadow-2xs hover:shadow-xs',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <i className="fa-solid fa-spinner fa-spin text-current" />
      ) : (
        icon && iconPosition === 'left' && <i className={`fa-solid ${icon}`} />
      )}
      {children}
      {!isLoading && icon && iconPosition === 'right' && <i className={`fa-solid ${icon}`} />}
    </button>
  );
};

