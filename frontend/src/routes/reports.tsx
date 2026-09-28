import { createFileRoute } from "@tanstack/react-router";
import { ReportsPage } from "@/components/reports-page";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Operational Reports | WarehouseVision AI" },
      {
        name: "description",
        content: "Daily monitoring summaries, safety audits, and inventory movement reports.",
      },
      { property: "og:title", content: "Operational Reports | WarehouseVision AI" },
      {
        property: "og:description",
        content: "Daily monitoring summaries, safety audits, and inventory movement reports.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ReportsPage,
});
