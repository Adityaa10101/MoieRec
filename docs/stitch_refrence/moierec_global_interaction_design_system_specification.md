# MoieRec — Global Interaction & Design System Specification
**Product:** MoieRec — Personalized Movie Recommendation System  
**Document Version:** 1.0.0 (Global Editorial Canon)  
**Status:** Canonical Design System & Motion Architecture  
**Device Target:** Responsive Web (Primary: Desktop Web 1440px+, Mobile Adaptive)

---

## 1. Global Design Tokens & Foundation

### 1.1 Palette & Surfaces
MoieRec operates exclusively on a rich, cinematic dark canvas. Surfaces are layered by perceived physical proximity and curatorial elevation rather than arbitrary gray steps.

| Token Name | Hex / Value | Tailwind / CSS Equivalent | Purpose & Hierarchy |
| :--- | :--- | :--- | :--- |
| `surface-base` / `background` | `#0d0e12` | `bg-[#0d0e12]` | Deepest substrate; canvas base, full-page void |
| `surface-dim` | `#121317` | `bg-[#121317]` | Primary content background; body sections |
| `surface-container-low` | `#1a1b20` | `bg-[#1a1b20]` | Subtle grouping cards, metadata panels |
| `surface-container-high` | `#23252b` | `bg-[#23252b]` | Elevated cards, dialog overlays, dropdown sheets |
| `surface-elevated` | `#2b2d35` | `bg-[#2b2d35]` | Highest interactive elevation, floating toolbars |
| `surface-glass` | `rgba(18, 19, 23, 0.75)` | `backdrop-blur-md bg-[#121317]/75` | Sticky navbar, floating action clusters, modal scrims |

### 1.2 Curatorial Accent Palette
Gold is used with strict restraint to designate high personalization, editorial truth, and primary intent.

| Token Name | Value | Purpose |
| :--- | :--- | :--- |
| `accent-gold-primary` | `#f59e0b` / `amber-500` | Primary CTAs, high match badges (90%+), active nav indicator |
| `accent-gold-hover` | `#d97706` / `amber-600` | Hover states for primary gold elements |
| `accent-gold-muted` | `rgba(245, 158, 11, 0.16)` | Selected genre chips, active list backgrounds, tag backdrops |
| `accent-gold-glow` | `0 0 24px rgba(245, 158, 11, 0.22)` | Subtle glow for active mood cards, hero badges, match highlights |
| `accent-gold-subtle` | `#b45309` | Inactive slider milestones, secondary match telemetry |

### 1.3 Text Hierarchy & Opacities
Typography adheres to strict contrast ratios against the cinematic dark backdrop.

| Level | Value | RGBA / Class | Usage |
| :--- | :--- | :--- | :--- |
| `text-primary` | `#f8fafc` | `text-slate-50` (100% white-amber tint) | Titles, active headers, key movie names |
| `text-secondary` | `#cbd5e1` | `text-slate-300` (80% opacity) | Synopsis, body paragraphs, field labels |
| `text-muted` | `#64748b` | `text-slate-500` (50% opacity) | Secondary metadata (runtime, year, studio) |
| `text-disabled` | `#334155` | `text-slate-700` (25% opacity) | Inactive controls, placeholder inputs |

### 1.4 Borders & Separators
- **Subtle (Default):** `1px solid rgba(255, 255, 255, 0.07)` (`border-white/5` to `border-white/10`)
- **Interactive / Hover:** `1px solid rgba(255, 255, 255, 0.20)` (`hover:border-white/20`)
- **Active / Match Anchor:** `1px solid rgba(245, 158, 11, 0.40)` (`border-amber-500/40`)

### 1.5 Elevation & Shadow System
- `elevation-flat`: `none` (default for grid containers)
- `elevation-card`: `0 8px 24px -4px rgba(0, 0, 0, 0.60)`
- `elevation-hover`: `0 20px 40px -8px rgba(0, 0, 0, 0.85), 0 0 20px rgba(245, 158, 11, 0.12)`
- `elevation-nav`: `0 12px 32px rgba(0, 0, 0, 0.70)`

