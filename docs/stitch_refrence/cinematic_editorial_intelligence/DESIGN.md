---
name: Cinematic Editorial Intelligence
colors:
  surface: '#121317'
  surface-dim: '#121317'
  surface-bright: '#38393d'
  surface-container-lowest: '#0d0e12'
  surface-container-low: '#1a1b20'
  surface-container: '#1f1f24'
  surface-container-high: '#292a2e'
  surface-container-highest: '#343439'
  on-surface: '#e3e2e7'
  on-surface-variant: '#d8c3ad'
  inverse-surface: '#e3e2e7'
  inverse-on-surface: '#2f3035'
  outline: '#a08e7a'
  outline-variant: '#534434'
  surface-tint: '#ffb95f'
  primary: '#ffc174'
  on-primary: '#472a00'
  primary-container: '#f59e0b'
  on-primary-container: '#613b00'
  inverse-primary: '#855300'
  secondary: '#ffb77d'
  on-secondary: '#4d2600'
  secondary-container: '#d97707'
  on-secondary-container: '#432100'
  tertiary: '#fdc425'
  on-tertiary: '#3f2e00'
  tertiary-container: '#dea900'
  on-tertiary-container: '#574000'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddb8'
  primary-fixed-dim: '#ffb95f'
  on-primary-fixed: '#2a1700'
  on-primary-fixed-variant: '#653e00'
  secondary-fixed: '#ffdcc3'
  secondary-fixed-dim: '#ffb77d'
  on-secondary-fixed: '#2f1500'
  on-secondary-fixed-variant: '#6e3900'
  tertiary-fixed: '#ffdf9a'
  tertiary-fixed-dim: '#f7be1d'
  on-tertiary-fixed: '#251a00'
  on-tertiary-fixed-variant: '#5a4300'
  background: '#121317'
  on-background: '#e3e2e7'
  surface-variant: '#343439'
typography:
  display-hero:
    fontFamily: Bodoni Moda
    fontSize: 56px
    fontWeight: '600'
    lineHeight: 64px
    letterSpacing: -0.02em
  display-hero-mobile:
    fontFamily: Bodoni Moda
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Bodoni Moda
    fontSize: 36px
    fontWeight: '500'
    lineHeight: 44px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Bodoni Moda
    fontSize: 26px
    fontWeight: '500'
    lineHeight: 34px
    letterSpacing: 0em
  headline-md:
    fontFamily: Bodoni Moda
    fontSize: 24px
    fontWeight: '500'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-match:
    fontFamily: Space Grotesk
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-tag:
    fontFamily: Space Grotesk
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.08em
  caption:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 0.75rem
  margin: 3rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.75rem
  space-xl: 3rem
---

## Brand & Style

This design system embodies the intimacy and gravitas of prestige cinema paired with surgical, explainable intelligence. Built for cinephiles, curators, and discerning viewers exhausted by algorithmic bloat, the interface delivers an editorial lounge atmosphere rather than an endless scrolling warehouse.

The aesthetic fuses **Editorial Minimalism** with **Atmospheric Glassmorphism**:
- Ultra-dark, layered charcoal grounds the experience, simulating a darkened private screening room.
- Warm amber and radiant bronze provide deliberate points of focus, reminiscent of projector light cutting through smoke.
- High-contrast visual framing treats key art and film stills as gallery pieces rather than generic thumbnail tiles.
- Explainability is celebrated through precise, restrained analytical badges and micro-editorial annotations, giving weight to every recommendation.

## Colors

The palette relies on absolute darkness punctured by warm photonic luminance:

- **Canvas & Surface Tiering**:
  - `Canvas Ground`: `#0D0E12` (deepest cinematic black-charcoal).
  - `Surface Tier 1 (Cards, Elevated Modules)`: `#14161D` with 60%–80% opacity when paired with backdrop blur.
  - `Surface Tier 2 (Flyouts, Context Trays)`: `#1B1E28`.
  - `Border / Ghost Outlines`: `rgba(255, 255, 255, 0.08)` for structural containment; `rgba(245, 158, 11, 0.24)` for active or matched focus.

- **Accent & Luminance**:
  - `Primary Amber`: `#F59E0B` for match affirmations, editorial spotlights, primary interactions, and dynamic badges.
  - `Secondary Bronze`: `#D97706` for nuanced hover states, subtle gradient stops, and structural indicators.
  - `Tertiary Gold`: `#EAB308` reserved for critic scores, award nominations, and high-confidence telemetry indicators.

- **Editorial Typography Tones**:
  - `Text Primary`: `#F3F4F6` (crisp chalk).
  - `Text Secondary`: `#9CA3AF` (mist gray).
  - `Text Muted`: `#4B5563` (slate charcoal).

## Typography

The typographic hierarchy intentionally contrasts high-culture cinematic publishing with structured analytical precision:

- **Editorial Titles (`Bodoni Moda`)**: Expressive, high-contrast serif applied to film headlines, master director spotlights, and thematic narrative anchors. Conveys prestige film festival pedigree without feeling archival.
- **Interface & Narrative Core (`Inter`)**: Utilitarian, highly neutral grotesk handling loglines, actor credits, user reflections, and explainability reasoning text. Ensures instantaneous scan-ability.
- **Analytical Telemetry (`Space Grotesk`)**: Fixed-feeling, geometric display monospace hybrid deployed exclusively on data overlays: Match percentages, runtimes, audio mastering specs, and contextual rationale chips.

