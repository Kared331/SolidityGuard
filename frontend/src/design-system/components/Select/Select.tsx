import React, { useState, useRef, useEffect, useCallback } from 'react';
import styles from './Select.module.css';

export interface SelectOption {
  label: string;
  value: string;
}

export interface SelectProps {
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder,
  disabled,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  const handleToggle = useCallback(() => {
    if (!disabled) {
      setIsOpen((prev) => !prev);
    }
  }, [disabled]);

  const handleSelect = useCallback(
    (optionValue: string) => {
      onChange?.(optionValue);
      setIsOpen(false);
    },
    [onChange]
  );

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const wrapperClass = [
    styles['ds-select'],
    disabled ? styles['ds-select--disabled'] : '',
    isOpen ? styles['ds-select--open'] : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={wrapperClass} ref={containerRef}>
      <button
        type="button"
        className={styles['ds-select__trigger']}
        onClick={handleToggle}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span
          className={
            selectedOption
              ? styles['ds-select__value']
              : styles['ds-select__placeholder']
          }
        >
          {selectedOption ? selectedOption.label : placeholder ?? '请选择'}
        </span>
        <span className={styles['ds-select__chevron']} />
      </button>
      {isOpen && (
        <ul className={styles['ds-select__dropdown']} role="listbox">
          {options.map((option) => (
            <li
              key={option.value}
              className={[
                styles['ds-select__option'],
                option.value === value ? styles['ds-select__option--selected'] : '',
              ]
                .filter(Boolean)
                .join(' ')}
              role="option"
              aria-selected={option.value === value}
              onClick={() => handleSelect(option.value)}
            >
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

Select.displayName = 'Select';
export default Select;
