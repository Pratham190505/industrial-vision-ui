import { useState } from "react";
import {
  Bell,
  Boxes,
  Camera,
  Expand,
  Focus,
  Forklift,
  Gauge,
  Menu,
  MoreHorizontal,
  PackageOpen,
  Pause,
  Play,
  RotateCcw,
  ScanSearch,
  Users,
  X,
} from "lucide-react";

import warehouseAsset from "@/assets/warehouse-command-center.jpg.asset.json";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { WarehouseSidebar } from "@/components/warehouse-sidebar";
import { cn } from "@/lib/utils";

const cameras = ["CAM-01 | Main Warehouse", "CAM-02 | Receiving Bay", "CAM-03 | Dispatch Zone"];

const monitoringStats = [
  { label: "Workers Detected", value: "24", icon: Users },
  { label: "Forklifts Detected", value: "5", icon: Forklift },
  { label: "Boxes Detected", value: "127", icon: Boxes },
  { label: "Objects Tracked", value: "32", icon: ScanSearch },
  { label: "Current FPS", value: "24", icon: Gauge },
];

const detectionEvents = [
  { object: "Worker", id: "#12", confidence: "94%", time: "14:32:18", status: "Tracked" },
  { object: "Forklift", id: "#3", confidence: "91%", time: "14:32:16", status: "Tracked" },
  { object: "Box", id: "#27", confidence: "88%", time: "14:32:12", status: "Detected" },
  { object: "Worker", id: "#07", confidence: "96%", time: "14:32:09", status: "Tracked" },
  { object: "Pallet", id: "#08", confidence: "89%", time: "14:32:04", status: "Detected" },
];

const legend = [
  { label: "Worker", color: "bg-success" },
  { label: "Forklift", color: "bg-primary" },
  { label: "Box", color: "bg-chart-3" },
  { label: "Pallet", color: "bg-chart-4" },
];

const iconButtonClass = "border-border bg-panel/80 text-muted-foreground shadow-none hover:bg-surface-hover hover:text-foreground";

function DetectionBox({ label, className, tone }: { label: string; className: string; tone: "worker" | "forklift" | "box" | "pallet" }) {
  const color = {
    worker: "border-success text-success",
    forklift: "border-primary text-primary",
    box: "border-chart-3 text-chart-3",
    pallet: "border-chart-4 text-chart-4",
  }[tone];

  return (
    <div className={cn("absolute border", color, className)}>
      <span className="absolute -top-5 left-[-1px] whitespace-nowrap bg-background/90 px-1.5 py-0.5 font-mono text-[8px] font-semibold text-current backdrop-blur-sm">{label}</span>
      <span className="absolute -left-px -top-px size-2 border-l-2 border-t-2 border-current" />
      <span className="absolute -right-px -top-px size-2 border-r-2 border-t-2 border-current" />
      <span className="absolute -bottom-px -left-px size-2 border-b-2 border-l-2 border-current" />
      <span className="absolute -bottom-px -right-px size-2 border-b-2 border-r-2 border-current" />
    </div>
  );
}