---

## 2. Typography Architecture

MoieRec balances high-fashion editorial serif typography (`Bodoni Moda` / `Cinzel` display) with ultra-legible, modern neutral sans-serif typography (`Plus Jakarta Sans` / `Inter`) for dense telemetry and reading comfort.

| Element | Typeface | Size / Weight | Line Height | Tracking | Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hero Title** | Serif Display | 56px–72px / Bold (700) | 1.05 | -0.02em | UPPERCASE / Title |
| **Page Title** | Serif Display | 36px–44px / SemiBold (600) | 1.15 | -0.015em | UPPERCASE |
| **Section Title** | Serif Display | 24px–28px / SemiBold (600) | 1.25 | -0.01em | UPPERCASE / Title |
| **Movie Card Title**| Sans / Serif | 16px–18px / Medium (500) | 1.30 | -0.005em | Title Case |
| **Body / Synopsis** | Sans | 15px–16px / Regular (400) | 1.60 | 0 | Sentence |
| **Telemetry / Stats**| Sans Mono / Sans | 13px–14px / SemiBold (600) | 1.20 | +0.02em | Tabular |
| **Badges / Chips** | Sans | 11px–12px / Medium (500) | 1.00 | +0.05em | UPPERCASE |
| **Nav Links** | Sans | 14px / Regular to Medium | 1.00 | +0.01em | Title Case |

---

## 3. Global Navigation Behavior

### 3.1 Desktop Position & Transitions
- **Position:** `fixed top-0 left-0 right-0 z-50 w-full`
- **Initial Top State (Scroll Offset 0px):**
  - Height: `80px`
  - Background: `rgba(18, 19, 23, 0.40)` with `backdrop-blur-sm`
  - Border Bottom: `border-transparent`
- **Scrolled State (Scroll Offset > 40px):**
  - Height: `72px` (subtle 8px collapse)
  - Background: `rgba(13, 14, 18, 0.88)` with `backdrop-blur-md`
  - Border Bottom: `1px solid rgba(255, 255, 255, 0.08)`
  - Shadow: `elevation-nav`
  - Transition: `all 300ms cubic-bezier(0.16, 1, 0.3, 1)`

### 3.2 Active & Inactive Links
- **Active Page:** Warm gold text (`text-amber-500`), subtle underline or bottom gold dot indicator (`after:w-1.5 after:h-1.5 after:bg-amber-500 after:rounded-full`).
- **Inactive Page:** `text-slate-400 hover:text-slate-100 hover:bg-white/5` with `transition-colors duration-200`.
- **Taste Profile Pill:** Persistent pill indicator displaying active genre vector (`Taste Profile • Sci-Fi & Drama`), clickable for rapid profile adjustment.

---

## 4. Page Scrolling & Viewport Dynamics

1. **Document-Level Scrolling:** The entire `window` / `body` scrolls natively. No internal overflow containers for whole pages (`overflow-y: auto` strictly on `body`/`html`).
2. **Horizontal Recommendation Rows:**
   - Dedicated row containers utilize `overflow-x: auto; scrollbar-width: none; -ms-overflow-style: none; scroll-snap-type: x mandatory;`.
   - Trackpad and shift-wheel interactions scroll horizontally without blocking page vertical progression.
   - Peek Cue: The trailing card is partially cropped (showing 25%–35% of its width) to indicate horizontal depth.
3. **No Trapped Viewports:** Users never get trapped inside sticky nested scrollboxes.

---

## 5. Scroll Reveal Animation Language

Sections reveal smoothly without delaying fast-scrolling curators.

```css
/* Section Scroll-In Specification */
@keyframes sectionEnter {
  0% {
    opacity: 0;
    transform: translateY(24px);
    filter: blur(4px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}
.reveal-on-scroll {
  animation: sectionEnter 450ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  will-change: opacity, transform, filter;
}
```

