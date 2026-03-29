---
name: ui_design_systems
description: Design token structure, component checklist, color system, typography/spacing scales, and layout grid rules for UI design systems
tags: [design, ui, css, tokens, components, accessibility]
source: agency-agents/design/design-ui-designer.md
---

## UI Design Systems

> ~2800 tokens

### Design Token Structure

```css
:root {
  /* Color Tokens (use 100-900 scale) */
  --color-primary-100: #f0f9ff;
  --color-primary-500: #3b82f6;
  --color-primary-900: #1e3a8a;
  --color-secondary-100: #f3f4f6;
  --color-secondary-500: #6b7280;
  --color-secondary-900: #111827;

  /* Semantic Colors */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;

  /* Typography Scale */
  --font-size-xs: 0.75rem;    /* 12px */
  --font-size-sm: 0.875rem;   /* 14px */
  --font-size-base: 1rem;     /* 16px */
  --font-size-lg: 1.125rem;   /* 18px */
  --font-size-xl: 1.25rem;    /* 20px */
  --font-size-2xl: 1.5rem;    /* 24px */
  --font-size-3xl: 1.875rem;  /* 30px */
  --font-size-4xl: 2.25rem;   /* 36px */

  /* Spacing Scale (4px base unit) */
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */

  /* Shadows (elevation system) */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 300ms ease;
  --transition-slow: 500ms ease;
}

/* Dark Theme: invert semantic direction of scale */
[data-theme="dark"] {
  --color-primary-100: #1e3a8a;
  --color-primary-500: #60a5fa;
  --color-primary-900: #dbeafe;
  --color-secondary-100: #111827;
  --color-secondary-500: #9ca3af;
  --color-secondary-900: #f9fafb;
}
```

### Responsive Breakpoints (mobile-first)

| Breakpoint | Min-width | Container max-width |
|------------|-----------|---------------------|
| Base       | 0         | 100%                |
| sm         | 640px     | 640px               |
| md         | 768px     | 768px               |
| lg         | 1024px    | 1024px              |
| xl         | 1280px    | 1280px              |

### Component Checklist

For each component, define all of these:

- [ ] **Variants**: primary, secondary, tertiary (or ghost/outline)
- [ ] **Sizes**: sm, md, lg
- [ ] **States**: default, hover, active, focus-visible, disabled
- [ ] **Loading state**: skeleton or spinner
- [ ] **Error state**: validation feedback
- [ ] **Empty state**: no-data messaging
- [ ] **Dark mode**: token-based, not hardcoded colors
- [ ] **Accessibility**: focus ring (2px outline, 2px offset), ARIA attributes

### Base Components to Define

| Category      | Components                                  |
|---------------|---------------------------------------------|
| Interactive   | Button, Input, Select, Checkbox, Radio      |
| Navigation    | Menu, Breadcrumb, Pagination, Tabs          |
| Feedback      | Alert, Toast, Modal, Tooltip                |
| Data display  | Card, Table, List, Badge, Tag               |
| Layout        | Container, Grid, Stack, Divider             |

### Accessibility Minimums (WCAG AA)

| Rule              | Requirement                                     |
|-------------------|------------------------------------------------|
| Color contrast    | 4.5:1 normal text, 3:1 large text              |
| Touch targets     | 44px minimum                                    |
| Focus indicators  | Visible outline on all interactive elements     |
| Motion            | Respect `prefers-reduced-motion`                |
| Text scaling      | Works up to 200% browser zoom                   |
| Keyboard          | Full functionality without mouse                |

### Design System Documentation Template

```markdown
# [Project] Design System

## Color System
- Primary: [hex values, 100-900 scale]
- Secondary: [hex values]
- Semantic: success, warning, error, info
- Neutrals: grayscale for text/backgrounds
- Accessibility: list all compliant color pairings

## Typography
- Primary font: [family] for headings/UI
- Secondary font: [family] for body/code
- Scale: 12/14/16/18/20/24/30/36px
- Weights: 400, 500, 600, 700
- Line heights: 1.2 (headings), 1.5 (body), 1.6 (reading)

## Spacing
- Base unit: 4px
- Scale: 4/8/12/16/24/32/48/64px

## Components
[For each: variants, sizes, states, code example]

## Responsive
[Breakpoints, container rules, grid behavior]
```