function MonitoringFeed() {
  const [paused, setPaused] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [controlsOpen, setControlsOpen] = useState(false);

  return (
    <section className={cn("overflow-hidden border border-border bg-card/95 shadow-panel", expanded && "fixed inset-3 z-50 flex flex-col bg-card lg:inset-8")}>
      <div className="flex min-h-14 items-center justify-between gap-3 border-b border-border px-4 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <Camera className="size-4 shrink-0 text-primary" />
          <div className="min-w-0"><h2 className="truncate text-sm font-semibold">Primary Monitoring Feed</h2><p className="mt-0.5 hidden text-[10px] text-muted-foreground sm:block">Object detection · Multi-class tracking</p></div>
        </div>
        <div className="flex shrink-0 gap-1">
          <Tooltip><TooltipTrigger asChild><Button size="icon" variant="outline" className={cn("size-8", iconButtonClass, controlsOpen && "border-primary text-primary")} onClick={() => setControlsOpen((value) => !value)} aria-label="Camera controls"><Focus /></Button></TooltipTrigger><TooltipContent>Camera controls</TooltipContent></Tooltip>
          <Tooltip><TooltipTrigger asChild><Button size="icon" variant="outline" className={cn("size-8", iconButtonClass)} onClick={() => setPaused((value) => !value)} aria-label={paused ? "Resume camera" : "Pause camera"}>{paused ? <Play /> : <Pause />}</Button></TooltipTrigger><TooltipContent>{paused ? "Resume camera" : "Pause camera"}</TooltipContent></Tooltip>
          <Tooltip><TooltipTrigger asChild><Button size="icon" variant="outline" className={cn("size-8", iconButtonClass)} onClick={() => setExpanded((value) => !value)} aria-label={expanded ? "Exit fullscreen" : "Open fullscreen"}>{expanded ? <X /> : <Expand />}</Button></TooltipTrigger><TooltipContent>{expanded ? "Exit fullscreen" : "Open fullscreen"}</TooltipContent></Tooltip>
        </div>
      </div>
      {controlsOpen && <div className="flex items-center gap-2 border-b border-border bg-background/50 px-4 py-2"><span className="mr-2 text-[10px] uppercase tracking-[0.12em] text-muted-foreground">Camera control</span>{["Pan left", "Center", "Pan right"].map((label, index) => <Button key={label} variant="outline" size="sm" className="h-7 border-border bg-card text-[10px] text-muted-foreground hover:text-primary" aria-label={label}>{index === 1 ? <RotateCcw className="size-3" /> : label}</Button>)}</div>}
      <div className={cn("relative min-h-[390px] overflow-hidden bg-background", expanded ? "flex-1" : "aspect-[16/10] xl:aspect-[16/9]")}>
        <img src={warehouseAsset.url} alt="Warehouse camera monitoring feed" className={cn("size-full object-cover saturate-[0.58] contrast-110", paused && "grayscale")} />
        <div className="absolute inset-0 bg-camera-overlay" />
        <div className="pointer-events-none absolute inset-0 scanlines opacity-30" />
        <div className="absolute left-4 top-4 flex items-center gap-2 border border-border/70 bg-background/85 px-2.5 py-1.5 backdrop-blur-sm">
          <span className="font-mono text-[10px] font-semibold text-foreground">CAM-01</span><span className="h-3 w-px bg-border" /><span className="flex items-center gap-1.5 font-mono text-[9px] font-semibold text-success"><span className="size-1.5 rounded-full bg-success" />LIVE</span>
        </div>
        <div className="absolute right-4 top-4 bg-background/85 px-2.5 py-1.5 font-mono text-[9px] text-muted-foreground backdrop-blur-sm">2026-09-14 14:32:21</div>
        {!paused && <>
          <DetectionBox label="Worker #12 · 94%" tone="worker" className="left-[43%] top-[39%] h-[25%] w-[8%]" />
          <DetectionBox label="Worker #07 · 96%" tone="worker" className="right-[8%] top-[48%] h-[27%] w-[7%]" />
          <DetectionBox label="Forklift #3 · 91%" tone="forklift" className="bottom-[16%] left-[18%] h-[25%] w-[25%]" />
          <DetectionBox label="Box #27 · 88%" tone="box" className="right-[22%] top-[42%] h-[18%] w-[17%]" />
          <DetectionBox label="Pallet #08 · 89%" tone="pallet" className="bottom-[12%] right-[12%] h-[18%] w-[24%]" />
        </>}
        {paused && <div className="absolute inset-0 grid place-items-center"><div className="flex items-center gap-2 border border-border bg-background/90 px-4 py-2 text-xs font-semibold"><Pause className="size-4 text-primary" /> FEED PAUSED</div></div>}
        <div className="absolute bottom-0 left-0 right-0 flex items-center gap-4 border-t border-border/70 bg-background/85 px-4 py-3 font-mono text-[9px] text-muted-foreground backdrop-blur-sm"><span>1920 × 1080</span><span>24 FPS</span><span className="ml-auto text-success">● TRACKING ACTIVE</span></div>
      </div>
    </section>
  );
}

function MonitoringPanel() {
  return (
    <aside className="border border-border bg-card/95 shadow-panel">
      <div className="flex h-14 items-center justify-between border-b border-border px-5"><div><h2 className="text-sm font-semibold">Live Statistics</h2><p className="mt-0.5 text-[10px] text-muted-foreground">Current camera frame</p></div><span className="size-2 rounded-full bg-success" /></div>
      <div className="divide-y divide-border">
        {monitoringStats.map((stat) => { const Icon = stat.icon; return <div key={stat.label} className="flex items-center gap-3 px-5 py-3.5"><div className="grid size-8 place-items-center rounded-md border border-primary/20 bg-primary/10 text-primary"><Icon className="size-4" /></div><span className="flex-1 text-[11px] text-muted-foreground">{stat.label}</span><strong className="font-mono text-lg font-semibold text-foreground">{stat.value}</strong></div>; })}
      </div>
      <div className="border-t border-border px-5 py-5"><h3 className="mb-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Detection Legend</h3><div className="grid grid-cols-2 gap-3">{legend.map((item) => <div key={item.label} className="flex items-center gap-2 text-[11px] text-foreground"><span className={cn("size-2 rounded-sm", item.color)} />{item.label}</div>)}</div></div>
      <div className="border-t border-border px-5 py-4"><div className="flex items-center justify-between text-[10px]"><span className="text-muted-foreground">Model confidence threshold</span><span className="font-mono text-primary">85%</span></div><div className="mt-2 h-1 overflow-hidden rounded-full bg-muted"><div className="h-full w-[85%] bg-primary" /></div></div>
    </aside>
  );
}

