import { createFileRoute } from "@tanstack/react-router";
import { SafetyMonitoringPage } from "@/components/safety-monitoring-page";
export const Route = createFileRoute("/safety")({
  head: () => ({
    meta: [
      { title: "Safety Monitoring | WarehouseVision AI" },
      {
        name: "description",
        content: "Monitor warehouse safety risks, violations, and incident resolution.",
      },
      { property: "og:title", content: "Safety Monitoring | WarehouseVision AI" },
      {
        property: "og:description",
        content: "Monitor warehouse safety risks, violations, and incident resolution.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SafetyMonitoringPage,
});
