import { createFileRoute } from "@tanstack/react-router";
import { AnalyticsPage } from "@/components/analytics-page";
export const Route = createFileRoute("/analytics")({ head: () => ({ meta: [
  { title: "Operational Analytics | WarehouseVision AI" }, { name: "description", content: "Analyze warehouse productivity, inventory flow, safety, and zone performance." },
  { property: "og:title", content: "Operational Analytics | WarehouseVision AI" }, { property: "og:description", content: "Analyze warehouse productivity, inventory flow, safety, and zone performance." },
  { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary_large_image" },
] }), component: AnalyticsPage });