- **Stagger Pattern (Card Rows):**
  - Card 1: `delay: 0ms`
  - Card 2: `delay: 40ms`
  - Card 3: `delay: 80ms`
  - Card 4: `delay: 120ms`
  - Card 5: `delay: 160ms`
- **Reduced Motion:** If `prefers-reduced-motion: reduce`, set `opacity: 1 !important; transform: none !important; filter: none !important; animation: none !important;`.

---

## 6. Cinematic Hero Animation

On initial page landing (e.g. Movie Detail or Personalized Home):

1. **Backdrop Image (0ms – 600ms):**
   - Initial state: `opacity: 0; transform: scale(1.04);`
   - Settles to: `opacity: 1; transform: scale(1.00);` via `cubic-bezier(0.16, 1, 0.3, 1)`.
2. **Editorial Title & Vignette (150ms – 550ms):**
   - Slides up: `translateY(16px) → translateY(0)` with fade in.
3. **Personalization Badge & Metadata (300ms – 650ms):**
   - Matches score pill lights up with subtle ambient gold glow.
4. **Action Cluster (400ms – 750ms):**
   - `[ Watch Trailer ]`, `[ + Add to Watchlist ]`, and `[ Rate ]` buttons become interactive.

---

## 7. Movie Card Default State

- **Aspect Ratio:** `2:3` standard theatrical vertical poster format (e.g., `w-56 h-84` or responsive equivalent).
- **Poster Treatment:** Sharp, high-fidelity film artwork with a bottom 40% vertical gradient (`linear-gradient(to top, rgba(13,14,18,0.95), transparent)`).
- **Default Visual Elements:**
  - Top Left: Personalized Match Pill (e.g., `96% MATCH` in amber pill with dark background).
  - Bottom Surface: Movie Title (Medium serif/sans), release year, director or genre tag, star rating (`★ 4.8`).
- **Border:** `1px solid rgba(255, 255, 255, 0.08)`.
- **Corner Radius:** `rounded-lg` (8px–10px, restrained).

---

## 8. Movie Card Hover State (The Signature Interaction)

When a curator hovers over any movie card in a recommendation row:

1. **Scale & Depth (Timing: 240ms cubic-bezier(0.2, 0.8, 0.2, 1)):**
   - Card scales to `1.04x` (subtle, never overflowing neighbor hitboxes).
   - Z-index elevates (`z-20` or `z-30`).
   - Shadow deepens to `elevation-hover`.
2. **Backdrop Cross-Fade (Optional High-Fidelity Asset):**
   - If available, horizontal cinematic still dissolves over poster (`opacity: 0.85`).
3. **Content Expansion (Upward Reveal):**
   - Synopsis excerpt (2 lines maximum) slides into view (`translateY(0)` from `translateY(8px)`).
   - Genre chips display.
   - Action cluster slides in: `[ Details ]`, `[ + Watchlist ]`, `[ ★ Rate ]`.
4. **Neighboring Cards:** Do NOT shrink or shake. Neighboring cards remain completely stable.

---

## 9. Dynamic Ambient Movie Backdrop

- **Atmospheric Reflection:** Hovering a movie card triggers a subtle, blurred ambient color wash across the global background canvas (`filter: blur(80px); opacity: 0.18;`).
- **Darkening Guarantee:** Global darkness is preserved; text readability never drops below WCAG AAA.
- **Hover Leave:** Smoothly dissolves back to `#0d0e12` over `400ms` with zero abrupt flicker.
- **Missing Backdrop Fallback:** Gracefully utilizes poster color temperature or maintains neutral dark surface.

---

## 10. Match Score & Telemetry Animation

- **Score Meter Animation:**
  - Runs once when scrolled into view (e.g. `0% → 96%` over `480ms`).
  - Utilizes a smooth ease-out curve (`cubic-bezier(0.16, 1, 0.3, 1)`).