## Layout & Spacing

The layout is governed by a **12-column dynamic editorial grid** on desktop, collapsing to **6 columns on tablet** and **4 columns on mobile**:

- **Grid Dynamics**: Desktop max content width is locked at 1440px with generous outer margins (`3rem`) to preserve white (dark) space and eliminate claustrophobia.
- **Artwork Framing Hierarchy**:
  - Primary Hero Features: Span 8 to 12 columns with asymmetrical textual balance.
  - Explainability Cards & Film Stills: 3-column span (desktop), 6-column (tablet), full-bleed carousel (mobile).
  - Vertical Poster Aspect: 2:3 ratio strictly maintained with inline spacing gutters.
  - Editorial Stills & Narrative Frames: 16:9 or 2.39:1 widescreen ratios for contextual discovery modules.
- **Spacing Rhythm**: Spacing is rhythmic and deliberate. Card interiors utilize `space-md` (`1rem`) for dense analytical telemetry and `space-lg` (`1.75rem`) for editorial retrospectives.

## Elevation & Depth

Depth avoids crude black dropshadows, relying instead on optical illumination and multi-plane glass filtration:

- **Backdrop Blur Layers**: Secondary panels and context sheets utilize `backdrop-filter: blur(20px)` over `rgba(20, 22, 29, 0.72)`.
- **Projector Ambient Glow**: Focused or hovered artwork casts a directional ambient amber bleed: `0px 20px 40px -15px rgba(245, 158, 11, 0.15)`.
- **Subtle Surface Edges**: All floating containers, dialogs, and flyout overlays feature a hairline stroke (`1px solid rgba(255, 255, 255, 0.07)`) with an inward directional top highlight (`inset 0 1px 0 0 rgba(255, 255, 255, 0.12)`).
- **Z-Index Layering**:
  - Level 0: Pure charcoal matte canvas (`#0D0E12`).
  - Level 1: Film metadata cards & still matrices (`#14161D`).
  - Level 2: Explainability trays & popover inspection lenses (`#1B1E28` with frosted glass).
  - Level 3: Navigation, persistent search ribbons, and global screen overlays.

## Shapes

The shape system adopts a **tailored, refined architectural profile** (`roundedness: 1`):

- **Base Radius (0.25rem / 4px)**: Crisp micro-elements including rating chips, codec indicators, metadata tags, and input borders.
- **Card & Frame Radius (`rounded-lg`, 0.5rem / 8px)**: Film posters, video player frames, thematic collections, and analytical graph surfaces.
- **Overlay Panels (`rounded-xl`, 0.75rem / 12px)**: Modal sheets, drawer views, and explainable insight dialogs.
- **Exceptions**: Status pips, circular micro-avatars, and icon-only floating transport controls use full circular containment (`rounded-full`).

## Components

### Buttons
- **Primary Interactive (Amber Luminary)**: High-contrast rich amber background (`#F59E0B`), text rendered in deep charcoal (`#0D0E12`), font `Inter` SemiBold (`14px`), subtle internal top highlight, transition timing: `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Secondary (Editorial Outline)**: Charcoal tinted glass fill (`rgba(255, 255, 255, 0.03)`), ghost border (`1px solid rgba(255, 255, 255, 0.14)`), text `#F3F4F6`. Hover triggers border transition to `rgba(245, 158, 11, 0.5)` with amber glow.
- **Ghost/Tertiary**: No border, muted typography (`#9CA3AF`), shifts to `#F3F4F6` with underline accent.

### Chips & Rationale Badges
- **Explainability Match Badge**: Dual-segment chip. Left segment: `#F59E0B` background with deep charcoal label (e.g., `96% MATCH`). Right segment: translucent dark glass (`rgba(245, 158, 11, 0.1)`) housing the rationale string (e.g., `BECAUSE OF CINEMATOGRAPHY`). Typography: `Space Grotesk` (`11px`, all caps, tracked).
- **Genre & Attribute Chips**: Pill shape, borderless, matte carbon surface (`rgba(255, 255, 255, 0.05)`), text `#9CA3AF`.

### Film Cards & Visual Framing
- **Poster Artifact Card**: Strict 2:3 ratio. Artwork sits inside an inset matte with a hairline frame. On hover: slight zoom (`scale(1.02)`), ambient amber underglow appears, and the lower third reveals an editorial overlay containing the director's signature framing note and thematic alignment tags.
- **Wide Narrative Card (2.39:1)**: Cinematic widescreen canvas used for curated director retrospectives and deep dive sequences.

### Input Fields & Search Lens
- Surface: Recessed dark charcoal (`#090A0D`).
- Border: `1px solid rgba(255, 255, 255, 0.1)`.
- Focused State: Border transitions to `#F59E0B` with `0 0 0 1px #F59E0B` inner ring. Placeholder text styled in muted slate (`#4B5563`).

### Checkboxes, Radio Controls, & Toggles
- Custom geometry with 3px border radius.
- Unchecked: Outlined in `rgba(255, 255, 255, 0.2)` on matte charcoal.
- Checked: Amber fill (`#F59E0B`) with `#0D0E12` checkmark icon.

### Explainability Inspector Lens (Bespoke Module)
- Floating panel docked alongside film details.
- Displays a multi-axis breakdown: Narrative Weight, Visual Tone, Pacing, and Directorial Continuity.
- Visualized using amber hairline radar plots and mono-spaced contextual justification text.