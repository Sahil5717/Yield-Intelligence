/**
 * MarketLens design tokens.
 *
 * The client-facing Diagnosis surface uses a deliberately restrained
 * aesthetic -- Linear/Vercel-adjacent, with a warm off-white canvas and
 * sparing use of color. Professional-services tool, not a consumer dashboard.
 *
 * Typography: Geist as the display+body family. Loaded from Google Fonts
 * at the HTML level. Fall back to system-ui. No serif anywhere -- this
 * reads as a product, not a document.
 *
 * Colors stay within a narrow warm-gray neutral palette with one teal
 * accent and three confidence-tier colors. Deliberately NO yellow
 * (EY brand association avoided for the pitch tool), NO gradients,
 * NO purple.
 *
 * Spacing follows an 8px base unit: all paddings, margins, gaps are
 * multiples of 4 or 8. Corner radius is 12px on cards, 6px on pills
 * and buttons, 24px on the top hero card -- no other values.
 */

export const tokens = {
  // ─── Color ────────────────────────────────────────────────────────
  color: {
    // Canvas
    canvas: "#FAFAF7",        // warm off-white page background
    canvasAlt: "#F5F5F0",     // subtle variant for alternating sections
    surface: "#FFFFFF",       // card backgrounds
    surfaceSunken: "#F8F8F3", // inset / code-block / muted sections

    // Borders
    borderFaint: "#EDEDE8",   // hairline dividers inside cards
    border: "#E5E5E0",        // default card borders
    borderStrong: "#D4D4CE",  // emphatic borders on focus/hover

    // Text
    textPrimary: "#0A0A0A",   // near-black, not pure black
    textSecondary: "#525252", // muted body and metadata
    textTertiary: "#737373",  // captions, footers
    textInverse: "#FAFAF7",   // text on dark surfaces

    // Accent (used very sparingly)
    accent: "#0F766E",        // professional teal
    accentHover: "#0D5E58",   // hover state
    accentSubtle: "#F0FDFA",  // very light teal for accent-tinted backgrounds

    // Confidence tiers -- the three categorical colors
    confidenceHigh: "#15803D",      // forest green
    confidenceHighBg: "#F0FDF4",
    confidenceDirectional: "#A16207", // amber (saturated enough to read as "caution")
    confidenceDirectionalBg: "#FEF3C7",
    confidenceInconclusive: "#6B7280", // stone gray (deliberately absent of color)
    confidenceInconclusiveBg: "#F5F5F4",

    // Signal colors for tones -- used for KPI pills and finding types
    positive: "#15803D",
    positiveBg: "#F0FDF4",
    warning: "#B45309",
    warningBg: "#FFFBEB",
    negative: "#B91C1C",
    negativeBg: "#FEF2F2",
    neutralBg: "#F5F5F0",
  },

  // ─── Typography ───────────────────────────────────────────────────
  font: {
    display: "'Geist', system-ui, -apple-system, sans-serif",
    body: "'Geist', system-ui, -apple-system, sans-serif",
    mono: "'Geist Mono', ui-monospace, monospace",
  },

  // Type scale (rem). Every size used in the app must pick from this list.
  size: {
    xs: "0.75rem",    // 12px — metadata, captions
    sm: "0.875rem",   // 14px — secondary body
    base: "1rem",     // 16px — body
    md: "1.0625rem",  // 17px — finding narrative
    lg: "1.25rem",    // 20px — finding headline
    xl: "1.5rem",     // 24px — section header
    "2xl": "1.875rem", // 30px — KPI value
    "3xl": "2.5rem",  // 40px — hero diagnosis paragraph
    "4xl": "3rem",    // 48px — page title (MarketLens brand)
  },

  weight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  // Line heights tuned per context
  leading: {
    tight: 1.15,      // display sizes
    snug: 1.3,        // headlines
    normal: 1.5,      // body
    relaxed: 1.7,     // long-form prose (the diagnosis paragraph)
  },

  // Letter-spacing (negative for display, positive for UPPERCASE chrome)
  tracking: {
    tight: "-0.02em",
    snug: "-0.01em",
    normal: "0",
    wide: "0.05em",
    wider: "0.12em",
  },

  // ─── Spacing ──────────────────────────────────────────────────────
  // 8px base. Use these exclusively. No ad-hoc values.
  space: {
    0: "0",
    1: "4px",
    2: "8px",
    3: "12px",
    4: "16px",
    5: "20px",
    6: "24px",
    8: "32px",
    10: "40px",
    12: "48px",
    16: "64px",
    20: "80px",
    24: "96px",
  },

  // ─── Radius ───────────────────────────────────────────────────────
  radius: {
    sm: "6px",        // pills, buttons, chips
    md: "12px",       // cards (default)
    lg: "16px",       // larger cards
    xl: "24px",       // hero card containing headline paragraph
    full: "9999px",
  },

  // ─── Elevation ────────────────────────────────────────────────────
  // Deliberately restrained. Two shadows only, used for distinct purposes.
  shadow: {
    // Default card -- barely there, just enough to lift off the canvas
    card: "0 1px 2px rgba(10, 10, 10, 0.04)",
    // Raised state (when a card is expanded or focused)
    raised: "0 4px 12px rgba(10, 10, 10, 0.06), 0 2px 4px rgba(10, 10, 10, 0.04)",
  },

  // ─── Motion ───────────────────────────────────────────────────────
  motion: {
    // All transitions use the same cubic-bezier for cohesion
    ease: "cubic-bezier(0.16, 1, 0.3, 1)",
    fast: "120ms",
    base: "200ms",
    slow: "360ms",
  },

  // ─── Layout ───────────────────────────────────────────────────────
  layout: {
    readingWidth: "760px",   // max-width for headline paragraph and findings
    gridWidth: "1100px",     // max-width for KPI bento-grid section
    headerHeight: "64px",
  },
};

// Helper: convenience for inline style `color` shorthand
export const c = tokens.color;
export const t = tokens;

// Confidence tier → color mapping used throughout the app
export const confidenceColors = {
  High: {
    fg: tokens.color.confidenceHigh,
    bg: tokens.color.confidenceHighBg,
  },
  Directional: {
    fg: tokens.color.confidenceDirectional,
    bg: tokens.color.confidenceDirectionalBg,
  },
  Inconclusive: {
    fg: tokens.color.confidenceInconclusive,
    bg: tokens.color.confidenceInconclusiveBg,
  },
};

// Finding type → color mapping (for card left-border accent)
export const findingTypeColors = {
  positive: tokens.color.positive,
  opportunity: tokens.color.positive,
  warning: tokens.color.warning,
  negative: tokens.color.negative,
  insight: tokens.color.accent,
  neutral: tokens.color.textSecondary,
};
