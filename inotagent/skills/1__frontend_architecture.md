---
name: frontend_architecture
description: CSS architecture patterns, layout strategies, responsive breakpoints, component structure, naming conventions, and theme systems
tags: [frontend, css, architecture, layout, responsive, theming]
source: agency-agents/design/design-ux-architect.md
---

## Frontend Architecture

> ~2400 tokens

### CSS File Organization

```
css/
  design-system.css  # Variables, tokens, theme definitions
  layout.css         # Container, grid, flexbox utilities
  components.css     # Reusable component styles
  utilities.css      # Helper classes
  main.css           # Project-specific overrides
```

### Design System Variables Template

```css
:root {
  --bg-primary: #ffffff;  --bg-secondary: #f9fafb;
  --text-primary: #111827;  --text-secondary: #6b7280;
  --border-color: #e5e7eb;  --primary-color: #3b82f6;
  /* Typography: 12/14/16/18/20/24/30px */
  --text-xs: 0.75rem;  --text-sm: 0.875rem;  --text-base: 1rem;
  --text-lg: 1.125rem; --text-xl: 1.25rem;   --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  /* Spacing (4px base): 4/8/16/24/32/48/64px */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-4: 1rem;
  --space-6: 1.5rem;  --space-8: 2rem;   --space-12: 3rem; --space-16: 4rem;
  /* Container widths */
  --container-sm: 640px; --container-md: 768px;
  --container-lg: 1024px; --container-xl: 1280px;
}
[data-theme="dark"] {
  --bg-primary: #0f172a; --bg-secondary: #1e293b;
  --text-primary: #f1f5f9; --text-secondary: #94a3b8;
  --border-color: #334155;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg-primary: #0f172a; --bg-secondary: #1e293b;
    --text-primary: #f1f5f9; --text-secondary: #94a3b8;
    --border-color: #334155;
  }
}
body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  transition: background-color 0.3s ease, color 0.3s ease;
}
```

### Theme Toggle Pattern

```html
<div class="theme-toggle" role="radiogroup" aria-label="Theme selection">
  <button class="theme-toggle-option" data-theme="light" role="radio">Light</button>
  <button class="theme-toggle-option" data-theme="dark" role="radio">Dark</button>
  <button class="theme-toggle-option" data-theme="system" role="radio">System</button>
</div>
```

JS: Read `localStorage.getItem('theme')` or detect via `matchMedia('(prefers-color-scheme: dark)')`. Set `data-theme` attribute on `documentElement`. For "system", remove the attribute and let the CSS media query handle it.

### Layout Patterns

| Pattern        | CSS                                              | Use when              |
|----------------|--------------------------------------------------|-----------------------|
| Container      | `max-width: var(--container-lg); margin: 0 auto` | Page wrapper          |
| 2-col grid     | `grid-template-columns: 1fr 1fr`                 | Content sections      |
| Auto-fit cards | `grid-template-columns: repeat(auto-fit, minmax(300px, 1fr))` | Card grids |
| Sidebar        | `grid-template-columns: 2fr 1fr`                 | Main + aside          |
| Hero           | `min-height: 100vh; place-items: center`          | Landing sections      |

Collapse all grids to `1fr` on mobile (`max-width: 768px`).

### Component Hierarchy (build order)

1. **Layout**: containers, grids, sections
2. **Content**: cards, articles, media blocks
3. **Interactive**: buttons, forms, navigation
4. **Utility**: spacing helpers, typography classes, visibility

### Naming Conventions

- Use **semantic color names** (`--bg-primary`) not literal (`--color-white`)
- Use **BEM** for components: `.card`, `.card__title`, `.card--featured`
- Use **utility prefixes** for helpers: `.text-heading-1`, `.grid-2-col`

### Responsive Strategy

| Tier    | Width     | Padding        | Notes                   |
|---------|-----------|----------------|-------------------------|
| Mobile  | 320-639px | `--space-4`    | Base design, single col |
| Tablet  | 640-1023px| `--space-4`    | 2-col layouts           |
| Desktop | 1024-1279px| `--space-6`   | Full feature set        |
| Large   | 1280px+   | `--space-8`    | Wider containers        |

### Grid vs Flexbox Decision

- **CSS Grid**: 2D layouts, card grids, page structure, anything with rows AND columns
- **Flexbox**: 1D alignment, nav bars, button groups, centering, spacing within a row/column

### Implementation Priority

1. Design system variables (tokens + theme)
2. Layout structure (container + grid)
3. Component base styles
4. Content integration with proper hierarchy
5. Interactive polish (hover, transitions, animations)

### Performance Checklist

- [ ] Critical CSS inlined in `<head>`
- [ ] Non-critical CSS loaded async
- [ ] No unused CSS shipped
- [ ] `prefers-reduced-motion` respected
- [ ] Images lazy-loaded
- [ ] Web fonts preloaded with `font-display: swap`
