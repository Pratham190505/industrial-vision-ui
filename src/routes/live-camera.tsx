import { createFileRoute } from "@tanstack/react-router";

import { LiveCameraPage } from "@/components/live-camera-page";

export const Route = createFileRoute("/live-camera")({
  head: () => ({
    meta: [
      { title: "Live Camera | WarehouseVision AI" },
      {
        name: "description",
        content: "Real-time computer vision monitoring for warehouse operations.",
      },
      { property: "og:title", content: "Live Camera | WarehouseVision AI" },
      {
        property: "og:description",
        content: "Real-time computer vision monitoring for warehouse operations.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LiveCameraPage,
});
