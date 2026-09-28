import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/components/settings-page";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "System Settings | WarehouseVision AI" },
      {
        name: "description",
        content:
          "Configure camera streams, safety limits, notification preferences, and AI inference models.",
      },
      { property: "og:title", content: "System Settings | WarehouseVision AI" },
      {
        property: "og:description",
        content:
          "Configure camera streams, safety limits, notification preferences, and AI inference models.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SettingsPage,
});