function DetectionEvents() {
  return (
    <section className="overflow-hidden border border-border bg-card/95 shadow-panel">
      <div className="flex h-14 items-center justify-between border-b border-border px-5"><div><h2 className="text-sm font-semibold">Recent Detection Events</h2><p className="mt-0.5 text-[10px] text-muted-foreground">Latest objects identified by CAM-01</p></div><Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:bg-surface-hover hover:text-foreground" aria-label="Detection event options"><MoreHorizontal /></Button></div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] border-collapse text-left">
          <thead><tr className="border-b border-border bg-background/35 text-[9px] uppercase tracking-[0.12em] text-muted-foreground">{["Object", "ID", "Confidence", "Time", "Status"].map((heading) => <th key={heading} className="px-5 py-3 font-medium">{heading}</th>)}</tr></thead>
          <tbody className="divide-y divide-border">{detectionEvents.map((event) => <tr key={`${event.object}-${event.id}`} className="text-xs transition-colors hover:bg-surface-hover/40"><td className="px-5 py-3.5 font-medium text-foreground">{event.object}</td><td className="px-5 py-3.5 font-mono text-muted-foreground">{event.id}</td><td className="px-5 py-3.5"><span className="font-mono text-primary">{event.confidence}</span></td><td className="px-5 py-3.5 font-mono text-muted-foreground">{event.time}</td><td className="px-5 py-3.5"><span className="inline-flex items-center gap-1.5 rounded-sm border border-success/25 bg-success/10 px-2 py-1 text-[9px] font-semibold uppercase text-success"><span className="size-1.5 rounded-full bg-success" />{event.status}</span></td></tr>)}</tbody>
        </table>
      </div>
    </section>
  );
}

export function LiveCameraPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [camera, setCamera] = useState(cameras[0]);

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background text-foreground">
        <WarehouseSidebar active="Live Camera" />
        {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setMobileOpen(false)} /><div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border"><WarehouseSidebar active="Live Camera" mobile onNavigate={() => setMobileOpen(false)} /><Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} className="absolute right-3 top-4 text-muted-foreground" aria-label="Close menu"><X /></Button></div></div>}
        <main className="relative min-h-screen lg:ml-64">
          <div className="fixed inset-0 bg-cover bg-center lg:left-64" style={{ backgroundImage: `url(${warehouseAsset.url})` }} aria-hidden="true" />
          <div className="fixed inset-0 bg-dashboard-overlay lg:left-64" aria-hidden="true" />
          <div className="relative z-10">
            <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6 xl:px-8">
              <div className="mx-auto flex min-h-18 max-w-[1600px] items-center gap-3 py-3">
                <Button variant="outline" size="icon" onClick={() => setMobileOpen(true)} className={cn("shrink-0 lg:hidden", iconButtonClass)} aria-label="Open navigation"><Menu /></Button>
                <div className="min-w-0 flex-1"><h1 className="truncate text-lg font-semibold sm:text-xl">Live Camera</h1><p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">Real-time computer vision monitoring</p></div>
                <Select value={camera} onValueChange={setCamera}><SelectTrigger className="hidden h-9 w-56 border-border bg-card/80 text-xs shadow-none md:flex"><SelectValue /></SelectTrigger><SelectContent>{cameras.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select>
                <div className="hidden items-center gap-2 border border-success/20 bg-success/5 px-3 py-2 sm:flex"><span className="size-2 rounded-full bg-success" /><span className="text-[10px] font-semibold text-success">Monitoring Active</span></div>
                <Tooltip><TooltipTrigger asChild><Button variant="outline" size="icon" className={cn("relative", iconButtonClass)} aria-label="Notifications"><Bell /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-primary ring-2 ring-card" /></Button></TooltipTrigger><TooltipContent>Detection notifications</TooltipContent></Tooltip>
                <div className="grid size-9 shrink-0 place-items-center rounded-md border border-primary/30 bg-primary/15 text-xs font-bold text-primary">AM</div>
              </div>
            </header>
            <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
              <div className="md:hidden"><Select value={camera} onValueChange={setCamera}><SelectTrigger className="border-border bg-card/95 text-xs"><SelectValue /></SelectTrigger><SelectContent>{cameras.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
              <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_300px]"><MonitoringFeed /><MonitoringPanel /></div>
              <DetectionEvents />
              <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground"><span>WarehouseVision AI · CAM-01</span><span>Latency: 42 ms · Stream stable</span></footer>
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}