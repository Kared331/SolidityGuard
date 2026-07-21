export interface IconProps {
  name: string;
  size?: number;
  className?: string;
  color?: string;
}

/**
 * SVG Icon component.
 * Looks up icon from a pre-defined registry of inline SVG paths.
 * Falls back to displaying the icon name if not found.
 */
export default function Icon({ name, size = 16, className, color }: IconProps) {
  const svgContent = iconRegistry[name];

  if (!svgContent) {
    return (
      <span
        className={className}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: size,
          height: size,
          color: color || 'var(--ds-color-icon-default)',
          fontSize: `${size * 0.7}px`,
          fontWeight: 600,
          userSelect: 'none',
        }}
        aria-hidden="true"
      >
        ?
      </span>
    );
  }

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
        color: color || 'var(--ds-color-icon-default)',
        flexShrink: 0,
      }}
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  );
}

/* ===== Icon Registry ===== */
/* All icons are inline SVG paths extracted from TRAE Work design system */
const iconRegistry: Record<string, string> = {
  /* Navigation */
  'chevron-down': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'chevron-right': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'chevron-left': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 4l-4 4 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'arrow-left': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M12 8H4M4 8l3-3M4 8l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',

  /* Actions */
  'close': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'plus': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'search': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="6.5" cy="6.5" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M10 10l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'edit': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M11 2l3 3-9 9H2v-3l9-9z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'delete': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M5 4V2h6v2M6 7v4M10 7v4M3 4l1 10h8l1-10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'copy': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="4" width="9" height="10" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M3 12V3h9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'download': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v8M4 10l4 4 4-4M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'upload': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v8M4 6l4-4 4 4M2 12v1a1 1 0 001 1h10a1 1 0 001-1v-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'refresh': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13 8a5 5 0 00-9.9-1M3 8a5 5 0 009.9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M3 3v3h3M13 13v-3h-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',

  /* Security / Audit Specific */
  'shield': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2S3 4 3 7.5c0 5 5 6.5 5 6.5s5-1.5 5-6.5C13 4 8 2 8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'shield-check': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2S3 4 3 7.5c0 5 5 6.5 5 6.5s5-1.5 5-6.5C13 4 8 2 8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 8l1.5 1.5L10 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'bug': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 6V4a3 3 0 016 0v2M3 6h10M4 10h8M6 6v4M10 6v4M5 14h6M2 3l2 2M14 3l-2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'lock': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="3" y="7" width="10" height="7" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M5 7V5a3 3 0 016 0v2" stroke="currentColor" stroke-width="1.5"/></svg>',
  'eye': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 4C4 4 1.5 8 1.5 8s2.5 4 6.5 4 6.5-4 6.5-4S12 4 8 4z" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.5"/></svg>',
  'file': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V6l-5-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 1v5h5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'folder': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M1 4a1 1 0 011-1h3l2 2h6a1 1 0 011 1v6a1 1 0 01-1 1H2a1 1 0 01-1-1V4z" stroke="currentColor" stroke-width="1.5"/></svg>',
  'code': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 5L2 8l3 3M11 5l3 3-3 3M9 3L7 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'brain': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1C5.5 1 4 3 4 5.5c0 1.5.5 2.5 1 3.5v4h6V9c.5-1 1-2 1-3.5C12 3 10.5 1 8 1z" stroke="currentColor" stroke-width="1.5"/><path d="M5 9c-1 0-2 .5-2 1.5S4 13 5 13m6-4c1 0 2 .5 2 1.5S12 13 11 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'flash': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M9 1L3 9h5L6 15l7-9H7l2-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'zap': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M9 1L3 9h5l-2 6 7-9H7l2-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'test-tube': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M5 1h6M6 1v6L3 12a2 2 0 001.5 3h7A2 2 0 0013 12l-3-5V1" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',

  /* General UI */
  'check': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'alert-triangle': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2L1 14h14L8 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M8 7v3M8 12v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'alert-circle': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3M8 11v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'info': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 7v4M8 5v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'play': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 2l10 6-10 6V2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'stop': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="3" y="3" width="10" height="10" rx="1" stroke="currentColor" stroke-width="1.5"/></svg>',
  'more-horizontal': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="3" cy="8" r="1" fill="currentColor"/><circle cx="8" cy="8" r="1" fill="currentColor"/><circle cx="13" cy="8" r="1" fill="currentColor"/></svg>',
  'external-link': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M11 2h3v3M9 7l5-5M12 9v3a1 1 0 01-1 1H4a1 1 0 01-1-1V5a1 1 0 011-1h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  'home': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 6l6-4 6 4v7a1 1 0 01-1 1H3a1 1 0 01-1-1V6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M6 14V9h4v5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>',
  'settings': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.5" stroke="currentColor" stroke-width="1.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'database': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><ellipse cx="8" cy="3" rx="6" ry="2" stroke="currentColor" stroke-width="1.5"/><path d="M2 3v5c0 1.1 2.7 2 6 2s6-.9 6-2V3M2 8v5c0 1.1 2.7 2 6 2s6-.9 6-2V8" stroke="currentColor" stroke-width="1.5"/></svg>',
  'bar-chart': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="9" width="3" height="5" rx="0.5" stroke="currentColor" stroke-width="1.5"/><rect x="6.5" y="5" width="3" height="9" rx="0.5" stroke="currentColor" stroke-width="1.5"/><rect x="12" y="2" width="3" height="12" rx="0.5" stroke="currentColor" stroke-width="1.5"/></svg>',
  'table': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="14" height="14" rx="1" stroke="currentColor" stroke-width="1.5"/><path d="M1 5h14M1 9h14M5 1v14" stroke="currentColor" stroke-width="1.5"/></svg>',
  'list': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h12M2 12h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'grid': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="1" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="1" y="9" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="6" height="6" rx="1" stroke="currentColor" stroke-width="1.5"/></svg>',
  'user': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
  'clock': '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};
