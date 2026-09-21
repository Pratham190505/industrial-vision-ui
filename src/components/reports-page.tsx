import { useState } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  Boxes,
  Calendar as CalendarIcon,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  Filter,
  Forklift,
  Layers,
  Menu,
  Printer,
  Radio,
  Share2,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Users,
  Warehouse,
  X,
} from "lucide-react";
import { toast } from "sonner";

import warehouseAsset from "@/assets/warehouse-command-center.jpg.asset.json";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WarehouseSidebar } from "@/components/warehouse-sidebar";
import {
  inventoryEvents,
  reportsData,
  warehouses,
  zoneDetailedMetrics,
} from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

export function ReportsPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [warehouse, setWarehouse] = useState("North Distribution Center");
  const [dateRange, setDateRange] = useState("Today");
  const [cameraFilter, setCameraFilter] = useState("All");
  const [zoneFilter, setZoneFilter] = useState("All");
  const [activeTab, setActiveTab] = useState("daily");

  // Client-side export handlers
  const handleExportCSV = () => {
    try {
      const headers = [
        "Object ID",
        "Object Type",
        "Direction",
        "Camera",
        "Timestamp",
        "Confidence",
        "Status",
        "Zone",
      ];
      const rows = inventoryEvents.map((e) => [
        e.id,
        e.objectType,
        e.direction,
        e.camera,
        e.timestamp,
        `${e.confidence}%`,
        e.status,
        e.zone,
      ]);
      const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute(
        "download",
        `warehouse-vision-report-${dateRange.toLowerCase().replace(/\s+/g, "-")}.csv`,
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("CSV Report generated and downloaded successfully");
    } catch {
      toast.error("Failed to generate CSV export");
    }
  };

  const handleExportJSON = () => {
    try {
      const payload = {
        meta: {
          facility: warehouse,
          dateRange,
          cameraFilter,
          zoneFilter,
          generatedAt: new Date().toISOString(),
        },
        ...reportsData,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute(
        "download",
        `warehouse-vision-audit-${dateRange.toLowerCase().replace(/\s+/g, "-")}.json`,
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("JSON Summary audit log downloaded successfully");
    } catch {
      toast.error("Failed to generate JSON export");
    }
  };

  const handlePrint = () => {
    toast.info("Opening browser print dialog...");
    window.print();
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sidebar Navigation */}
      <WarehouseSidebar active="Reports" />

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
            <WarehouseSidebar active="Reports" mobile onNavigate={() => setMobileOpen(false)} />
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
        {/* Background Image & Dark industrial overlay */}
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
                <h1 className="truncate text-lg font-semibold sm:text-xl">
                  Operational & Safety Reports
                </h1>
                <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                  Auditable executive summaries, incident digests & inventory throughput logs
                </p>
              </div>

              {/* Warehouse selector */}
              <Select value={warehouse} onValueChange={setWarehouse}>
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
              <Select value={dateRange} onValueChange={setDateRange}>
                <SelectTrigger className="h-9 w-32 border-border bg-card/90 text-xs shadow-none">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Today">Today's Shift</SelectItem>
                  <SelectItem value="Yesterday">Yesterday</SelectItem>
                  <SelectItem value="Last 7 Days">Last 7 Days</SelectItem>
                  <SelectItem value="This Month">This Month</SelectItem>
                </SelectContent>
              </Select>

              {/* Export Dropdown Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button className="h-9 gap-2 border border-primary/40 bg-primary px-3 text-xs font-semibold text-primary-foreground shadow-amber hover:bg-primary/90">
                    <Download className="size-3.5" />
                    <span>Export Report</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48 border-border bg-popover">
                  <DropdownMenuItem
                    onClick={handleExportCSV}
                    className="flex cursor-pointer items-center gap-2 text-xs"
                  >
                    <FileSpreadsheet className="size-4 text-success" />
                    <span>Export as CSV (.csv)</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handleExportJSON}
                    className="flex cursor-pointer items-center gap-2 text-xs"
                  >
                    <FileText className="size-4 text-primary" />
                    <span>Export as JSON (.json)</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handlePrint}
                    className="flex cursor-pointer items-center gap-2 text-xs"
                  >
                    <Printer className="size-4 text-muted-foreground" />
                    <span>Print / Save as PDF</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
            {/* Filter Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border border-border bg-card/90 p-3.5 shadow-panel">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  <Filter className="size-3.5 text-primary" /> Report Scope:
                </span>

                <Select value={cameraFilter} onValueChange={setCameraFilter}>
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

                <Select value={zoneFilter} onValueChange={setZoneFilter}>
                  <SelectTrigger className="h-8 w-40 border-border bg-background/60 text-xs">
                    <SelectValue placeholder="All Zones" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="All">All Zones</SelectItem>
                    <SelectItem value="Receiving">Receiving Bay</SelectItem>
                    <SelectItem value="Main Storage">Main Storage</SelectItem>
                    <SelectItem value="Packing">Packing Line</SelectItem>
                    <SelectItem value="Dispatch">Dispatch Dock</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-3 font-mono text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="size-3 text-success" /> Verified Vision Audit
                </span>
                <span>•</span>
                <span>Report ID: WV-RPT-2026-0921</span>
              </div>
            </div>

            {/* Structured Report Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-5">
              <TabsList className="grid h-10 w-full grid-cols-2 border border-border bg-card/90 p-1 md:grid-cols-4">
                <TabsTrigger
                  value="daily"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Clock className="size-3.5" />
                  Daily Monitoring Summary
                </TabsTrigger>
                <TabsTrigger
                  value="safety"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <ShieldAlert className="size-3.5" />
                  Safety Incident Report
                </TabsTrigger>
                <TabsTrigger
                  value="inventory"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Boxes className="size-3.5" />
                  Inventory Movement Report
                </TabsTrigger>
                <TabsTrigger
                  value="equipment"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Forklift className="size-3.5" />
                  Worker & Forklift Activity
                </TabsTrigger>
              </TabsList>

              {/* Tab 1: Daily Monitoring Summary */}
              <TabsContent value="daily" className="space-y-5 outline-none">
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Total Frames Processed
                    </p>
                    <p className="mt-1 font-mono text-2xl font-bold text-foreground">
                      {reportsData.dailySummary.totalFramesProcessed}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Zero dropped frames in period
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Detection Accuracy Rate
                    </p>
                    <p className="mt-1 font-mono text-2xl font-bold text-success">
                      {reportsData.dailySummary.meanAccuracy}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      YOLOv8x Industrial Model
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">System Uptime</p>
                    <p className="mt-1 font-mono text-2xl font-bold text-foreground">
                      {reportsData.dailySummary.uptime}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Edge Node 01 & 02 Nominal
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Total Objects Tracked
                    </p>
                    <p className="mt-1 font-mono text-2xl font-bold text-primary">
                      {reportsData.dailySummary.totalDetections}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Workers, forklifts, boxes, pallets
                    </p>
                  </div>
                </div>

                <div className="border border-border bg-card/95 p-5 shadow-panel">
                  <h3 className="text-sm font-semibold text-foreground">
                    Shift Operational Highlights
                  </h3>
                  <div className="mt-3 grid gap-3 divide-y divide-border/60 text-xs sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                    <div className="pt-2 sm:pr-4 sm:pt-0">
                      <p className="font-semibold text-foreground">Personnel Density</p>
                      <p className="mt-1 text-muted-foreground">
                        Peak staffing reached 24 active workers at 14:00. Average worker utilization
                        stood at 87.5% across primary picking and packing zones.
                      </p>
                    </div>
                    <div className="pt-2 sm:px-4 sm:pt-0">
                      <p className="font-semibold text-foreground">Material Flow Throughput</p>
                      <p className="mt-1 text-muted-foreground">
                        344 items handled (179 inbound / 165 outbound). Net inventory increased by
                        14 units with receiving bay turnaround average of 18.5 min.
                      </p>
                    </div>
                    <div className="pt-2 sm:pl-4 sm:pt-0">
                      <p className="font-semibold text-foreground">Safety Compliance Index</p>
                      <p className="mt-1 text-muted-foreground">
                        18 safety triggers logged with 15 successfully cleared. Mean time to resolve
                        was 4.2 minutes with 100% PPE compliance recorded in Storage Area B.
                      </p>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Tab 2: Safety Incident Report */}
              <TabsContent value="safety" className="space-y-5 outline-none">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Recorded Safety Triggers
                    </p>
                    <p className="mt-1 font-mono text-3xl font-bold text-danger">
                      {reportsData.safetySummary.totalIncidents}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      {reportsData.safetySummary.criticalIncidents} flagged high severity
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Mean Resolution Time
                    </p>
                    <p className="mt-1 font-mono text-3xl font-bold text-primary">
                      {reportsData.safetySummary.meanTimeToResolve}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Target threshold: &lt; 5.0 min
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Overall Compliance Score
                    </p>
                    <p className="mt-1 font-mono text-3xl font-bold text-success">
                      {reportsData.safetySummary.complianceScore}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      PPE Compliance: {reportsData.safetySummary.ppeComplianceRate}
                    </p>
                  </div>
                </div>

                <div className="border border-border bg-card/95 p-5 shadow-panel">
                  <h3 className="text-sm font-semibold text-foreground">
                    Safety Incident Breakdown & Corrective Actions
                  </h3>
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[700px] text-left text-xs">
                      <thead>
                        <tr className="border-b border-border text-[9px] uppercase tracking-wider text-muted-foreground">
                          <th className="pb-2">Incident Classification</th>
                          <th className="pb-2">Frequency</th>
                          <th className="pb-2">Primary Zone</th>
                          <th className="pb-2">Resolution Status</th>
                          <th className="pb-2">Corrective Action Taken</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        <tr>
                          <td className="py-2.5 font-medium text-foreground">
                            Worker–Forklift Proximity
                          </td>
                          <td className="py-2.5 font-mono text-danger">7 events</td>
                          <td className="py-2.5 text-muted-foreground">Loading Zone</td>
                          <td className="py-2.5 text-success">All 7 Resolved</td>
                          <td className="py-2.5 text-muted-foreground">
                            Aisle sound beacons dispatched; speed governed
                          </td>
                        </tr>
                        <tr>
                          <td className="py-2.5 font-medium text-foreground">
                            Restricted Zone Entry
                          </td>
                          <td className="py-2.5 font-mono text-primary">5 events</td>
                          <td className="py-2.5 text-muted-foreground">Storage Area A</td>
                          <td className="py-2.5 text-success">All 5 Cleared</td>
                          <td className="py-2.5 text-muted-foreground">
                            Operator badge verification; supervisor notified
                          </td>
                        </tr>
                        <tr>
                          <td className="py-2.5 font-medium text-foreground">PPE Non-Compliance</td>
                          <td className="py-2.5 font-mono text-chart-2">6 events</td>
                          <td className="py-2.5 text-muted-foreground">Packing Line 2</td>
                          <td className="py-2.5 text-success">All 6 Cleared</td>
                          <td className="py-2.5 text-muted-foreground">
                            Safety vest & hard-hat re-issue at bay entrance
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </TabsContent>

              {/* Tab 3: Inventory Movement Report */}
              <TabsContent value="inventory" className="space-y-5 outline-none">
                <div className="grid gap-4 sm:grid-cols-4">
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">Boxes Detected</p>
                    <p className="mt-1 font-mono text-2xl font-bold text-primary">
                      {reportsData.inventorySummary.boxesDetected}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">Active in view</p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">Pallets Detected</p>
                    <p className="mt-1 font-mono text-2xl font-bold text-success">
                      {reportsData.inventorySummary.palletsDetected}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">Tracked in view</p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">Inbound Total</p>
                    <p className="mt-1 font-mono text-2xl font-bold text-foreground">
                      {reportsData.inventorySummary.inboundTotal}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">Through Receiving</p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">Outbound Total</p>
                    <p className="mt-1 font-mono text-2xl font-bold text-foreground">
                      {reportsData.inventorySummary.outboundTotal}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">Through Dispatch</p>
                  </div>
                </div>

                <div className="border border-border bg-card/95 p-5 shadow-panel">
                  <h3 className="text-sm font-semibold text-foreground">
                    Movement & Flow Observations
                  </h3>
                  <div className="mt-3 space-y-2 text-xs text-muted-foreground">
                    <p>
                      • Peak inventory turnover occurred between{" "}
                      <strong className="text-foreground">10:00 and 14:00</strong> with a high of 71
                      units/hr recorded across CAM-02 and CAM-03.
                    </p>
                    <p>
                      • Net warehouse movement was{" "}
                      <strong className="text-success">+14 units</strong>, matching estimated stock
                      adjustments without discrepancy.
                    </p>
                    <p>
                      • Optical character recognition (OCR) and barcode reading confidence averaged
                      94.2% on standard carton boxes.
                    </p>
                  </div>
                </div>
              </TabsContent>

              {/* Tab 4: Worker & Forklift Activity */}
              <TabsContent value="equipment" className="space-y-5 outline-none">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Active Forklift Fleet
                    </p>
                    <p className="mt-1 font-mono text-3xl font-bold text-primary">
                      {reportsData.equipmentSummary.activeForklifts} / 5
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      100% fleet availability
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Fleet Operating Hours
                    </p>
                    <p className="mt-1 font-mono text-3xl font-bold text-foreground">
                      {reportsData.equipmentSummary.totalFleetOperatingHours}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Idle/Moving ratio: {reportsData.equipmentSummary.idleVsMovingRatio}
                    </p>
                  </div>
                  <div className="border border-border bg-card/95 p-4 shadow-panel">
                    <p className="text-[10px] uppercase text-muted-foreground">
                      Proximity Encounters
                    </p>
                    <p className="mt-1 font-mono text-3xl font-bold text-success">
                      {reportsData.equipmentSummary.safestOperator}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Top safety compliance record
                    </p>
                  </div>
                </div>

                <div className="border border-border bg-card/95 p-5 shadow-panel">
                  <h3 className="text-sm font-semibold text-foreground">
                    Equipment Maintenance & Duty Cycle
                  </h3>
                  <div className="mt-4 divide-y divide-border/60 text-xs">
                    {[
                      {
                        id: "FL-01",
                        zone: "Receiving Bay",
                        hours: "8.4 hrs",
                        battery: "78%",
                        status: "Active",
                      },
                      {
                        id: "FL-02",
                        zone: "Storage Aisle 3",
                        hours: "9.1 hrs",
                        battery: "84%",
                        status: "Active",
                      },
                      {
                        id: "FL-03",
                        zone: "Loading Zone",
                        hours: "7.8 hrs",
                        battery: "62%",
                        status: "Active",
                      },
                      {
                        id: "FL-04",
                        zone: "Dispatch Dock",
                        hours: "8.9 hrs",
                        battery: "91%",
                        status: "Active",
                      },
                      {
                        id: "FL-05",
                        zone: "High-Bay Aisle",
                        hours: "8.6 hrs",
                        battery: "70%",
                        status: "Active",
                      },
                    ].map((fl) => (
                      <div key={fl.id} className="flex items-center justify-between py-2.5">
                        <div className="flex items-center gap-3">
                          <Forklift className="size-4 text-primary" />
                          <div>
                            <p className="font-semibold text-foreground">{fl.id}</p>
                            <p className="text-[10px] text-muted-foreground">{fl.zone}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-6 font-mono text-[11px]">
                          <span>{fl.hours}</span>
                          <span className="text-success">{fl.battery} Batt</span>
                          <span className="rounded-sm border border-success/30 bg-success/10 px-2 py-0.5 text-[9px] text-success">
                            {fl.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Executive Report Preview Section */}
            <section className="border border-border bg-card/95 shadow-panel">
              <div className="flex items-center justify-between border-b border-border px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold text-foreground">
                    Executive Report Preview
                  </h2>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Structured summary compiled for facility operations review
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePrint}
                    className="h-8 gap-1.5 border-border bg-card text-xs text-foreground hover:bg-surface-hover"
                  >
                    <Printer className="size-3.5" /> Print Preview
                  </Button>
                </div>
              </div>

              <div className="space-y-4 p-5 font-mono text-xs text-foreground">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3 text-[11px] text-muted-foreground">
                  <span>FACILITY: {warehouse.toUpperCase()}</span>
                  <span>DATE: {reportsData.dailySummary.reportDate.toUpperCase()}</span>
                  <span>STATUS: CERTIFIED VISION AUDIT</span>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded border border-border/70 bg-background/50 p-3">
                    <p className="font-sans font-semibold text-primary">Key Metrics Summary</p>
                    <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                      <li>
                        • Total Frames Processed: {reportsData.dailySummary.totalFramesProcessed}
                      </li>
                      <li>• Vision Model Accuracy: {reportsData.dailySummary.meanAccuracy}</li>
                      <li>• Inbound Volume: {reportsData.inventorySummary.inboundTotal} units</li>
                      <li>• Outbound Volume: {reportsData.inventorySummary.outboundTotal} units</li>
                    </ul>
                  </div>

                  <div className="rounded border border-border/70 bg-background/50 p-3">
                    <p className="font-sans font-semibold text-success">Safety & Compliance</p>
                    <ul className="mt-2 space-y-1 text-[11px] text-muted-foreground">
                      <li>
                        • Total Incidents: {reportsData.safetySummary.totalIncidents} (15 resolved)
                      </li>
                      <li>• Critical Triggers: {reportsData.safetySummary.criticalIncidents}</li>
                      <li>• Mean Resolution Time: {reportsData.safetySummary.meanTimeToResolve}</li>
                      <li>• Facility Compliance Grade: 94.6% (Pass)</li>
                    </ul>
                  </div>
                </div>

                <p className="pt-2 text-[10px] text-muted-foreground">
                  * Note: This document is auto-generated by the WarehouseVision AI computer vision
                  edge processing node.
                </p>
              </div>
            </section>

            {/* Footer */}
            <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
              <span>WarehouseVision AI · Reporting & Audit Engine</span>
              <span>Document Version 1.4.0</span>
            </footer>
          </div>
        </div>
      </main>
    </div>
  );
}
