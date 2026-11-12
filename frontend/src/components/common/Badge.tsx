import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'pink' | 'secondary';
  size?: 'sm' | 'md';
  dot?: boolean;
  withDot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  dot = false,
  withDot = false,
  className = '',
  ...props
}) => {
  const hasDot = dot || withDot;
  const baseStyles =
    'inline-flex items-center font-bold rounded-full select-none tracking-wide leading-none whitespace-nowrap shrink-0';

  const sizeStyles = {
    sm: 'text-[0.68rem] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
  };

  const variantStyles = {
    primary: 'bg-primary-subtle text-primary border border-primary-border',
    success: 'bg-success-subtle text-success border border-success-border',
    warning: 'bg-warning-subtle text-warning-text border border-warning-border',
    danger: 'bg-danger-subtle text-danger border border-danger-border',
    info: 'bg-info-subtle text-info border border-info-border',
    purple: 'bg-purple-subtle text-purple border border-purple-border',
    pink: 'bg-pink-subtle text-pink border border-pink-border',
    secondary: 'bg-surface-elevated text-secondary border border-border-subtle',
  };

  const dotColors = {
    primary: 'bg-primary',
    success: 'bg-success',
    warning: 'bg-warning-text',
    danger: 'bg-danger',
    info: 'bg-info',
    purple: 'bg-purple',
    pink: 'bg-pink',
    secondary: 'bg-muted',
  };

  return (
    <span
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {hasDot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]} shrink-0`} />}
      {children}
    </span>
  );
};

