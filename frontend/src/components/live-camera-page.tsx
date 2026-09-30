import { useState } from "react";
import {
  Bell,
  Boxes,
  Camera,
  Forklift,
  Gauge,
  Menu,
  MoreHorizontal,
  ScanSearch,
  Users,
  Video,
  X,
} from "lucide-react";

import warehouseAsset from "@/assets/warehouse-command-center.jpg.asset.json";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { WarehouseSidebar } from "@/components/warehouse-sidebar";
import { cn } from "@/lib/utils";

import { LiveCamera } from "./live/LiveCamera";
import { SafetyPanel } from "./live/SafetyPanel";
import { InventoryPanel } from "./live/InventoryPanel";
import { LiveFrameResponse } from "@/services/liveMonitoringApi";

const cameraOptions = [
  "LIVE-WEBCAM | Browser Camera Feed",
  "CAM-01 | Main Warehouse (Demo)",
  "CAM-02 | Receiving Bay (Demo)",
  "CAM-03 | Dispatch Zone (Demo)",
];

const legend = [
  { label: "Person / Worker", color: "bg-emerald-500" },
  { label: "Forklift", color: "bg-cyan-500" },
  { label: "Box", color: "bg-amber-500" },
  { label: "Pallet", color: "bg-purple-500" },
  { label: "Hazard Alert", color: "bg-rose-500" },
];

const iconButtonClass =
  "border-border bg-panel/80 text-muted-foreground shadow-none hover:bg-surface-hover hover:text-foreground";

