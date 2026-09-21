import { createFileRoute } from "@tanstack/react-router";
import { InventoryPage } from "@/components/inventory-page";
export const Route = createFileRoute("/inventory")({
  head: () => ({
    meta: [
      { title: "Inventory | WarehouseVision AI" },
      {
        name: "description",
        content: "Track warehouse inventory, movement, and stock availability.",
      },
      { property: "og:title", content: "Inventory | WarehouseVision AI" },
      {
        property: "og:description",
        content: "Track warehouse inventory, movement, and stock availability.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: InventoryPage,
});
