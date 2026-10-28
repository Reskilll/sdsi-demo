import clsx from 'clsx';
import type { SelectHTMLAttributes } from 'react';

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export function Select({ label, className, children, ...rest }: Props) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      <span className="select-wrap">
        <select className={clsx('select', className)} {...rest}>
          {children}
        </select>
      </span>
    </label>
  );
}