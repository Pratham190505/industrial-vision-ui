import { useState } from "react";
import {
  AlertTriangle,
  Bell,
  Camera,
  ChevronRight,
  Expand,
  Eye,
  Focus,
  Menu,
  MoreHorizontal,
  Pause,
  Play,
  ShieldCheck,
  Warehouse,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";

import warehouseAsset from "@/assets/warehouse-command-center.jpg.asset.json";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  activityData,
  alerts,
  inventoryData,
  kpis,
  warehouses,
  zoneOccupancy,
} from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";
import { WarehouseSidebar } from "@/components/warehouse-sidebar";

const iconButtonClass =
  "border-border bg-panel/80 text-muted-foreground shadow-none hover:bg-surface-hover hover:text-foreground";

function MetricCard({ metric }: { metric: (typeof kpis)[number] }) {
  const Icon = metric.icon;
  const isDanger = metric.tone === "danger";
  const isSuccess = metric.tone === "success";
  return (
    <article className="group border border-border bg-card/95 p-4 shadow-panel transition-colors hover:border-primary/50 sm:p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{metric.label}</p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-foreground">{metric.value}</p>
        </div>
        <div className={cn("grid size-10 place-items-center rounded-md border", isDanger ? "border-danger/25 bg-danger/10 text-danger" : isSuccess ? "border-success/25 bg-success/10 text-success" : "border-primary/25 bg-primary/10 text-primary")}>
          <Icon className="size-5" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 border-t border-border/70 pt-3">
        <span className={cn("size-1.5 rounded-full", isDanger ? "bg-danger" : isSuccess ? "bg-success" : "bg-primary")} />
        <p className="text-[11px] text-muted-foreground">{metric.detail}</p>
      </div>
    </article>
  );
}

function DetectionBox({ className, label, tone = "success" }: { className: string; label: string; tone?: "success" | "primary" }) {
  return (
    <div className={cn("absolute border-2", tone === "success" ? "border-success" : "border-primary", className)}>
      <span className={cn("absolute -top-6 left-[-2px] whitespace-nowrap px-1.5 py-1 font-mono text-[9px] font-semibold text-primary-foreground", tone === "success" ? "bg-success" : "bg-primary")}>
        {label}
      </span>
    </div>
  );
}

