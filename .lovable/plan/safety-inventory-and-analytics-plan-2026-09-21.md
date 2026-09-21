# Safety, Inventory, and Analytics Plan

## Safety Monitoring

- Add `/safety` with the requested safety status, date range, four KPI cards, seven-day incident chart, active alerts, and searchable/filterable event history.
- Add an accessible event detail dialog opened from each table row, using mock data only.

## Inventory

- Add `/inventory` in the established command-center style with inventory KPIs, stock distribution and movement charts, searchable/filterable inventory records, and item details using mock data.

## Analytics

- Add `/analytics` with operational KPIs, range controls, worker/forklift activity, inventory flow, safety trend, zone performance, and mock performance summaries.

## Shared Navigation and Quality

- Connect Safety, Inventory, and Analytics in the existing shared sidebar without changing Dashboard or Live Camera visuals.
- Add unique page metadata, responsive layouts, accessible controls, and verify desktop/mobile interactions and preview health.

## Technical Details

- Reuse current React, TypeScript, Tailwind, shadcn/ui, Lucide, Recharts, shared tokens, typography, background treatment, and sidebar.
- Keep all behavior client-side with local mock data; no backend, authentication, APIs, or persistence.
