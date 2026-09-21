# WarehouseVision AI Dashboard Plan

## Overview

Build the existing `/` screen into a polished, frontend-only warehouse monitoring command center. All values, alerts, detections, charts, controls, and statuses will use local mock data with no backend, authentication, database, or AI integration.

## Interface

- Create a fixed dark-navy sidebar with WarehouseVision AI branding, the seven requested navigation items, active-state styling, and an AI Engine Online status.
- Add a compact mobile navigation treatment so the dashboard remains usable on smaller screens while preserving the desktop command-center layout.
- Build the header with warehouse title/subtitle, warehouse selector, Monitoring Active status, notifications, and user avatar.
- Add four reusable KPI cards for workers, forklifts, visible inventory, and safety alerts.
- Use the uploaded warehouse photo as the dashboard background with a strong navy overlay; keep the sidebar opaque for readability.

## Monitoring Content

- Build a large CCTV-style Live Camera panel with mock image treatment, LIVE badge, camera label, FPS/object/model indicators, camera controls, and fullscreen interaction.
- Overlay labeled detection boxes for Worker #12, Forklift #3, and Box #27.
- Build the Recent Safety Alerts panel with the three requested incidents, severity hierarchy, timestamps, and clear status coloring.
- Add Zone Occupancy progress bars using mock zone capacities.
- Add Operational Analytics with responsive Recharts visualizations for worker/forklift activity and inventory movement.

## Design System

- Apply the supplied industrial palette through semantic theme tokens, including background, sidebar, cards, borders, amber accent, success, danger, foreground, and muted text.
- Use clean typography, compact data-dense spacing, subtle borders, restrained motion, and Lucide icons.
- Use reusable components and existing project conventions; avoid gradients and decorative clutter.
- Add page-specific title, description, Open Graph, and Twitter metadata for WarehouseVision AI.

## Functional Details

- Make selectors, sidebar controls, notifications, camera buttons, and fullscreen behavior respond visibly using local React state only.
- Provide accessible labels, keyboard focus states, readable contrast, and stable layouts across desktop and mobile.
- Keep all mock data centralized and easy to adjust.

## Verification

- Confirm the page compiles without errors.
- Test the dashboard in the running preview at desktop and mobile widths.
- Verify navigation states, selector behavior, camera controls/fullscreen, chart rendering, image overlay readability, and absence of content overlap.
