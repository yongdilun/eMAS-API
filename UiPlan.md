Linear UI Upgrade Implementation Plan
Based on the DESIGN-linear.app.md specifications, this plan outlines a 5-stage approach to upgrading the entire eMas Front application to the new dual-theme (Light/Dark) Linear design system.

Stage 1: Foundation & Theming Setup
Objective: Establish the design tokens (colors, typography, spacing, shapes) to support the dual-theme Linear aesthetic across the application.

Tailwind/CSS Configuration: Update tailwind.config.js and index.css (or src/styles/*) to include all design tokens from the markdown file.
Dual-Theme Architecture: Implement a robust light/dark mode toggling system.
Dark Mode (Default): Implement the #010102 canvas, surface-1 through surface-4 lifts, and hairline border variables.
Light Mode: Implement the #ffffff canvas and its respective light surfaces and hairlines.
Typography: Configure Linear Display, Linear Text, and Linear Mono (with fallbacks SF Pro Display / Inter / JetBrains Mono). Apply the aggressive negative letter-spacing for display text.
Spacing & Radii: Implement the 4px base spacing scale and border-radius tokens (xs to pill).
Global Overrides: Remove any existing drop shadows, gradients, and unauthorized semantic colors across global styles.
Stage 2: Core Shared Components Upgrade
Objective: Upgrade all foundational atomic components in src/components/shared to strict Linear guidelines.

Button.jsx: Implement button-primary (lavender), button-secondary (charcoal), button-tertiary, and button-inverse variants. Ensure correct padding (8px 14px), typography, and rounded-md (8px). Add hover and pressed states.
Card.jsx: Apply surface-1 background, 1px hairline border, and rounded.lg (12px) or rounded.xl (16px) depending on the context. Ensure zero drop shadows in dark mode.
Modal.jsx: Implement semantic-overlay (pure black scrim) and use surface-1 or surface-2 for the modal body.
Inputs & Badges: Upgrade form elements (text inputs, selects) to use the 2px primary-focus outline at 50% opacity. Implement the status-badge (rounded.pill, surface-2, ink-muted).
EmptyState.jsx & Loading.jsx: Refine styling to use ink-muted and ink-subtle colors with sparse, clean typography.
Stage 3: Layout & Navigation Upgrade
Objective: Apply the dense, technical software-craft aesthetic to the application's shell and routing structures.

Header.jsx / PageHeader.jsx: Implement the top-nav spec (canvas background, 56px height, ink text).
Sidebar.jsx & MobileMenu.jsx: Style navigational menus to utilize surface-3 for active states or lifts, maintaining 1px hairlines to separate the sidebar from the main content canvas.
Layout.jsx: Ensure the main content wrapper strictly uses the canvas background color and controls max-widths correctly for the 1280px grid.
Responsive Collapsing: Ensure proper hamburger menu collapsing below 768px, as specified in the design doc.
Stage 4: Feature Components & Complex UI Upgrade
Objective: Upgrade the domain-specific components inside src/components/features (charts, forms, scheduling, predictive, etc.).

Table.jsx & Lists: Use changelog-row patterns. Implement strict 1px hairline bottom borders for rows. Use ink-muted for headers and ink for data.
FilterSortPanel.jsx & Forms (Forms.jsx, RefSelect.jsx): Refactor complex filter panels. Ensure all inputs use the text-input spec and utilize pricing-tab pill toggles for multi-selects.
Data Visualization (Charts/Gantt): Ensure charts in charts and gantt directories use the approved ink, ink-muted, and primary (lavender) colors. Remove unauthorized bright accents (reds/greens) unless conveying strict semantic success/failure.
Floating Actions (FloatingChatButton.jsx): Align the floating chat with the button-primary or button-inverse spec with appropriate focus rings.
Stage 5: Full Page Assembly & Polish
Objective: Assemble the upgraded components onto the main views in src/pages and conduct a final visual QA.

Page Upgrades: Systematically update all pages:
Dashboard.jsx & Reports.jsx
Jobs.jsx & Products.jsx
MachineResources.jsx & StorageInventory.jsx
Scheduling.jsx & PredictiveAnalysis.jsx
ShortageResolution.jsx & ProductionData.jsx
Settings.jsx & AIAssistantChat.jsx
"Product Screenshot" Aesthetic: Structure major page sections into surface-1 panels with rounded.xl (16px) corners. Let the dark/light canvas act as the whitespace (spacing.section / 96px gaps between major blocks).
Typography QA: Verify the transition from display headlines to body text on every page, ensuring negative tracking and weights are applied perfectly.
Dual-Theme Verification: Toggle between Light and Dark mode on every page to guarantee contrast, surface lifts, and hairline borders render correctly without relying on shadows.