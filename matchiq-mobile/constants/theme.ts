// MatchIQ - Tema Dark (identico alla webapp)
export const Colors = {
  // Colori principali webapp
  background: '#0a0f1a',   // --bg
  card:       '#162447',   // --card
  accent:     '#3498db',   // --accent
  green:      '#2ecc71',   // --green
  red:        '#e74c3c',   // --red
  yellow:     '#f39c12',   // --yellow
  text:       '#e8eaf6',   // --text
  muted:      '#8892b0',   // --muted
  border:     '#1f3460',   // border card
  surface:    '#0d1b2a',   // nav background

  // Alias per compatibilità componenti esistenti
  primary:       '#3498db',
  primaryDark:   '#2980b9',
  primaryLight:  '#5dade2',
  danger:        '#e74c3c',
  warning:       '#f39c12',
  info:          '#3498db',
  surfaceLight:  '#162447',
  textSecondary: '#8892b0',
  textMuted:     '#8892b0',
  success:       '#2ecc71',
  error:         '#e74c3c',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const Typography = {
  h1: { fontSize: 28, fontWeight: '700' as const },
  h2: { fontSize: 24, fontWeight: '700' as const },
  h3: { fontSize: 20, fontWeight: '600' as const },
  body: { fontSize: 16, fontWeight: '400' as const },
  caption: { fontSize: 14, fontWeight: '400' as const },
  small: { fontSize: 12, fontWeight: '400' as const },
};

export const BorderRadius = {
  sm: 8,
  md: 12,
  lg: 14,
  xl: 24,
  full: 9999,
};
