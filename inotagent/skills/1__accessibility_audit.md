---
name: accessibility_audit
description: WCAG 2.2 accessibility audit workflow with screen reader testing, keyboard navigation, and ARIA patterns
tags: [testing, accessibility, wcag, a11y]
source: agency-agents/testing/testing-accessibility-auditor
---

## Accessibility Audit

> ~1800 tokens

### WCAG 2.2 Audit Checklist (POUR Principles)

**Perceivable**
- All images have appropriate alt text (decorative = `alt=""`, informative = descriptive)
- Color contrast: normal text >= 4.5:1, large text >= 3:1 (WCAG 1.4.3)
- Content readable at 200% and 400% zoom without horizontal scroll
- Media has captions/transcripts

**Operable**
- All interactive elements reachable via Tab in logical order
- No keyboard traps (can always Tab away from any element)
- Focus indicator visible on every interactive element
- Skip navigation link present and functional

**Understandable**
- Form labels associated with inputs; required fields announced
- Error messages identify the field and suggest correction
- Consistent navigation and naming across pages

**Robust**
- Semantic HTML used before ARIA (best ARIA = no ARIA needed)
- Custom components have correct ARIA roles, states, properties
- Content works across screen readers (VoiceOver, NVDA, JAWS)

### Screen Reader Testing Protocol

1. **Setup**: Note screen reader + browser + OS versions
2. **Navigation**: Verify heading hierarchy (h1>h2>h3), landmark regions (main, nav, banner), skip links
3. **Interactive components**:
   - Buttons: announced with role + label, state changes announced
   - Forms: labels read, required announced, errors identified
   - Modals: focus trapped inside, Escape closes, focus returns to trigger
   - Custom widgets (tabs, accordions, menus): proper ARIA roles + keyboard patterns
4. **Dynamic content**: live regions announce status without focus change, loading states communicated, toasts via aria-live

### Keyboard Navigation Checklist

**Global**
- [ ] All interactive elements reachable via Tab
- [ ] Tab order follows visual layout
- [ ] Escape closes modals/dropdowns/overlays
- [ ] Focus returns to trigger after modal close

**Tabs**: Arrow keys between tabs, Tab into panel content, aria-selected on active
**Menus**: Arrow keys navigate, Enter/Space activates, Escape closes + returns focus
**Data Tables**: headers via scope/headers attributes, caption or aria-label

### Common ARIA Anti-Patterns
- `aria-label` on non-interactive elements (ignored by most screen readers)
- Redundant roles on semantic HTML (`role="button"` on `<button>`)
- `aria-hidden="true"` on focusable elements (creates ghost focus)
- Missing `aria-expanded` on disclosure triggers
- Using `aria-live="assertive"` for non-urgent updates

### Severity Classification
- **Critical**: Blocks access entirely (missing form labels, keyboard traps, no alt on functional images)
- **Serious**: Major barrier requiring workarounds (broken focus management, missing ARIA on custom widgets)
- **Moderate**: Causes difficulty but has workarounds (low contrast on secondary text, missing skip links)
- **Minor**: Usability annoyance (focus order slightly off, redundant ARIA)

### Audit Report Template

```
# Accessibility Audit Report
Product/Feature: [scope]
Standard: WCAG 2.2 Level AA
Tools: axe-core, Lighthouse, [screen reader], keyboard testing

## Summary
Total Issues: [n] | Critical: [n] | Serious: [n] | Moderate: [n] | Minor: [n]
Conformance: DOES NOT CONFORM / PARTIALLY CONFORMS / CONFORMS

## Issues
### [Title]
- WCAG Criterion: [number - name] (Level A/AA)
- Severity: Critical/Serious/Moderate/Minor
- User Impact: [who affected, how]
- Location: [page, component]
- Current: [code/behavior]
- Fix: [code/behavior]
- Verify: [how to confirm fix works]

## Remediation Priority
Immediate (Critical/Serious): [list]
Short-term (Moderate): [list]
Ongoing (Minor): [list]
```

### Automated Baseline Commands
```bash
npx @axe-core/cli <url> --tags wcag2a,wcag2aa,wcag22aa
npx lighthouse <url> --only-categories=accessibility --output=json
```

Note: Automated tools catch ~30% of issues. Manual screen reader + keyboard testing required for the other 70%.
