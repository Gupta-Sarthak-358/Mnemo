---
name: Mnemo Design System
colors:
  surface: '#121414'
  surface-dim: '#121414'
  surface-bright: '#38393a'
  surface-container-lowest: '#0c0f0f'
  surface-container-low: '#1a1c1c'
  surface-container: '#1e2020'
  surface-container-high: '#282a2b'
  surface-container-highest: '#333535'
  on-surface: '#e2e2e2'
  on-surface-variant: '#c3c6d4'
  inverse-surface: '#e2e2e2'
  inverse-on-surface: '#2f3131'
  outline: '#8d909e'
  outline-variant: '#424752'
  surface-tint: '#aec6ff'
  primary: '#aec6ff'
  on-primary: '#002e6b'
  primary-container: '#5d8ef1'
  on-primary-container: '#00275e'
  inverse-primary: '#1e5bba'
  secondary: '#b5c6f2'
  on-secondary: '#1e3053'
  secondary-container: '#35466b'
  on-secondary-container: '#a4b5df'
  tertiary: '#ffb960'
  on-tertiary: '#472a00'
  tertiary-container: '#ca8103'
  on-tertiary-container: '#3e2400'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#aec6ff'
  on-primary-fixed: '#001a43'
  on-primary-fixed-variant: '#004397'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#b5c6f2'
  on-secondary-fixed: '#061a3d'
  on-secondary-fixed-variant: '#35466b'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb960'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#121414'
  on-background: '#e2e2e2'
  surface-variant: '#333535'
typography:
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  chip-label:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  section-cap:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.08em
  body-xs:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-margin: 24px
  gutter: 16px
  card-padding: 12px
  stack-gap: 8px
  element-gap: 4px
---

## Brand & Style
The design system is engineered for a "local-first" memory engine, prioritizing speed, focus, and longevity. The brand personality is quiet, dependable, and unobtrusive—acting as an extension of the user's mind rather than a loud external tool.

The aesthetic leans heavily into **High-Utility Minimalism** with a **Native Desktop** feel. It draws inspiration from high-performance productivity tools, utilizing a dark-mode-first approach to reduce eye strain during long periods of deep thought. The interface avoids ephemeral trends like glassmorphism or vibrant gradients, opting instead for a structured, architectural layout that feels grounded and permanent. The emotional response should be one of "calm control."

## Colors
This design system utilizes a strictly controlled monochromatic base with a single functional accent. 

- **Primary Canvas**: The `#0F0F0F` background provides a deep, non-distracting void.
- **Surface Layers**: `#1A1A1A` is used for cards and containers to create subtle separation.
- **Borders**: Interactive and structural elements use `#2A2A2A`. On hover or focus, these brighten to `#3A3A3A` to provide tactile feedback without color shifts.
- **Accent**: `#5B8DEF` (Calm Blue) is reserved for primary actions, active states, and specific "Page" metadata to guide the eye toward navigation.
- **Functional Chips**: Distinct background logic separates general concepts (`#252525`) from navigational pages (`#1E2A3A`).

## Typography
The system relies exclusively on **Inter** to maintain a utilitarian, system-level feel that integrates seamlessly with desktop OS environments.

- **Information Hierarchy**: Titles are kept small (16px) to maximize information density. 
- **Muted Metadata**: Authors, timestamps, and secondary details use the `body-sm` role with a muted color hex to keep the focus on the content.
- **Section Headers**: Use the `section-cap` role to provide clear structural breaks without needing heavy lines or large font sizes. 
- **Readability**: Line heights are optimized for short-form snippets and list-based navigation typical of a memory engine.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy for the sidebar and utility panels, with a **Fluid Center** for the content engine.

- **The 8px Rule**: All spacing increments are based on an 8px scale (4, 8, 16, 24, 32) to ensure a rhythmic density.
- **Sidebar**: Fixed at 240px–280px depending on user preference, containing high-density navigation.
- **Command Bar**: Centered horizontally, mimicking the "Raycast" pattern with consistent 16px internal padding.
- **Content Feed**: Uses a single-column stack with 8px gaps between cards to maintain a list-like feel.

## Elevation & Depth
Elevation is achieved through **Tonal Layering** and **Crisp Borders** rather than dramatic shadows.

- **Level 0 (Background)**: `#0F0F0F` is the furthest back.
- **Level 1 (Surface)**: Cards and panels use `#1A1A1A` with a 1px solid border of `#2A2A2A`.
- **Level 2 (Interaction)**: Hovered states or active modals utilize a subtle ambient shadow: `0px 4px 12px rgba(0, 0, 0, 0.5)`.
- **Depth Markers**: Use the "brightening border" technique—when an element is focused, its border transitions from `#2A2A2A` to `#3A3A3A` to simulate a physical rise toward the light source.

## Shapes
The shape language balances modern software aesthetics with high-density utility.

- **Windows/Main Containers**: Use `rounded-xl` (1.5rem / 24px) or `rounded-lg` (1rem / 16px) depending on the OS environment.
- **Cards & Primary UI**: Standardized at 8px (base `roundedness: 2`).
- **Inner Elements**: Chips, inputs, and buttons use a tighter 6px radius to appear "nested" correctly within 8px cards.

## Components
- **Cards**: Background `#1A1A1A`, 1px border `#2A2A2A`, 8px corner radius. Padding is 12px.
- **Concept Chips**: Rounded 6px, background `#252525`, text `#AAAAAA`, no border.
- **Page Chips**: Rounded 6px, background `#1E2A3A`, text `#5B8DEF`.
- **Input Fields**: No background (transparent) when inactive; `#1A1A1A` with `#3A3A3A` border when focused. Text is `#E8E8E8`.
- **Primary Button**: Background `#5B8DEF`, text `#0F0F0F` (high contrast) or `#FFFFFF`, 6px radius.
- **Ghost Button**: No background, border `#2A2A2A` on hover only, text `#888888`.
- **Command Palette**: Large modal, 12px radius, heavy 24px shadow, internal search input with no border, items separated by 4px gaps.