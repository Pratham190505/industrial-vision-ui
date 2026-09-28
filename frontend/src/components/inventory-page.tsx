import { useMemo, useState } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  Boxes,
  CalendarIcon,
  Camera,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Filter,
  Layers,
  Menu,
  PackageCheck,
  PackageOpen,
  Radio,
  Search,
  SlidersHorizontal,
  TrendingDown,
  TrendingUp,
  Warehouse,
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
import {
  inventoryData,
  inventoryEvents,
  inventoryKPIs,
  warehouses,
  type InventoryEvent,
} from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

const ITEMS_PER_PAGE = 7;

const statusStyle = (status: InventoryEvent["status"]) => {
  switch (status) {
    case "Verified":
      return "border-success/30 bg-success/10 text-success";
    case "Logged":
      return "border-primary/30 bg-primary/10 text-primary";
    case "Flagged":
      return "border-danger/30 bg-danger/10 text-danger";
    default:
      return "border-border bg-muted/40 text-muted-foreground";
  }
};

const directionStyle = (direction: InventoryEvent["direction"]) => {
  return direction === "Inbound"
    ? "border-primary/30 bg-primary/10 text-primary"
    : "border-success/30 bg-success/10 text-success";
};

export function InventoryPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [warehouse, setWarehouse] = useState("North Distribution Center");
  const [query, setQuery] = useState("");
  const [objectType, setObjectType] = useState<string>("All");
  const [direction, setDirection] = useState<string>("All");
  const [cameraFilter, setCameraFilter] = useState<string>("All");
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date(2026, 8, 21));
  const [selectedEvent, setSelectedEvent] = useState<InventoryEvent | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  // Filtered inventory events
  const filteredEvents = useMemo(() => {
    return inventoryEvents.filter((item) => {
      const matchesQuery =
        item.id.toLowerCase().includes(query.toLowerCase()) ||
        item.camera.toLowerCase().includes(query.toLowerCase()) ||
        item.zone.toLowerCase().includes(query.toLowerCase());

      const matchesType = objectType === "All" || item.objectType === objectType;
      const matchesDirection = direction === "All" || item.direction === direction;
      const matchesCamera = cameraFilter === "All" || item.camera === cameraFilter;

      return matchesQuery && matchesType && matchesDirection && matchesCamera;
    });
  }, [query, objectType, direction, cameraFilter]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredEvents.length / ITEMS_PER_PAGE));
  const paginatedEvents = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredEvents.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredEvents, currentPage]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sidebar navigation */}
      <WarehouseSidebar active="Inventory" />

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
            <WarehouseSidebar active="Inventory" mobile onNavigate={() => setMobileOpen(false)} />
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

      {/* Main Content */}
      <main className="relative min-h-screen lg:ml-64">
        {/* Warehouse Background Overlay */}
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
                <h1 className="truncate text-lg font-semibold sm:text-xl">Inventory Management</h1>
                <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                  Automated computer vision detection, counting & inbound/outbound flow
                </p>
              </div>

              {/* Warehouse selector */}
              <Select value={warehouse} onValueChange={setWarehouse}>
                <SelectTrigger className="hidden h-9 w-56 border-border bg-card/80 text-xs shadow-none md:flex">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Live status badge */}
              <div className="hidden items-center gap-2 border border-success/20 bg-success/5 px-3 py-2 sm:flex">
                <span className="size-2 rounded-full bg-success" />
                <span className="text-[10px] font-semibold text-success">Vision Count Active</span>
              </div>

              {/* Date Filter */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="h-9 justify-start gap-2 border-border bg-card/90 px-3 text-left text-xs font-normal text-foreground shadow-none hover:bg-surface-hover"
                  >
                    <CalendarIcon className="size-4 text-primary" />
                    {selectedDate ? format(selectedDate, "MMM d, yyyy") : "Select date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="end">
                  <Calendar
                    mode="single"
                    selected={selectedDate}
                    onSelect={setSelectedDate}
                    initialFocus
                    className="p-3"
                  />
                </PopoverContent>
              </Popover>
            </div>
          </header>

          <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
            {/* KPI Cards Grid */}
            <section
              className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5 xl:gap-4"
              aria-label="Inventory Key Performance Indicators"
            >
              {inventoryKPIs.map((kpi) => {
                const Icon = kpi.icon;
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
                        <p className="mt-2 font-mono text-2xl font-bold tabular-nums text-foreground sm:text-3xl">
                          {kpi.value}
                        </p>
                      </div>
                      <div
                        className={cn(
                          "grid size-9 place-items-center rounded-md border",
                          isSuccess
                            ? "border-success/25 bg-success/10 text-success"
                            : "border-primary/25 bg-primary/10 text-primary",
                        )}
                      >
                        <Icon className="size-4.5" aria-hidden="true" />
                      </div>
                    </div>
                    <div className="mt-3.5 flex items-center gap-2 border-t border-border/70 pt-2.5">
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          isSuccess ? "bg-success" : "bg-primary",
                        )}
                      />
                      <p className="truncate text-[11px] text-muted-foreground">{kpi.detail}</p>
                    </div>
                  </article>
                );
              })}
            </section>

            {/* Inventory Movement Chart */}
            <section className="border border-border bg-card/95 shadow-panel">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">
                    Inventory Movement Trends
                  </h2>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Hourly inbound vs. outbound units detected by camera sensors
                  </p>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-primary" />
                    Inbound Flow (179 units)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-success" />
                    Outbound Flow (165 units)
                  </span>
                </div>
              </div>
              <div className="h-72 p-4 sm:p-5">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={inventoryData}
                    margin={{ top: 12, right: 12, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
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
                    <ChartTooltip
                      contentStyle={{
                        background: "var(--popover)",
                        border: "1px solid var(--border)",
                        borderRadius: 4,
                        fontSize: 11,
                        color: "var(--foreground)",
                      }}
                    />
                    <Bar
                      dataKey="inbound"
                      name="Inbound"
                      fill="var(--primary)"
                      radius={[3, 3, 0, 0]}
                    />
                    <Bar
                      dataKey="outbound"
                      name="Outbound"
                      fill="var(--success)"
                      radius={[3, 3, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* Inventory Event History Table */}
            <section className="overflow-hidden border border-border bg-card/95 shadow-panel">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">Inventory Event History</h2>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Live detection log of tracked boxes and pallets with camera source & confidence
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-primary">
                    {filteredEvents.length} Events Tracked
                  </span>
                </div>
              </div>

              {/* Filters Toolbar */}
              <div className="grid gap-2.5 border-b border-border p-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setCurrentPage(1);
                    }}
                    placeholder="Search Object ID, camera, zone..."
                    className="h-9 border-border bg-background/50 pl-9 text-xs text-foreground placeholder:text-muted-foreground"
                  />
                </div>

                {/* Object Type filter */}
                <Select
                  value={objectType}
                  onValueChange={(val) => {
                    setObjectType(val);
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="h-9 border-border bg-background/50 text-xs">
                    <SelectValue placeholder="Object Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Object Types</SelectItem>
                    <SelectItem value="Box">Boxes only</SelectItem>
                    <SelectItem value="Pallet">Pallets only</SelectItem>
                  </SelectContent>
                </Select>

                {/* Direction filter */}
                <Select
                  value={direction}
                  onValueChange={(val) => {
                    setDirection(val);
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="h-9 border-border bg-background/50 text-xs">
                    <SelectValue placeholder="Direction" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Directions</SelectItem>
                    <SelectItem value="Inbound">Inbound only</SelectItem>
                    <SelectItem value="Outbound">Outbound only</SelectItem>
                  </SelectContent>
                </Select>

                {/* Camera filter */}
                <Select
                  value={cameraFilter}
                  onValueChange={(val) => {
                    setCameraFilter(val);
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="h-9 border-border bg-background/50 text-xs">
                    <SelectValue placeholder="Camera" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Cameras</SelectItem>
                    <SelectItem value="CAM-01">CAM-01 (Main Warehouse)</SelectItem>
                    <SelectItem value="CAM-02">CAM-02 (Receiving Bay)</SelectItem>
                    <SelectItem value="CAM-03">CAM-03 (Dispatch Zone)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-left">
                  <thead>
                    <tr className="border-b border-border bg-background/40 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-4 py-3">Object ID</th>
                      <th className="px-4 py-3">Object Type</th>
                      <th className="px-4 py-3">Direction</th>
                      <th className="px-4 py-3">Camera</th>
                      <th className="px-4 py-3">Timestamp</th>
                      <th className="px-4 py-3">Confidence</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {paginatedEvents.map((item) => (
                      <tr
                        key={item.id + item.timestamp}
                        tabIndex={0}
                        onClick={() => setSelectedEvent(item)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") setSelectedEvent(item);
                        }}
                        className="cursor-pointer text-[11px] outline-none transition-colors hover:bg-surface-hover/50 focus:bg-surface-hover/50"
                      >
                        <td className="whitespace-nowrap px-4 py-3.5 font-mono font-medium text-primary">
                          {item.id}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5 font-medium text-foreground">
                          <span className="flex items-center gap-1.5">
                            {item.objectType === "Box" ? (
                              <Boxes className="size-3.5 text-primary" />
                            ) : (
                              <PackageCheck className="size-3.5 text-success" />
                            )}
                            {item.objectType}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-[9px] font-bold uppercase",
                              directionStyle(item.direction),
                            )}
                          >
                            {item.direction === "Inbound" ? (
                              <ArrowDownLeft className="size-3" />
                            ) : (
                              <ArrowUpRight className="size-3" />
                            )}
                            {item.direction}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5 font-mono text-muted-foreground">
                          <span className="flex items-center gap-1.5">
                            <Camera className="size-3 text-primary/70" />
                            {item.camera}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5 font-mono text-muted-foreground">
                          {item.timestamp}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-semibold text-foreground">
                              {item.confidence}%
                            </span>
                            <div className="h-1.5 w-14 overflow-hidden rounded-full bg-muted">
                              <div
                                className={cn(
                                  "h-full rounded-full",
                                  item.confidence >= 90
                                    ? "bg-success"
                                    : item.confidence >= 85
                                      ? "bg-primary"
                                      : "bg-danger",
                                )}
                                style={{ width: `${item.confidence}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5">
                          <span
                            className={cn(
                              "rounded-sm border px-2 py-0.5 text-[9px] font-bold uppercase",
                              statusStyle(item.status),
                            )}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3.5 text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 text-muted-foreground hover:bg-surface-hover hover:text-primary"
                            aria-label={`View details for ${item.id}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedEvent(item);
                            }}
                          >
                            <ChevronRight className="size-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filteredEvents.length === 0 && (
                  <div className="p-8 text-center text-xs text-muted-foreground">
                    <Boxes className="mx-auto mb-2 size-8 text-muted-foreground/40" />
                    No inventory events match the selected filters.
                  </div>
                )}
              </div>

              {/* Pagination Controls */}
              {filteredEvents.length > 0 && (
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-3 text-xs text-muted-foreground">
                  <span className="font-mono text-[11px]">
                    Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–
                    {Math.min(currentPage * ITEMS_PER_PAGE, filteredEvents.length)} of{" "}
                    {filteredEvents.length} events
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage === 1}
                      onClick={() => handlePageChange(currentPage - 1)}
                      className="h-8 border-border bg-card text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
                    >
                      <ChevronLeft className="size-3.5 mr-1" /> Prev
                    </Button>
                    <span className="px-2 font-mono text-[11px] text-foreground">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage === totalPages}
                      onClick={() => handlePageChange(currentPage + 1)}
                      className="h-8 border-border bg-card text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
                    >
                      Next <ChevronRight className="size-3.5 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </section>

            {/* Footer */}
            <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
              <span>WarehouseVision AI · Inventory CV Subsystem</span>
              <span>Last vision sync: 2 sec ago</span>
            </footer>
          </div>
        </div>
      </main>

      {/* Inventory Event Detail Dialog */}
      <Dialog
        open={Boolean(selectedEvent)}
        onOpenChange={(open) => {
          if (!open) setSelectedEvent(null);
        }}
      >
        <DialogContent className="border-border bg-popover sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base text-foreground">
              <PackageOpen className="size-5 text-primary" />
              Inventory Event Details
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Computer vision detection bounding box & object telemetry
            </DialogDescription>
          </DialogHeader>

          {selectedEvent && (
            <div className="space-y-4 pt-2">
              {/* Snapshot Mock */}
              <div className="relative aspect-video overflow-hidden rounded-md border border-border bg-background">
                <img
                  src={warehouseAsset.url}
                  alt="Detection snapshot"
                  className="size-full object-cover saturate-[0.6]"
                />
                <div className="absolute inset-0 bg-camera-overlay" />
                <div className="pointer-events-none absolute inset-0 scanlines opacity-30" />
                <div className="absolute left-3 top-3 border border-primary/50 bg-background/80 px-2 py-0.5 font-mono text-[9px] text-primary">
                  {selectedEvent.camera} · CROP
                </div>
                {/* Mock bounding box overlay */}
                <div className="absolute inset-x-[28%] inset-y-[22%] border-2 border-primary">
                  <span className="absolute -top-5 left-0 bg-primary px-1.5 py-0.5 font-mono text-[8px] font-bold text-primary-foreground">
                    {selectedEvent.id} {selectedEvent.confidence}%
                  </span>
                </div>
              </div>

              {/* Data Grid */}
              <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
                <div className="border-b border-border/60 pb-2">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Object ID
                  </p>
                  <p className="mt-1 font-mono text-xs font-bold text-primary">
                    {selectedEvent.id}
                  </p>
                </div>
                <div className="border-b border-border/60 pb-2">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Classification
                  </p>
                  <p className="mt-1 text-xs font-semibold text-foreground">
                    {selectedEvent.objectType}
                  </p>
                </div>
                <div className="border-b border-border/60 pb-2">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Direction
                  </p>
                  <p className="mt-1 text-xs font-semibold text-foreground">
                    {selectedEvent.direction} Flow
                  </p>
                </div>
                <div className="border-b border-border/60 pb-2">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Source Camera
                  </p>
                  <p className="mt-1 font-mono text-xs text-foreground">{selectedEvent.camera}</p>
                </div>
                <div className="border-b border-border/60 pb-2">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Zone Location
                  </p>
                  <p className="mt-1 text-xs text-foreground">{selectedEvent.zone}</p>
                </div>
                <div className="border-b border-border/60 pb-2">
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Estimated Dimensions
                  </p>
                  <p className="mt-1 font-mono text-xs text-foreground">
                    {selectedEvent.dimensions || "N/A"}
                  </p>
                </div>
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    AI Confidence Score
                  </p>
                  <p className="mt-1 font-mono text-xs font-bold text-success">
                    {selectedEvent.confidence}%
                  </p>
                </div>
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-muted-foreground">
                    Tracking Status
                  </p>
                  <span
                    className={cn(
                      "mt-1 inline-block rounded-sm border px-2 py-0.5 text-[9px] font-bold uppercase",
                      statusStyle(selectedEvent.status),
                    )}
                  >
                    {selectedEvent.status}
                  </span>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
