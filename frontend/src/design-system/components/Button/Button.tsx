import React from 'react';
import styles from './Button.module.css';

export interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'brand' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  className?: string;
  type?: 'button' | 'submit';
}

const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  className,
  type = 'button',
}) => {
  const classNames = [
    styles['ds-btn'],
    styles[`ds-btn--${variant}`],
    styles[`ds-btn--${size}`],
    disabled && styles['ds-btn--disabled'],
    loading && styles['ds-btn--loading'],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type={type}
      className={classNames}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <span className={styles['ds-btn__spinner']} />}
      {children}
    </button>
  );
};

export default Button;