function CameraPanel() {
  const [paused, setPaused] = useState(false);
  const [expanded, setExpanded] = useState(false);

  return (
    <section className={cn("border border-border bg-card/95 shadow-panel", expanded && "fixed inset-4 z-50 flex flex-col bg-card shadow-2xl lg:inset-8")}>
      <div className="flex h-14 items-center justify-between border-b border-border px-4 sm:px-5">
        <div className="flex items-center gap-3">
          <Camera className="size-4 text-primary" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-foreground">Live Camera</h2>
          <span className="flex items-center gap-1.5 rounded-sm border border-success/30 bg-success/10 px-2 py-1 text-[9px] font-bold tracking-[0.12em] text-success">
            <span className="size-1.5 rounded-full bg-success" /> LIVE
          </span>
        </div>
        <TooltipProvider>
          <div className="flex gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="icon" variant="outline" className={cn("size-8", iconButtonClass)} onClick={() => setPaused((value) => !value)} aria-label={paused ? "Resume camera" : "Pause camera"}>
                  {paused ? <Play /> : <Pause />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{paused ? "Resume camera" : "Pause camera"}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="icon" variant="outline" className={cn("size-8", iconButtonClass)} onClick={() => setExpanded((value) => !value)} aria-label={expanded ? "Exit fullscreen" : "Open fullscreen"}>
                  {expanded ? <X /> : <Expand />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{expanded ? "Exit fullscreen" : "Open fullscreen"}</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
      <div className={cn("relative min-h-80 flex-1 overflow-hidden bg-background", expanded ? "min-h-0" : "aspect-[16/9]")}>
        <img src={warehouseAsset.url} alt="Main warehouse camera feed" className={cn("size-full object-cover saturate-[0.65] contrast-110", paused && "grayscale")} />
        <div className="absolute inset-0 bg-camera-overlay" />
        <div className="pointer-events-none absolute inset-0 scanlines opacity-30" />
        <div className="absolute left-4 top-4 flex items-center gap-2 bg-background/80 px-2.5 py-1.5 backdrop-blur-sm">
          <span className="font-mono text-[10px] font-semibold text-foreground">CAM-01</span>
          <span className="h-3 w-px bg-border" />
          <span className="font-mono text-[10px] text-muted-foreground">MAIN WAREHOUSE</span>
        </div>
        {!paused && (
          <>
            <DetectionBox label="Worker #12  97%" className="left-[45%] top-[41%] h-[23%] w-[8%]" />
            <DetectionBox label="Forklift #3  94%" tone="primary" className="bottom-[20%] left-[20%] h-[22%] w-[24%]" />
            <DetectionBox label="Box #27  91%" tone="primary" className="right-[14%] top-[47%] h-[17%] w-[19%]" />
          </>
        )}
        {paused && <div className="absolute inset-0 grid place-items-center"><div className="flex items-center gap-2 border border-border bg-background/90 px-4 py-2 text-xs font-semibold text-foreground"><Pause className="size-4 text-primary" /> FEED PAUSED</div></div>}
        <div className="absolute bottom-0 left-0 right-0 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border/70 bg-background/85 px-4 py-3 backdrop-blur-sm">
          <CameraStat icon={Focus} text="24 FPS" />
          <CameraStat icon={Eye} text="32 Objects Tracked" />
          <CameraStat icon={ShieldCheck} text="YOLO Active" success />
          <span className="ml-auto hidden font-mono text-[9px] text-muted-foreground sm:block">2026-09-14 22:56:42</span>
        </div>
      </div>
    </section>
  );
}

function CameraStat({ icon: Icon, text, success = false }: { icon: typeof Focus; text: string; success?: boolean }) {
  return <span className={cn("flex items-center gap-1.5 font-mono text-[9px]", success ? "text-success" : "text-muted-foreground")}><Icon className="size-3" />{text}</span>;
}

function SafetyAlerts() {
  return (
    <section className="border border-border bg-card/95 shadow-panel">
      <div className="flex h-14 items-center justify-between border-b border-border px-5">
        <div className="flex items-center gap-3"><AlertTriangle className="size-4 text-danger" /><h2 className="text-sm font-semibold">Recent Safety Alerts</h2></div>
        <Button variant="ghost" size="icon" className="size-8 text-muted-foreground hover:bg-surface-hover hover:text-foreground" aria-label="Alert options"><MoreHorizontal /></Button>
      </div>
      <div className="divide-y divide-border">
        {alerts.map((alert) => (
          <div key={alert.title} className="group flex gap-3 px-5 py-4 transition-colors hover:bg-surface-hover/50">
            <div className={cn("mt-0.5 grid size-8 shrink-0 place-items-center rounded-md border", alert.severity === "High" ? "border-danger/30 bg-danger/10 text-danger" : "border-primary/30 bg-primary/10 text-primary")}>
              <AlertTriangle className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs font-semibold leading-5 text-foreground">{alert.title}</p>
                <span className={cn("rounded-sm border px-1.5 py-0.5 text-[9px] font-bold uppercase", alert.severity === "High" ? "border-danger/30 bg-danger/10 text-danger" : "border-primary/30 bg-primary/10 text-primary")}>{alert.severity}</span>
              </div>
              <p className="mt-1 text-[11px] leading-5 text-muted-foreground">{alert.description}</p>
              <p className="mt-1 font-mono text-[9px] text-muted-foreground/70">{alert.time}</p>
            </div>
          </div>
        ))}
      </div>
      <Button variant="ghost" className="h-11 w-full rounded-none border-t border-border text-xs text-primary hover:bg-primary/5 hover:text-primary">View all safety events <ChevronRight className="size-3.5" /></Button>
    </section>
  );
}

function ZoneOccupancy() {
  return (
    <section className="border border-border bg-card/95 p-5 shadow-panel">
      <div className="mb-5 flex items-center justify-between">
        <div><h2 className="text-sm font-semibold">Zone Occupancy</h2><p className="mt-1 text-[11px] text-muted-foreground">Live capacity by operational zone</p></div>
        <Warehouse className="size-5 text-primary" />
      </div>
      <div className="space-y-4">
        {zoneOccupancy.map((zone) => (
          <div key={zone.label}>
            <div className="mb-2 flex justify-between text-[11px]"><span className="font-medium text-foreground">{zone.label}</span><span className="font-mono text-muted-foreground">{zone.count}</span></div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted"><div className={cn("h-full rounded-full", zone.value >= 85 ? "bg-danger" : zone.value >= 70 ? "bg-primary" : "bg-success")} style={{ width: `${zone.value}%` }} /></div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Analytics() {
  return (
    <section className="border border-border bg-card/95 shadow-panel xl:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div><h2 className="text-sm font-semibold">Operational Analytics</h2><p className="mt-1 text-[11px] text-muted-foreground">Activity and inventory flow · Today</p></div>
        <div className="flex gap-4 text-[10px] text-muted-foreground"><Legend color="bg-primary" label="Primary" /><Legend color="bg-success" label="Secondary" /></div>
      </div>
      <div className="grid gap-0 divide-y divide-border lg:grid-cols-2 lg:divide-x lg:divide-y-0">
        <ChartBlock title="Worker / Forklift Activity">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={activityData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
              <defs><linearGradient id="workerFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--primary)" stopOpacity={0.28} /><stop offset="100%" stopColor="var(--primary)" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" stroke="var(--muted-foreground)" fontSize={9} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--muted-foreground)" fontSize={9} tickLine={false} axisLine={false} />
              <ChartTooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 11 }} />
              <Area type="monotone" dataKey="workers" stroke="var(--primary)" fill="url(#workerFill)" strokeWidth={2} />
              <Area type="monotone" dataKey="forklifts" stroke="var(--success)" fill="transparent" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartBlock>
        <ChartBlock title="Inventory Movement">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={inventoryData} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" stroke="var(--muted-foreground)" fontSize={9} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--muted-foreground)" fontSize={9} tickLine={false} axisLine={false} />
              <ChartTooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 4, fontSize: 11 }} />
              <Bar dataKey="inbound" fill="var(--primary)" radius={[2, 2, 0, 0]} />
              <Bar dataKey="outbound" fill="var(--success)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartBlock>
      </div>
    </section>
  );
}

function Legend({ color, label }: { color: string; label: string }) { return <span className="flex items-center gap-1.5"><span className={cn("size-2 rounded-full", color)} />{label}</span>; }
function ChartBlock({ title, children }: { title: string; children: React.ReactNode }) { return <div className="p-5"><p className="mb-4 text-xs font-medium text-foreground">{title}</p><div className="h-52">{children}</div></div>; }

export function WarehouseDashboard() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [warehouse, setWarehouse] = useState("North Distribution Center");

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background text-foreground">
        <WarehouseSidebar active="Dashboard" />
        {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setMobileOpen(false)} /><div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border"><WarehouseSidebar active="Dashboard" mobile onNavigate={() => setMobileOpen(false)} /><Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)} className="absolute right-3 top-4 text-muted-foreground" aria-label="Close menu"><X /></Button></div></div>}

        <main className="relative min-h-screen lg:ml-64">
          <div className="fixed inset-0 bg-cover bg-center lg:left-64" style={{ backgroundImage: `url(${warehouseAsset.url})` }} aria-hidden="true" />
          <div className="fixed inset-0 bg-dashboard-overlay lg:left-64" aria-hidden="true" />
          <div className="relative z-10">
            <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6 xl:px-8">
              <div className="mx-auto flex min-h-18 max-w-[1600px] items-center gap-3 py-3">
                <Button variant="outline" size="icon" onClick={() => setMobileOpen(true)} className={cn("shrink-0 lg:hidden", iconButtonClass)} aria-label="Open navigation"><Menu /></Button>
                <div className="min-w-0 flex-1">
                  <h1 className="truncate text-lg font-semibold sm:text-xl">Warehouse Overview</h1>
                  <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">Real-time monitoring and operational intelligence</p>
                </div>
                <Select value={warehouse} onValueChange={setWarehouse}>
                  <SelectTrigger className="hidden h-9 w-56 border-border bg-card/80 text-xs shadow-none md:flex"><SelectValue /></SelectTrigger>
                  <SelectContent>{warehouses.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
                </Select>
                <div className="hidden items-center gap-2 border border-success/20 bg-success/5 px-3 py-2 sm:flex"><span className="size-2 rounded-full bg-success" /><span className="text-[10px] font-semibold text-success">Monitoring Active</span></div>
                <Tooltip><TooltipTrigger asChild><Button variant="outline" size="icon" className={cn("relative", iconButtonClass)} aria-label="Notifications"><Bell /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-danger ring-2 ring-card" /></Button></TooltipTrigger><TooltipContent>3 unread alerts</TooltipContent></Tooltip>
                <div className="grid size-9 shrink-0 place-items-center rounded-md border border-primary/30 bg-primary/15 text-xs font-bold text-primary" aria-label="User: Alex Morgan">AM</div>
              </div>
            </header>

            <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
              <div className="md:hidden"><Select value={warehouse} onValueChange={setWarehouse}><SelectTrigger className="border-border bg-card/95 text-xs"><SelectValue /></SelectTrigger><SelectContent>{warehouses.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
              <section className="grid grid-cols-2 gap-3 xl:grid-cols-4 xl:gap-5" aria-label="Key performance indicators">{kpis.map((metric) => <MetricCard key={metric.label} metric={metric} />)}</section>
              <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.75fr)_minmax(330px,0.75fr)]"><CameraPanel /><SafetyAlerts /></div>
              <div className="grid items-start gap-5 xl:grid-cols-[minmax(300px,0.72fr)_minmax(0,2fr)]"><ZoneOccupancy /><Analytics /></div>
              <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground"><span>WarehouseVision AI · Control Node 01</span><span>Last sync: 4 sec ago</span></footer>
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}