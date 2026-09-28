import { createFileRoute } from "@tanstack/react-router";
import { WarehouseDashboard } from "@/components/warehouse-dashboard";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "WarehouseVision AI | Warehouse Monitoring" },
      {
        name: "description",
        content: "Real-time warehouse monitoring and operational intelligence dashboard.",
      },
      { property: "og:title", content: "WarehouseVision AI Command Center" },
      {
        property: "og:description",
        content: "Real-time warehouse monitoring and operational intelligence dashboard.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  return <WarehouseDashboard />;
}
