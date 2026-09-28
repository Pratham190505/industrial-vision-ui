import { useMemo, useState } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  CalendarIcon,
  CheckCircle2,
  ChevronRight,
  Clock3,
  MapPin,
  Menu,
  Search,
  ShieldAlert,
  Siren,
  TriangleAlert,
  UserRound,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import warehouseAsset from "@/assets/warehouse-command-center.jpg.asset.json";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { WarehouseSidebar } from "@/components/warehouse-sidebar";
import { cn } from "@/lib/utils";

const trend = [
  { day: "Mon", proximity: 3, restricted: 1, ppe: 2 },
  { day: "Tue", proximity: 2, restricted: 2, ppe: 1 },
  { day: "Wed", proximity: 4, restricted: 1, ppe: 1 },
  { day: "Thu", proximity: 1, restricted: 3, ppe: 2 },
  { day: "Fri", proximity: 5, restricted: 2, ppe: 3 },
  { day: "Sat", proximity: 2, restricted: 1, ppe: 1 },
  { day: "Sun", proximity: 3, restricted: 2, ppe: 2 },
];
const activeAlerts = [
  {
    title: "Worker–Forklift Proximity",
    description: "Worker #12 is near Forklift #3",
    location: "Loading Zone",
    time: "2 minutes ago",
    severity: "High",
    icon: Siren,
  },
  {
    title: "Restricted Zone Entry",
    description: "Worker #07 entered Restricted Zone A",
    location: "Storage Area",
    time: "8 minutes ago",
    severity: "Medium",
    icon: ShieldAlert,
  },
  {
    title: "PPE Violation",
    description: "Worker #18 missing safety vest",
    location: "Packing Zone",
    time: "15 minutes ago",
    severity: "Medium",
    icon: TriangleAlert,
  },
];
const events = [
  {
    type: "Worker–Forklift Proximity",
    description: "Minimum separation fell below 2.0 m",
    location: "Loading Zone",
    object: "W-12 / FL-03",
    severity: "High",
    timestamp: "Sep 21, 14:32:18",
    status: "Active",
  },
  {
    type: "Restricted Zone Entry",
    description: "Worker entered Restricted Zone A",
    location: "Storage Area",
    object: "W-07",
    severity: "Medium",
    timestamp: "Sep 21, 14:26:04",
    status: "Investigating",
  },
  {
    type: "PPE Violation",
    description: "Safety vest not detected",
    location: "Packing Zone",
    object: "W-18",
    severity: "Medium",
    timestamp: "Sep 21, 14:19:37",
    status: "Active",
  },
  {
    type: "Speed Threshold",
    description: "Forklift exceeded 8 km/h zone limit",
    location: "Aisle C4",
    object: "FL-05",
    severity: "High",
    timestamp: "Sep 21, 13:58:20",
    status: "Resolved",
  },
  {
    type: "PPE Violation",
    description: "Hard hat not detected",
    location: "Receiving Bay",
    object: "W-21",
    severity: "Low",
    timestamp: "Sep 21, 13:42:11",
    status: "Resolved",
  },
  {
    type: "Blocked Exit",
    description: "Pallet obstructed marked emergency path",
    location: "Dispatch Zone",
    object: "PL-42",
    severity: "Medium",
    timestamp: "Sep 21, 12:55:08",
    status: "Resolved",
  },
];
type EventRow = (typeof events)[number];
const kpis = [
  { label: "Total Alerts", value: "18", detail: "Last 7 days", icon: ShieldAlert, tone: "primary" },
  {
    label: "Critical Alerts",
    value: "3",
    detail: "Requires attention",
    icon: Siren,
    tone: "danger",
  },
  {
    label: "Proximity Violations",
    value: "7",
    detail: "39% of incidents",
    icon: AlertTriangle,
    tone: "primary",
  },
  {
    label: "Resolved Alerts",
    value: "15",
    detail: "83% resolution rate",
    icon: CheckCircle2,
    tone: "success",
  },
];
const badge = (value: string) =>
  value === "High" || value === "Active"
    ? "border-danger/30 bg-danger/10 text-danger"
    : value === "Resolved"
      ? "border-success/30 bg-success/10 text-success"
      : "border-primary/30 bg-primary/10 text-primary";

