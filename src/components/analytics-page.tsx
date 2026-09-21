import { useMemo, useState } from "react";
import {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  Boxes,
  Calendar,
  Clock,
  Filter,
  Flame,
  Forklift,
  Gauge,
  Layers,
  Menu,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Users,
  Warehouse,
  X,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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
import { WarehouseSidebar } from "@/components/warehouse-sidebar";
import {
  activityData,
  analyticsKPIs,
  dwellTimeByZone,
  inventoryData,
  safetyIncidentTrends,
  warehouses,
  workerForkliftTrends,
  zoneDetailedMetrics,
} from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

const chartTooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 4,
  fontSize: 11,
  color: "var(--foreground)",
};

export function AnalyticsPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [timeRange, setTimeRange] = useState("Today");
  const [selectedWarehouse, setSelectedWarehouse] = useState("North Distribution Center");
  const [selectedCamera, setSelectedCamera] = useState("All");
  const [selectedZone, setSelectedZone] = useState("All");

  // Zone occupancy filtered or all
  const displayedZones = useMemo(() => {
    if (selectedZone === "All") return zoneDetailedMetrics;
    return zoneDetailedMetrics.filter((z) => z.name.toLowerCase() === selectedZone.toLowerCase());
  }, [selectedZone]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sidebar navigation */}
      <WarehouseSidebar active="Analytics" />

      {/* Mobile navigation drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
            <WarehouseSidebar active="Analytics" mobile onNavigate={() => setMobileOpen(false)} />
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

      {/* Main Content Area */}
      <main className="relative min-h-screen lg:ml-64">
        {/* Background Image & Overlay */}
        <div
          className="fixed inset-0 bg-cover bg-center lg:left-64"
          style={{ backgroundImage: `url(${warehouseAsset.url})` }}
          aria-hidden="true"
        />
        <div className="fixed inset-0 bg-dashboard-overlay lg:left-64" aria-hidden="true" />

        <div className="relative z-10">
          {/* Header */}
          <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6 xl:px-8">
            <div className="mx-auto flex min-h-18 max-w-[1600px] items-center gap-3 py-3">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setMobileOpen(true)}
                className="shrink-0 border-border bg-card/80 text-muted-foreground hover:bg-surface-hover hover:text-foreground lg:hidden"
                aria-label="Open navigation"
              >
                <Menu />
              </Button>
              <div className="min-w-0 flex-1">
                <h1 className="truncate text-lg font-semibold sm:text-xl">Operational Analytics</h1>
                <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                  Vision intelligence: utilization, zone bottlenecks & activity dynamics
                </p>
              </div>

              {/* Warehouse selector */}
              <Select value={selectedWarehouse} onValueChange={setSelectedWarehouse}>
                <SelectTrigger className="hidden h-9 w-52 border-border bg-card/80 text-xs shadow-none md:flex">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((w) => (
                    <SelectItem key={w} value={w}>
                      {w}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Date Range Selector */}
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="h-9 w-32 border-border bg-card/90 text-xs shadow-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Today">Today (Shift)</SelectItem>
                  <SelectItem value="7 Days">Last 7 Days</SelectItem>
                  <SelectItem value="30 Days">Last 30 Days</SelectItem>
                  <SelectItem value="Quarter">Quarterly</SelectItem>
                </SelectContent>
              </Select>

              {/* Live telemetry badge */}
              <div className="hidden items-center gap-2 border border-success/20 bg-success/5 px-3 py-2 sm:flex">
                <span className="size-2 rounded-full bg-success" />
                <span className="text-[10px] font-semibold text-success">Analytics Active</span>
              </div>
            </div>
          </header>

          <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
            {/* Filter Toolbar for Camera & Zone */}
            <div className="flex flex-wrap items-center justify-between gap-3 border border-border bg-card/90 p-3.5 shadow-panel">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  <Filter className="size-3.5 text-primary" /> Multi-Filter:
                </span>

                {/* Camera Filter */}
                <Select value={selectedCamera} onValueChange={setSelectedCamera}>
                  <SelectTrigger className="h-8 w-44 border-border bg-background/60 text-xs">
                    <SelectValue placeholder="All Cameras" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Cameras (Node 01)</SelectItem>
                    <SelectItem value="CAM-01">CAM-01 (Main Warehouse)</SelectItem>
                    <SelectItem value="CAM-02">CAM-02 (Receiving Bay)</SelectItem>
                    <SelectItem value="CAM-03">CAM-03 (Dispatch Zone)</SelectItem>
                  </SelectContent>
                </Select>

                {/* Zone Filter */}
                <Select value={selectedZone} onValueChange={setSelectedZone}>
                  <SelectTrigger className="h-8 w-40 border-border bg-background/60 text-xs">
                    <SelectValue placeholder="All Zones" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Warehouse Zones</SelectItem>
                    <SelectItem value="Receiving">Receiving Bay</SelectItem>
                    <SelectItem value="Main Storage">Main Storage</SelectItem>
                    <SelectItem value="Packing">Packing Line</SelectItem>
                    <SelectItem value="Dispatch">Dispatch Dock</SelectItem>
                  </SelectContent>
                </Select>

                {(selectedCamera !== "All" || selectedZone !== "All") && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedCamera("All");
                      setSelectedZone("All");
                    }}
                    className="h-8 gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                  >
                    <RotateCcw className="size-3" /> Reset
                  </Button>
                )}
              </div>

              <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground">
                <span>Shift Window: 06:00 – 18:00</span>
                <span>•</span>
                <span className="text-primary">12-hr Sampling</span>
              </div>
            </div>

            {/* Summary KPI Cards Grid */}
            <section
              className="grid grid-cols-2 gap-3 sm:grid-cols-2 xl:grid-cols-4 xl:gap-5"
              aria-label="Operational Analytics KPIs"
            >
              {analyticsKPIs.map((kpi) => {
                const Icon = kpi.icon;
                const isDanger = kpi.tone === "danger";
                const isSuccess = kpi.tone === "success";
                return (
                  <article
                    key={kpi.label}
                    className="group border border-border bg-card/95 p-4 shadow-panel transition-colors hover:border-primary/50 sm:p-5"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                          {kpi.label}
                        </p>
                        <p className="mt-2 font-mono text-3xl font-bold tabular-nums text-foreground">
                          {kpi.value}
                        </p>
                      </div>
                      <div
                        className={cn(
                          "grid size-10 place-items-center rounded-md border",
                          isDanger
                            ? "border-danger/25 bg-danger/10 text-danger"
                            : isSuccess
                              ? "border-success/25 bg-success/10 text-success"
                              : "border-primary/25 bg-primary/10 text-primary",
                        )}
                      >
                        <Icon className="size-5" aria-hidden="true" />
                      </div>
                    </div>
                    <div className="mt-4 flex items-center gap-2 border-t border-border/70 pt-3">
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          isDanger ? "bg-danger" : isSuccess ? "bg-success" : "bg-primary",
                        )}
                      />
                      <p className="text-[11px] text-muted-foreground">{kpi.detail}</p>
                    </div>
                  </article>
                );
              })}
            </section>

            {/* Chart Grid Row 1: Worker Activity & Forklift Activity Trends */}
            <div className="grid gap-5 xl:grid-cols-2">
              {/* Worker Activity Trends */}
              <section className="border border-border bg-card/95 shadow-panel">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      Worker Activity & Utilization Trends
                    </h2>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Active workers detected & utilization efficiency percentage
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full bg-success" />
                      Active Workers
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full bg-primary" />
                      Utilization %
                    </span>
                  </div>
                </div>
                <div className="h-72 p-4 sm:p-5">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={workerForkliftTrends}
                      margin={{ top: 12, right: 12, left: -20, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="workerGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--success)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="var(--success)" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        stroke="var(--border)"
                        strokeDasharray="3 3"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="time"
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <ChartTooltip contentStyle={chartTooltipStyle} />
                      <Area
                        type="monotone"
                        dataKey="workers"
                        name="Active Workers"
                        stroke="var(--success)"
                        fill="url(#workerGrad)"
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="workerUtilization"
                        name="Utilization %"
                        stroke="var(--primary)"
                        strokeWidth={2}
                        dot={{ r: 3, fill: "var(--primary)" }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </section>

              {/* Forklift Activity Trends */}
              <section className="border border-border bg-card/95 shadow-panel">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      Forklift Fleet Activity & Operations
                    </h2>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Operating units in transit vs operational fleet utilization rate
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full bg-primary" />
                      Units In Operation
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full bg-chart-2" />
                      Fleet Utilization %
                    </span>
                  </div>
                </div>
                <div className="h-72 p-4 sm:p-5">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={workerForkliftTrends}
                      margin={{ top: 12, right: 12, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid
                        stroke="var(--border)"
                        strokeDasharray="3 3"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="time"
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <ChartTooltip contentStyle={chartTooltipStyle} />
                      <Bar
                        dataKey="forklifts"
                        name="Active Forklifts"
                        fill="var(--primary)"
                        radius={[3, 3, 0, 0]}
                      />
                      <Line
                        type="monotone"
                        dataKey="forkliftUtilization"
                        name="Utilization %"
                        stroke="var(--chart-2)"
                        strokeWidth={2}
                        dot={{ r: 3, fill: "var(--chart-2)" }}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>

            {/* Chart Grid Row 2: Safety Incident Trends & Inventory Movement Trends */}
            <div className="grid gap-5 xl:grid-cols-2">
              {/* Safety Incident Trends */}
              <section className="border border-border bg-card/95 shadow-panel">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      Safety Incident Frequency Trends
                    </h2>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      7-day incident breakdown across proximity, restricted zones & PPE
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-sm bg-danger" />
                      Proximity
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-sm bg-primary" />
                      Restricted Zone
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-sm bg-chart-2" />
                      PPE Violation
                    </span>
                  </div>
                </div>
                <div className="h-72 p-4 sm:p-5">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={safetyIncidentTrends}
                      margin={{ top: 12, right: 12, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid
                        stroke="var(--border)"
                        strokeDasharray="3 3"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="day"
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        allowDecimals={false}
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <ChartTooltip contentStyle={chartTooltipStyle} />
                      <Bar
                        dataKey="proximity"
                        name="Proximity"
                        fill="var(--danger)"
                        radius={[2, 2, 0, 0]}
                      />
                      <Bar
                        dataKey="restricted"
                        name="Restricted Zone"
                        fill="var(--primary)"
                        radius={[2, 2, 0, 0]}
                      />
                      <Bar dataKey="ppe" name="PPE" fill="var(--chart-2)" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>

              {/* Inventory Movement Trends */}
              <section className="border border-border bg-card/95 shadow-panel">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      Inventory Inbound vs Outbound Velocity
                    </h2>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Continuous throughput curve by camera tracking sensors
                    </p>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full bg-primary" />
                      Inbound
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full bg-success" />
                      Outbound
                    </span>
                  </div>
                </div>
                <div className="h-72 p-4 sm:p-5">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={inventoryData}
                      margin={{ top: 12, right: 12, left: -20, bottom: 0 }}
                    >
                      <CartesianGrid
                        stroke="var(--border)"
                        strokeDasharray="3 3"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="time"
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="var(--muted-foreground)"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                      />
                      <ChartTooltip contentStyle={chartTooltipStyle} />
                      <Line
                        type="monotone"
                        dataKey="inbound"
                        name="Inbound Flow"
                        stroke="var(--primary)"
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: "var(--primary)" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="outbound"
                        name="Outbound Flow"
                        stroke="var(--success)"
                        strokeWidth={2.5}
                        dot={{ r: 4, fill: "var(--success)" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>

            {/* Row 3: Zone Occupancy & Dwell Time Analysis */}
            <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
              {/* Zone Occupancy Visualization */}
              <section className="border border-border bg-card/95 p-5 shadow-panel">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-3">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      Operational Zone Occupancy & Bottleneck Analysis
                    </h2>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      Real-time capacity load, detected personnel & equipment by zone
                    </p>
                  </div>
                  <Warehouse className="size-5 text-primary" />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  {displayedZones.map((zone) => {
                    const isHigh = zone.occupancy >= 85;
                    const isMed = zone.occupancy >= 70;
                    return (
                      <div
                        key={zone.name}
                        className="rounded-sm border border-border/80 bg-background/50 p-4 transition-colors hover:border-primary/40"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-semibold text-foreground">{zone.name}</p>
                            <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                              Capacity: {zone.capacity}
                            </p>
                          </div>
                          <span
                            className={cn(
                              "font-mono text-base font-bold",
                              isHigh ? "text-danger" : isMed ? "text-primary" : "text-success",
                            )}
                          >
                            {zone.occupancy}%
                          </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all duration-500",
                              isHigh ? "bg-danger" : isMed ? "bg-primary" : "bg-success",
                            )}
                            style={{ width: `${zone.occupancy}%` }}
                          />
                        </div>

                        {/* Telemetry sub-metrics */}
                        <div className="mt-3.5 flex items-center justify-between border-t border-border/60 pt-2.5 text-[10px] text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Users className="size-3 text-muted-foreground" />
                            {zone.activeWorkers} Workers
                          </span>
                          <span className="flex items-center gap-1">
                            <Forklift className="size-3 text-muted-foreground" />
                            {zone.activeForklifts} Forklifts
                          </span>
                          <span className="flex items-center gap-1 font-mono">
                            <Clock className="size-3 text-primary" />
                            {zone.avgDwellMinutes}m avg
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Average Dwell Time by Operational Zone */}
              <section className="border border-border bg-card/95 p-5 shadow-panel">
                <div className="mb-4 border-b border-border pb-3">
                  <h2 className="text-sm font-semibold text-foreground">
                    Average Dwell Time by Zone
                  </h2>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Minutes spent before handoff (Actual vs Target)
                  </p>
                </div>

                <div className="space-y-4">
                  {dwellTimeByZone.map((item) => {
                    const isExceeding = item.time > item.target;
                    return (
                      <div key={item.zone} className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-foreground">{item.zone}</span>
                          <span className="font-mono text-xs">
                            <strong className={isExceeding ? "text-danger" : "text-success"}>
                              {item.time} min
                            </strong>
                            <span className="ml-1 text-[10px] text-muted-foreground">
                              / {item.target}m tgt
                            </span>
                          </span>
                        </div>
                        <div className="relative h-2 overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn(
                              "h-full rounded-full",
                              isExceeding ? "bg-danger" : "bg-primary",
                            )}
                            style={{ width: `${Math.min(100, (item.time / 35) * 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-6 rounded-md border border-primary/20 bg-primary/5 p-3 text-[11px] text-muted-foreground">
                  <p className="flex items-center gap-2 font-medium text-primary">
                    <Activity className="size-3.5" />
                    Operational Recommendation
                  </p>
                  <p className="mt-1 leading-relaxed">
                    Packing line dwell times are optimal at 9.8 min, but receiving bay dwell exceeds
                    target by 3.5 min due to forklift congestion during shift crossover.
                  </p>
                </div>
              </section>
            </div>

            {/* Footer */}
            <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
              <span>WarehouseVision AI · Operational Analytics Engine</span>
              <span>Model latency: 14ms · Frame rate: 24 FPS</span>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}
