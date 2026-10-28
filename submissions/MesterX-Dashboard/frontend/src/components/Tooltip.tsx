import { useState, useRef, useEffect, type ReactNode } from 'react';
import clsx from 'clsx';

export function Tooltip({ label, children }: { label: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [open]);

  return (
    <span
      ref={containerRef}
      className={clsx('tooltip', open && 'tooltip-open')}
      onClick={(e) => {
        e.stopPropagation();
        setOpen((prev) => !prev);
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      tabIndex={0}
      role="button"
      aria-expanded={open}
    >
      {children}
      {open && (
        <span
          className="tooltip-bubble"
          role="tooltip"
          onClick={(e) => e.stopPropagation()}
        >
          {label}
        </span>
      )}
    </span>
  );
}
