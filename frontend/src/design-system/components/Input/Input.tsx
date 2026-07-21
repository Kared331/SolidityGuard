import React, { forwardRef } from 'react';
import styles from './Input.module.css';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'prefix'> {
  type?: 'text' | 'search' | 'password';
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ type = 'text', prefix, suffix, className, disabled, ...rest }, ref) => {
    const wrapperClass = [
      styles['ds-input'],
      disabled ? styles['ds-input--disabled'] : '',
      prefix ? styles['ds-input--has-prefix'] : '',
      suffix ? styles['ds-input--has-suffix'] : '',
      type === 'search' ? styles['ds-input--search'] : '',
      className ?? '',
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <span className={wrapperClass}>
        {prefix && <span className={styles['ds-input__prefix']}>{prefix}</span>}
        <input
          ref={ref}
          type={type === 'search' ? 'text' : type}
          className={styles['ds-input__field']}
          disabled={disabled}
          {...rest}
        />
        {suffix && <span className={styles['ds-input__suffix']}>{suffix}</span>}
      </span>
    );
  }
);

Input.displayName = 'Input';
export default Input;
