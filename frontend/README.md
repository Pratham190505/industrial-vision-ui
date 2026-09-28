# Warehouse Command

Build a polished frontend dashboard for WarehouseVision AI, an AI-powered warehouse computer vision monitoring system.

Important: Focus ONLY on creating the frontend UI. Use mock data. Do not implement backend, AI models, APIs, authentication, or database integration.

Design

Create a dark industrial warehouse command-center dashboard with a fixed left sidebar and spacious main content.

Use this color palette:

Background: #111827

Sidebar: #0B1220

Cards: #1E293B

Borders: #334155

Primary accent: #F59E0B (industrial amber)

Success: #22C55E

Danger: #EF4444

Text: #F8FAFC

Muted text: #94A3B8

Background Image

Use the uploaded warehouse image as a subtle full-page background on the Dashboard. Apply a dark navy overlay (around 80% opacity) so the image is visible but does not reduce readability. Keep the sidebar solid dark navy.

Layout

Sidebar:

WarehouseVision AI logo and name

Dashboard

Live Camera

Inventory

Safety

Analytics

Reports

Settings

Bottom status: 🟢 AI Engine Online

Main Dashboard:

Header:

Title: Warehouse Overview

Subtitle: Real-time monitoring and operational intelligence

Warehouse selector

Monitoring Active status

Notification icon

User avatar

Four KPI cards:

Active Workers — 24

Active Forklifts — 5

Visible Inventory — 127

Safety Alerts — 3

Main content:
Create a large Live Camera panel on the left and Recent Safety Alerts panel on the right.

Live Camera:

Title: Live Camera

Green LIVE indicator

Camera label: CAM-01 | Main Warehouse

Use a dark CCTV-style placeholder

Add mock detection bounding boxes labeled:

Worker #12

Forklift #3

Box #27

Show small indicators: 24 FPS, 32 Objects Tracked, YOLO Active

Add fullscreen and camera controls

Recent Safety Alerts:

Worker–Forklift Proximity — Worker #12 near Forklift #3 — High

Restricted Zone Entry — Worker #07 entered Zone A — Medium

PPE Compliance Check — Worker #18 missing safety vest — Medium

Below these, add:

Zone Occupancy with progress bars

Operational Analytics with a Worker/Forklift activity chart and Inventory Movement chart

Technical Requirements

React + TypeScript

Tailwind CSS

shadcn/ui

Lucide icons

Recharts

Responsive layout

Reusable components

Clean, professional spacing

Subtle borders and restrained animations

No excessive gradients or unnecessary decorative elements

Goal: Create only a visually impressive, functional dashboard frontend that looks like a professional AI warehouse monitoring command center. Use mock data throughout.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/976fea91-0887-4424-8673-6b8921a2360b).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