- **No Infinite Reruns:** Once animated, the score remains static during user exploration. Does not re-trigger on micro-scrolls.
- **Visual Breakdown Bars:** Progress fills from left to right (`width: 0% → 94%`) accompanied by natural language curatorial evidence.

---

## 11. Buttons & Interactive Controls

| Control Type | Normal State | Hover State | Active / Pressed |
| :--- | :--- | :--- | :--- |
| **Primary CTA** | Warm gold background (`#f59e0b`), dark slate text (`#0d0e12`), font-medium | Bright amber (`#d97706`), `box-shadow: 0 0 16px rgba(245,158,11,0.3)` | Scale `0.98`, darker amber (`#b45309`) |
| **Secondary CTA** | Surface low (`#1a1b20`), border `white/10`, text `slate-200` | Surface high (`#23252b`), border `white/25`, text `white` | Scale `0.98`, surface elevated |
| **Ghost / Tertiary** | Transparent, text `slate-400` | Text `slate-100`, background `white/5` | Text `amber-500` |
| **Icon Button** | `w-10 h-10` circle/rounded square, `bg-white/5`, border `white/10` | `bg-white/10`, border `white/20`, text `white` | Scale `0.92`, gold icon state |

---

## 12. Instant Micro-Feedback & Toasts

### 12.1 Interactive State Changes
- **Watchlist Toggle:**
  - `+ Add to Watchlist` $\longrightarrow$ `✓ On Watchlist` (icon rotates 90° smoothly, border transitions to gold).
- **Like Toggle:**
  - Outline heart $\longrightarrow$ Filled amber heart with micro-scale pulse (`1.0 → 1.2 → 1.0`).
- **Rating Stars:**
  - Hover highlights stars up to mouse pointer in warm amber; clicking locks in rating with momentary particle shimmer.

### 12.2 Curatorial Toast System
- **Placement:** Bottom-right corner (`fixed bottom-8 right-8 z-50`).
- **Style:** Compact pill, `surface-elevated` (`#23252b`), gold icon glyph, subtle border (`border-amber-500/30`), backdrop blur.
- **Duration:** 3200ms auto-dismiss with linear progress drain.
- **Copy Examples:**
  - *"Blade Runner 2049 added to your screening watchlist"*
  - *"Taste profile calibrated with Denis Villeneuve affinity"*
  - *"Rating recorded (5.0 ★)"*

---

## 13. Skeleton Loading & Cinematic States

- **No Jarring White Flashes:** All skeletons use dark charcoal bases (`#16171d`) with an amber-tinted dark sweep (`linear-gradient(90deg, transparent, rgba(255,255,255,0.04), transparent)`).
- **Card Skeletons:** Preserve exact `2:3` aspect ratio; zero Cumulative Layout Shift (CLS = 0).
- **Curatorial Progress Messages:** Replace generic "Loading..." with evocative cinematic updates:
  - *"Analyzing directorial continuity..."*
  - *"Synthesizing atmospheric recommendations..."*
  - *"Calibrating your personal film canon..."*

---

## 14. Empty & Error States

- **Tone:** Respectful, inspiring, and curatorial. Never dead-end or technical.
- **Empty Watchlist:** *"Your screening room is quiet. Add films from Explore or your personalized slate to start your queue."* CTA: `[ Explore Atmospheric Masterpieces ]`.
- **Zero Discovery Matches:** *"No titles match this exact intersection of mood, era, and runtime. Broaden your curatorial sliders to reveal nearby gems."* CTA: `[ Reset Discovery Filters ]`.
- **Service Disruption:** *"Curatorial connection momentarily disrupted. Your taste vector is safely preserved in local telemetry."* CTA: `[ Reconnect Screening Engine ]`.

---

## 15. The Signature Popcorn Cursor & Easter Egg 🍿