export function LiveCameraPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState("LIVE-WEBCAM | Browser Camera Feed");
  const [currentAnalysis, setCurrentAnalysis] = useState<LiveFrameResponse | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const isWebcamMode = selectedCamera.startsWith("LIVE-WEBCAM");

  // Real-time telemetry calculations
  const totalObjectsTracked = currentAnalysis?.objects?.length ?? 0;
  const workersDetected =
    currentAnalysis?.objects?.filter(
      (o) => o.class_name.toLowerCase() === "person" || o.class_name.toLowerCase() === "worker"
    ).length ?? 0;
  const forkliftsDetected =
    currentAnalysis?.objects?.filter((o) => o.class_name.toLowerCase() === "forklift").length ?? 0;
  const boxesDetected =
    currentAnalysis?.inventory?.counts?.["box"] ??
    currentAnalysis?.objects?.filter((o) => o.class_name.toLowerCase() === "box").length ??
    0;

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background text-foreground">
        <WarehouseSidebar active="Live Camera" />
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-background/80 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
              <WarehouseSidebar
                active="Live Camera"
                mobile
                onNavigate={() => setMobileOpen(false)}
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileOpen(false)}
                className="absolute right-3 top-4 text-muted-foreground"
                aria-label="Close menu"
              >
                <X />
              </Button>
            </div>
          </div>
        )}

        <main className="relative min-h-screen lg:ml-64">
          <div
            className="fixed inset-0 bg-cover bg-center lg:left-64"
            style={{ backgroundImage: `url(${warehouseAsset.url})` }}
            aria-hidden="true"
          />
          <div className="fixed inset-0 bg-dashboard-overlay lg:left-64" aria-hidden="true" />

          <div className="relative z-10">
            {/* Top Navigation Header */}
            <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6 xl:px-8">
              <div className="mx-auto flex min-h-18 max-w-[1600px] items-center gap-3 py-3">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setMobileOpen(true)}
                  className={cn("shrink-0 lg:hidden", iconButtonClass)}
                  aria-label="Open navigation"
                >
                  <Menu />
                </Button>
                <div className="min-w-0 flex-1">
                  <h1 className="truncate text-lg font-semibold sm:text-xl">
                    Live Webcam Monitoring
                  </h1>
                  <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                    Real-time browser webcam sampling · YOLO tracking · Safety & Inventory AI
                  </p>
                </div>

                <Select value={selectedCamera} onValueChange={setSelectedCamera}>
                  <SelectTrigger className="hidden h-9 w-72 border-border bg-card/80 text-xs shadow-none md:flex">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {cameraOptions.map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="hidden items-center gap-2 border border-primary/20 bg-primary/5 px-3 py-2 sm:flex">
                  <span
                    className={cn(
                      "size-2 rounded-full",
                      currentSessionId ? "bg-emerald-400 animate-pulse" : "bg-muted-foreground"
                    )}
                  />
                  <span className="text-[10px] font-semibold text-foreground">
                    {currentSessionId ? "Live AI Active" : "Standby"}
                  </span>
                </div>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className={cn("relative", iconButtonClass)}
                      aria-label="Notifications"
                    >
                      <Bell />
                      {currentAnalysis?.safety?.events && currentAnalysis.safety.events.length > 0 && (
                        <span className="absolute right-2 top-2 size-1.5 rounded-full bg-rose-500 ring-2 ring-card animate-ping" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Active violations</TooltipContent>
                </Tooltip>

                <div className="grid size-9 shrink-0 place-items-center rounded-md border border-primary/30 bg-primary/15 text-xs font-bold text-primary">
                  WV
                </div>
              </div>
            </header>

            {/* Page Body */}
            <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
              {/* Mobile Camera Selector */}
              <div className="md:hidden">
                <Select value={selectedCamera} onValueChange={setSelectedCamera}>
                  <SelectTrigger className="border-border bg-card/95 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {cameraOptions.map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Main Monitoring Section & Lateral Panels */}
              <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
                {/* Primary Camera Feed Display */}
                <div className="space-y-4">
                  {isWebcamMode ? (
                    <LiveCamera
                      onAnalysisUpdate={setCurrentAnalysis}
                      onSessionChange={setCurrentSessionId}
                      frameIntervalMs={250}
                    />
                  ) : (
                    <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-border bg-black shadow-2xl">
                      <img
                        src={warehouseAsset.url}
                        alt="Demonstration camera feed"
                        className="size-full object-cover saturate-[0.7] contrast-105"
                      />
                      <div className="absolute inset-0 bg-camera-overlay" />
                      <div className="pointer-events-none absolute inset-0 scanlines opacity-30" />
                      <div className="absolute left-4 top-4 flex items-center gap-2 border border-border/70 bg-background/85 px-2.5 py-1.5 backdrop-blur-sm">
                        <span className="font-mono text-[10px] font-semibold text-foreground">
                          {selectedCamera.split("|")[0].trim()}
                        </span>
                        <span className="h-3 w-px bg-border" />
                        <span className="font-mono text-[9px] text-muted-foreground">DEMO FEED</span>
                      </div>
                    </div>
                  )}

                  {/* Summary Metric Counters */}
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div className="rounded-lg border border-border bg-card/80 p-3 backdrop-blur-sm">
                      <div className="flex items-center justify-between text-muted-foreground text-xs">
                        <span>Workers</span>
                        <Users className="size-4 text-emerald-400" />
                      </div>
                      <div className="mt-1 font-mono text-xl font-bold text-foreground">
                        {workersDetected}
                      </div>
                    </div>

                    <div className="rounded-lg border border-border bg-card/80 p-3 backdrop-blur-sm">
                      <div className="flex items-center justify-between text-muted-foreground text-xs">
                        <span>Forklifts</span>
                        <Forklift className="size-4 text-cyan-400" />
                      </div>
                      <div className="mt-1 font-mono text-xl font-bold text-foreground">
                        {forkliftsDetected}
                      </div>
                    </div>

                    <div className="rounded-lg border border-border bg-card/80 p-3 backdrop-blur-sm">
                      <div className="flex items-center justify-between text-muted-foreground text-xs">
                        <span>Boxes Visible</span>
                        <Boxes className="size-4 text-amber-400" />
                      </div>
                      <div className="mt-1 font-mono text-xl font-bold text-foreground">
                        {boxesDetected}
                      </div>
                    </div>

                    <div className="rounded-lg border border-border bg-card/80 p-3 backdrop-blur-sm">
                      <div className="flex items-center justify-between text-muted-foreground text-xs">
                        <span>Objects Tracked</span>
                        <ScanSearch className="size-4 text-primary" />
                      </div>
                      <div className="mt-1 font-mono text-xl font-bold text-foreground">
                        {totalObjectsTracked}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Lateral Panels: Safety & Inventory */}
                <div className="space-y-4">
                  <SafetyPanel
                    safety={currentAnalysis?.safety ?? null}
                    ppe={currentAnalysis?.ppe ?? null}
                  />

                  <InventoryPanel inventory={currentAnalysis?.inventory ?? null} />

                  {/* Overlay Legend */}
                  <div className="rounded-lg border border-border bg-card/90 p-4 shadow-sm backdrop-blur-sm">
                    <h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      Detection Legend
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {legend.map((item) => (
                        <div key={item.label} className="flex items-center gap-2 text-[11px] text-foreground">
                          <span className={cn("size-2 rounded-full", item.color)} />
                          <span>{item.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Real-time Tracked Objects Table */}
              <section className="overflow-hidden rounded-lg border border-border bg-card/95 shadow-sm">
                <div className="flex h-14 items-center justify-between border-b border-border px-5">
                  <div>
                    <h2 className="text-sm font-semibold">Active Tracked Objects</h2>
                    <p className="mt-0.5 text-[10px] text-muted-foreground">
                      Real-time objects monitored in the active camera session
                    </p>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                    <span>Frame: #{currentAnalysis?.frame_number ?? 0}</span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full min-w-[620px] border-collapse text-left">
                    <thead>
                      <tr className="border-b border-border bg-background/35 text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
                        {["Track ID", "Class", "Confidence", "Center Coordinates", "Status"].map(
                          (heading) => (
                            <th key={heading} className="px-5 py-3 font-medium">
                              {heading}
                            </th>
                          )
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {currentAnalysis?.objects && currentAnalysis.objects.length > 0 ? (
                        currentAnalysis.objects.map((obj) => (
                          <tr
                            key={`${obj.track_id}-${obj.class_name}`}
                            className="text-xs transition-colors hover:bg-surface-hover/40"
                          >
                            <td className="px-5 py-3 font-mono font-semibold text-primary">
                              #{obj.track_id}
                            </td>
                            <td className="px-5 py-3 font-medium capitalize text-foreground">
                              {obj.class_name}
                            </td>
                            <td className="px-5 py-3 font-mono text-muted-foreground">
                              {Math.round(obj.confidence * 100)}%
                            </td>
                            <td className="px-5 py-3 font-mono text-muted-foreground">
                              X: {Math.round(obj.center.x)}, Y: {Math.round(obj.center.y)}
                            </td>
                            <td className="px-5 py-3">
                              <span className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase text-emerald-400">
                                <span className="size-1.5 rounded-full bg-emerald-400" />
                                Tracking Active
                              </span>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td
                            colSpan={5}
                            className="py-8 text-center text-xs text-muted-foreground"
                          >
                            {currentSessionId
                              ? "Monitoring active — no objects currently detected in camera view."
                              : "Start webcam and click 'Start Monitoring' to initiate real-time AI object tracking."}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Status Footer */}
              <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
                <span>WarehouseVision AI · Real-Time Edge Processing</span>
                <span>
                  {currentSessionId
                    ? `Active Session: ${currentSessionId.slice(0, 12)}...`
                    : "Live Stream Ready"}
                </span>
              </footer>
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}