function DatePicker({
  date,
  onChange,
}: {
  date?: Date | undefined;
  onChange: (value?: Date | undefined) => void;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className="h-9 justify-start gap-2 border-border bg-card/90 px-3 text-left text-xs font-normal text-foreground shadow-none"
        >
          <CalendarIcon className="size-4 text-primary" />
          {date ? format(date, "MMM d, yyyy") : "Select date"}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="end">
        <Calendar
          mode="single"
          selected={date}
          onSelect={onChange}
          initialFocus
          className="pointer-events-auto p-3"
        />
      </PopoverContent>
    </Popover>
  );
}
function IncidentChart() {
  return (
    <section className="border border-border bg-card/95 shadow-panel">
      <div className="border-b border-border px-5 py-4">
        <h2 className="text-sm font-semibold">Safety Incidents Over Time</h2>
        <p className="mt-1 text-[10px] text-muted-foreground">
          Seven-day incident frequency by category
        </p>
      </div>
      <div className="h-[310px] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={trend} margin={{ top: 12, right: 8, left: -24, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="day"
              tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <ChartTooltip
              contentStyle={{
                background: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 4,
                fontSize: 11,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 10, paddingTop: 10 }} />
            <Bar dataKey="proximity" name="Proximity" fill="var(--danger)" radius={[2, 2, 0, 0]} />
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
  );
}
function ActiveAlerts() {
  return (
    <section className="border border-border bg-card/95 shadow-panel">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold">Active Alerts</h2>
          <p className="mt-1 text-[10px] text-muted-foreground">Open incidents requiring review</p>
        </div>
        <span className="font-mono text-xs text-danger">03 OPEN</span>
      </div>
      <div className="divide-y divide-border">
        {activeAlerts.map((alert) => {
          const Icon = alert.icon;
          return (
            <article key={alert.title} className="p-4 transition-colors hover:bg-surface-hover/30">
              <div className="flex gap-3">
                <div
                  className={cn(
                    "grid size-9 shrink-0 place-items-center rounded-md border",
                    alert.severity === "High"
                      ? "border-danger/25 bg-danger/10 text-danger"
                      : "border-primary/25 bg-primary/10 text-primary",
                  )}
                >
                  <Icon className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-xs font-semibold">{alert.title}</h3>
                    <span
                      className={cn(
                        "rounded-sm border px-2 py-0.5 text-[9px] font-semibold uppercase",
                        badge(alert.severity),
                      )}
                    >
                      {alert.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">{alert.description}</p>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[9px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <MapPin className="size-3" />
                      {alert.location}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock3 className="size-3" />
                      {alert.time}
                    </span>
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
function EventHistory() {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("All");
  const [status, setStatus] = useState("All");
  const [date, setDate] = useState<Date | undefined>();
  const [selected, setSelected] = useState<EventRow>();
  const filtered = useMemo(
    () =>
      events.filter(
        (event) =>
          `${event.type} ${event.description} ${event.location} ${event.object}`
            .toLowerCase()
            .includes(query.toLowerCase()) &&
          (severity === "All" || event.severity === severity) &&
          (status === "All" || event.status === status),
      ),
    [query, severity, status],
  );
  return (
    <>
      <section className="overflow-hidden border border-border bg-card/95 shadow-panel">
        <div className="border-b border-border px-5 py-4">
          <h2 className="text-sm font-semibold">Safety Event History</h2>
          <p className="mt-1 text-[10px] text-muted-foreground">
            Investigate and review recorded safety incidents
          </p>
        </div>
        <div className="grid gap-2 border-b border-border p-4 sm:grid-cols-2 xl:grid-cols-[minmax(220px,1fr)_170px_170px_auto]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search events, locations, IDs..."
              className="h-9 border-border bg-background/50 pl-9 text-xs"
            />
          </div>
          {[
            [severity, setSeverity, "Severity", ["All", "High", "Medium", "Low"]],
            [status, setStatus, "Status", ["All", "Active", "Investigating", "Resolved"]],
          ].map(([value, setter, label, options]) => (
            <Select
              key={label as string}
              value={value as string}
              onValueChange={setter as (value: string) => void}
            >
              <SelectTrigger className="h-9 border-border bg-background/50 text-xs">
                <SelectValue placeholder={label as string} />
              </SelectTrigger>
              <SelectContent>
                {(options as string[]).map((option) => (
                  <SelectItem key={option} value={option}>
                    {option === "All" ? `All ${label}` : option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ))}
          <DatePicker date={date} onChange={setDate} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1050px] text-left">
            <thead>
              <tr className="border-b border-border bg-background/35 text-[9px] uppercase text-muted-foreground">
                {[
                  "Alert Type",
                  "Description",
                  "Location",
                  "Object ID",
                  "Severity",
                  "Timestamp",
                  "Status",
                  "Action",
                ].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((event) => (
                <tr
                  key={`${event.object}-${event.timestamp}`}
                  tabIndex={0}
                  onClick={() => setSelected(event)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") setSelected(event);
                  }}
                  className="cursor-pointer text-[11px] outline-none transition-colors hover:bg-surface-hover/40 focus:bg-surface-hover/40"
                >
                  <td className="whitespace-nowrap px-4 py-3.5 font-medium">{event.type}</td>
                  <td className="max-w-[220px] truncate px-4 py-3.5 text-muted-foreground">
                    {event.description}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.5 text-muted-foreground">
                    {event.location}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.5 font-mono">{event.object}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={cn(
                        "rounded-sm border px-2 py-1 text-[9px] font-semibold uppercase",
                        badge(event.severity),
                      )}
                    >
                      {event.severity}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.5 font-mono text-muted-foreground">
                    {event.timestamp}
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={cn(
                        "rounded-sm border px-2 py-1 text-[9px] font-semibold uppercase",
                        badge(event.status),
                      )}
                    >
                      {event.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-primary"
                      aria-label={`View ${event.type}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelected(event);
                      }}
                    >
                      <ChevronRight />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="p-8 text-center text-xs text-muted-foreground">
              No safety events match these filters.
            </p>
          )}
        </div>
      </section>
      <Dialog
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) setSelected(undefined);
        }}
      >
        <DialogContent className="border-border bg-popover sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldAlert className="size-5 text-primary" />
              Alert Detail
            </DialogTitle>
            <DialogDescription>Recorded safety event information</DialogDescription>
          </DialogHeader>
          {selected && (
            <div className="grid gap-4 pt-2 sm:grid-cols-2">
              {[
                ["Alert Type", selected.type],
                ["Object ID", selected.object],
                ["Description", selected.description],
                ["Location", selected.location],
                ["Severity", selected.severity],
                ["Status", selected.status],
                ["Timestamp", selected.timestamp],
                ["Detection Source", "CAM-01 · Main Warehouse"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className={cn(
                    "border-b border-border pb-3",
                    label === "Description" && "sm:col-span-2",
                  )}
                >
                  <p className="text-[9px] uppercase text-muted-foreground">{label}</p>
                  <p className="mt-1 text-xs font-medium">{value}</p>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
export function SafetyMonitoringPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [date, setDate] = useState<Date | undefined>(new Date(2026, 8, 21));
  return (
    <div className="min-h-screen bg-background text-foreground">
      <WarehouseSidebar active="Safety" />
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-background/80" onClick={() => setMobileOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
            <WarehouseSidebar active="Safety" mobile onNavigate={() => setMobileOpen(false)} />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMobileOpen(false)}
              className="absolute right-3 top-4"
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
          <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6 xl:px-8">
            <div className="mx-auto flex min-h-18 max-w-[1600px] items-center gap-3 py-3">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setMobileOpen(true)}
                className="shrink-0 border-border bg-card/80 lg:hidden"
                aria-label="Open navigation"
              >
                <Menu />
              </Button>
              <div className="min-w-0 flex-1">
                <h1 className="truncate text-lg font-semibold sm:text-xl">Safety Monitoring</h1>
                <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                  Monitor workplace safety risks and violations
                </p>
              </div>
              <div className="hidden items-center gap-2 border border-success/20 bg-success/5 px-3 py-2 sm:flex">
                <span className="size-2 rounded-full bg-success" />
                <span className="text-[10px] font-semibold text-success">Safety System Active</span>
              </div>
              <DatePicker date={date} onChange={setDate} />
            </div>
          </header>
          <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {kpis.map((kpi) => {
                const Icon = kpi.icon;
                return (
                  <article
                    key={kpi.label}
                    className="border border-border bg-card/95 p-4 shadow-panel"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-[10px] font-medium uppercase text-muted-foreground">
                          {kpi.label}
                        </p>
                        <p className="mt-2 font-mono text-3xl font-semibold">{kpi.value}</p>
                      </div>
                      <div
                        className={cn(
                          "grid size-9 place-items-center rounded-md border",
                          kpi.tone === "danger"
                            ? "border-danger/25 bg-danger/10 text-danger"
                            : kpi.tone === "success"
                              ? "border-success/25 bg-success/10 text-success"
                              : "border-primary/25 bg-primary/10 text-primary",
                        )}
                      >
                        <Icon className="size-4" />
                      </div>
                    </div>
                    <p className="mt-3 text-[10px] text-muted-foreground">{kpi.detail}</p>
                  </article>
                );
              })}
            </div>
            <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(340px,0.7fr)]">
              <IncidentChart />
              <ActiveAlerts />
            </div>
            <EventHistory />
            <footer className="flex justify-between border-t border-border/60 py-2 font-mono text-[9px] uppercase text-muted-foreground">
              <span>WarehouseVision AI · Safety Control</span>
              <span>Last sync: just now</span>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}