### 15.1 Custom Popcorn Pointer Concept
- **Concept:** A subtle, ultra-refined custom pointer accessory that reinforces MoieRec's passion for cinema without ever descending into cartoonishness.
- **Default Motion:** Tiny, clean 14px monochrome-gold popcorn kernel glyph floating 8px adjacent to the primary cursor dot.
- **Card Hover:** Kernel gently illuminates with a faint golden ambient aura (`box-shadow: 0 0 10px rgba(245,158,11,0.4)`).
- **Button Hover:** Smoothly collapses into a standard precise cursor pointer to maintain functional clarity for clicking.
- **Click Event:** Micro-burst of 3 tiny golden spark particles that dissipate over 200ms.
- **Accessibility Switch:** Persistent toggle in Footer / Settings: `[ Enable / Disable Cinematic Cursor ]`. Defaults to system pointer for users with touch or motor sensitivity.

### 15.2 Curatorial Scroll Progress Easter Egg
- A miniature, minimalist popcorn bucket vector anchored in the footer or bottom navigation track.
- As the user scrolls vertically through long recommendation rows, the bucket gradually fills with golden kernels proportional to page scroll depth (0% to 100%).
- Upon reaching the editorial footer: Displays a quiet congratulatory message: *"Movie night complete. 🍿 Ready for the screening room."*

---

## 16. Multi-Screen Page Transitions

- **Route Transition:** `fade-out (120ms)` $\longrightarrow$ `fade-in (200ms)` with a `10px` upward ease.
- **Shared Elements:** Nav bar and background void stay fixed, preventing screen flicker.
- **Preserved Scroll Position:** Navigating back from *Movie Detail* to *Home* or *Explore* restores exact scroll coordinates.

---

## 17. Search & Discovery Flyout

- **Activation:** Clicking `Search` in the top nav or pressing `Cmd + K` / `Ctrl + K`.
- **Layout:** Command-palette overlay (`max-w-2xl mx-auto mt-24`) with `backdrop-blur-xl`.
- **Multi-Vector Queries:** Instant categorization across *Titles*, *Directors*, *Auteurs*, *Cinematographers*, and *Thematic Tropes*.
- **Live Preview:** Highlights title, year, and personalized match percentage inline.

---

## 18. Accessibility & Reduced Motion Matrix

| System Behavior | Standard Mode | Reduced Motion (`prefers-reduced-motion`) |
| :--- | :--- | :--- |
| **Card Hover** | Scale `1.04x` + shadow expand + synopsis reveal | Instant visual border highlight, no scale transform |
| **Scroll Reveal** | `translateY(24px) → 0` + `blur(4px) → 0` | Instant opacity 1, zero translate, zero blur |
| **Ambient Backdrop**| Smooth 400ms color bloom on canvas | Static neutral dark surface |
| **Match Score** | Counter counts up `0% → 96%` | Renders directly at `96%` |
| **Popcorn Cursor** | Animated follower + click burst | Disabled (native system cursor only) |
| **Focus Rings** | Subtle gold ring (`ring-2 ring-amber-500/70`) | High-contrast double ring (`outline: 2px solid #f59e0b`) |

---

## 19. Responsive Adaptation Rules

1. **Desktop (1280px – 1920px+):**
   - Full 5-column or 6-column movie recommendation rows.
   - Dual-column Movie Detail (Hero backdrop + side-by-side explainability matrices).
   - Rich hover cards with expanded synopses and action buttons.
2. **Tablet (768px – 1024px):**
   - 3 to 4-column movie rows; horizontal swipe gesture enabled.
   - Hover actions available via single-tap preview modal or bottom sheet.
3. **Mobile (< 768px):**
   - 2-column grid or single-row carousel with 1.3 card peek.
   - Bottom fixed navigation bar replacing top horizontal links.
   - Explainability bars stack vertically; font scales adapt by -15%.

---

## 20. MoieRec Curatorial Philosophy (Guiding Compass)

Every design token, interaction curve, and visual flourish must serve one primary mission:
> *"MoieRec is not a commodity video catalog; it is an intelligent, transparent sanctuary for cinema lovers. Every recommendation must be explainable, every interaction must feel cinematic, and the user must always hold the master controls to their own taste."*
