import {
  Boxes,
  Camera,
  ChartNoAxesCombined,
  CircleGauge,
  Clock,
  Eye,
  Forklift,
  Gauge,
  LayoutDashboard,
  PackageCheck,
  PackageOpen,
  RadioTower,
  Settings,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Users,
  Video,
  Warehouse,
  type LucideIcon,
} from "lucide-react";

export type NavigationItem = {
  label: string;
  icon: LucideIcon;
};

export const navigationItems: NavigationItem[] = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Live Camera", icon: Video },
  { label: "Inventory", icon: Boxes },
  { label: "Safety", icon: ShieldAlert },
  { label: "Analytics", icon: ChartNoAxesCombined },
  { label: "Reports", icon: CircleGauge },
  { label: "Settings", icon: Settings },
];

export const kpis = [
  { label: "Active Workers", value: "24", detail: "+2 this shift", icon: Users, tone: "success" },
  {
    label: "Active Forklifts",
    value: "5",
    detail: "All operational",
    icon: Forklift,
    tone: "primary",
  },
  {
    label: "Visible Inventory",
    value: "127",
    detail: "98.4% accounted",
    icon: Boxes,
    tone: "primary",
  },
  {
    label: "Safety Alerts",
    value: "3",
    detail: "1 high priority",
    icon: ShieldAlert,
    tone: "danger",
  },
] as const;

export const alerts = [
  {
    title: "Worker–Forklift Proximity",
    description: "Worker #12 near Forklift #3",
    severity: "High",
    time: "2 min ago",
  },
  {
    title: "Restricted Zone Entry",
    description: "Worker #07 entered Zone A",
    severity: "Medium",
    time: "8 min ago",
  },
  {
    title: "PPE Compliance Check",
    description: "Worker #18 missing safety vest",
    severity: "Medium",
    time: "14 min ago",
  },
] as const;

export const zoneOccupancy = [
  { label: "Receiving", value: 76, count: "19 / 25" },
  { label: "Main Storage", value: 58, count: "29 / 50" },
  { label: "Packing", value: 88, count: "22 / 25" },
  { label: "Dispatch", value: 44, count: "11 / 25" },
] as const;

export const activityData = [
  { time: "06:00", workers: 8, forklifts: 1 },
  { time: "08:00", workers: 17, forklifts: 3 },
  { time: "10:00", workers: 21, forklifts: 4 },
  { time: "12:00", workers: 19, forklifts: 5 },
  { time: "14:00", workers: 24, forklifts: 5 },
  { time: "16:00", workers: 22, forklifts: 4 },
  { time: "18:00", workers: 14, forklifts: 2 },
];

export const inventoryData = [
  { time: "06:00", inbound: 12, outbound: 8 },
  { time: "08:00", inbound: 28, outbound: 14 },
  { time: "10:00", inbound: 19, outbound: 25 },
  { time: "12:00", inbound: 34, outbound: 21 },
  { time: "14:00", inbound: 26, outbound: 31 },
  { time: "16:00", inbound: 42, outbound: 29 },
  { time: "18:00", inbound: 18, outbound: 37 },
];

export const warehouses = ["North Distribution Center", "East Fulfillment Hub", "South Cross-Dock"];

// --- Centralized Camera Configuration ---
export type CameraDevice = {
  id: string;
  name: string;
  location: string;
  zone: string;
  status: "Active" | "Standby" | "Offline";
  fps: number;
  resolution: string;
  rtspUrl: string;
  trackedObjects: number;
};

export const cameraDevices: CameraDevice[] = [
  {
    id: "CAM-01",
    name: "Main Overhead Wide",
    location: "Main Warehouse Floor",
    zone: "Main Storage",
    status: "Active",
    fps: 24,
    resolution: "1920x1080",
    rtspUrl: "rtsp://edge-node-01.local:8554/cam01_main",
    trackedObjects: 14,
  },
  {
    id: "CAM-02",
    name: "Dock North Gate",
    location: "Receiving Bay A",
    zone: "Receiving",
    status: "Active",
    fps: 24,
    resolution: "1920x1080",
    rtspUrl: "rtsp://edge-node-01.local:8554/cam02_recv",
    trackedObjects: 9,
  },
  {
    id: "CAM-03",
    name: "Dispatch Conveyor",
    location: "Loading Dock 4",
    zone: "Dispatch",
    status: "Active",
    fps: 24,
    resolution: "1920x1080",
    rtspUrl: "rtsp://edge-node-02.local:8554/cam03_disp",
    trackedObjects: 6,
  },
  {
    id: "CAM-04",
    name: "Packing Line 2",
    location: "Secondary Packaging",
    zone: "Packing",
    status: "Standby",
    fps: 20,
    resolution: "1920x1080",
    rtspUrl: "rtsp://edge-node-02.local:8554/cam04_pack",
    trackedObjects: 3,
  },
];

// --- Centralized Inventory Mock Data ---
export type InventoryEvent = {
  id: string;
  objectType: "Box" | "Pallet";
  direction: "Inbound" | "Outbound";
  camera: string;
  timestamp: string;
  date: string;
  confidence: number;
  status: "Verified" | "Logged" | "Flagged";
  zone: string;
  dimensions?: string;
};

// 96 boxes + 31 pallets = 127 visible items (matching Dashboard KPI)
export const inventoryKPIs = [
  {
    label: "Total Detected Boxes",
    value: "96",
    detail: "AI bounding count",
    icon: Boxes,
    tone: "primary",
  },
  {
    label: "Total Detected Pallets",
    value: "31",
    detail: "Euro & standard pallets",
    icon: PackageCheck,
    tone: "success",
  },
  {
    label: "Inbound Today",
    value: "179",
    detail: "Avg 25.5 units/hr",
    icon: TrendingUp,
    tone: "primary",
  },
  {
    label: "Outbound Today",
    value: "165",
    detail: "Avg 23.5 units/hr",
    icon: TrendingDown,
    tone: "success",
  },
  {
    label: "Estimated Inventory",
    value: "1,480",
    detail: "127 visible in camera feeds",
    icon: Warehouse,
    tone: "primary",
  },
];

export const inventoryEvents: InventoryEvent[] = [
  {
    id: "BX-1029",
    objectType: "Box",
    direction: "Inbound",
    camera: "CAM-02",
    timestamp: "14:31:05",
    date: "2026-09-21",
    confidence: 96,
    status: "Verified",
    zone: "Receiving",
    dimensions: "40x30x25 cm",
  },
  {
    id: "PL-0402",
    objectType: "Pallet",
    direction: "Inbound",
    camera: "CAM-02",
    timestamp: "14:28:44",
    date: "2026-09-21",
    confidence: 94,
    status: "Verified",
    zone: "Receiving",
    dimensions: "1200x800 mm",
  },
  {
    id: "BX-1033",
    objectType: "Box",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "14:24:12",
    date: "2026-09-21",
    confidence: 91,
    status: "Verified",
    zone: "Dispatch",
    dimensions: "60x40x40 cm",
  },
  {
    id: "BX-1035",
    objectType: "Box",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "14:19:55",
    date: "2026-09-21",
    confidence: 88,
    status: "Logged",
    zone: "Dispatch",
    dimensions: "30x20x20 cm",
  },
  {
    id: "PL-0408",
    objectType: "Pallet",
    direction: "Inbound",
    camera: "CAM-01",
    timestamp: "14:15:30",
    date: "2026-09-21",
    confidence: 95,
    status: "Verified",
    zone: "Main Storage",
    dimensions: "1200x1000 mm",
  },
  {
    id: "BX-1044",
    objectType: "Box",
    direction: "Inbound",
    camera: "CAM-02",
    timestamp: "14:09:18",
    date: "2026-09-21",
    confidence: 84,
    status: "Flagged",
    zone: "Receiving",
    dimensions: "Uncertain",
  },
  {
    id: "BX-1051",
    objectType: "Box",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "14:02:40",
    date: "2026-09-21",
    confidence: 93,
    status: "Verified",
    zone: "Dispatch",
    dimensions: "50x35x30 cm",
  },
  {
    id: "PL-0205",
    objectType: "Pallet",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "13:54:11",
    date: "2026-09-21",
    confidence: 92,
    status: "Verified",
    zone: "Dispatch",
    dimensions: "1200x800 mm",
  },
  {
    id: "BX-1060",
    objectType: "Box",
    direction: "Inbound",
    camera: "CAM-01",
    timestamp: "13:48:02",
    date: "2026-09-21",
    confidence: 97,
    status: "Verified",
    zone: "Main Storage",
    dimensions: "45x35x25 cm",
  },
  {
    id: "BX-1072",
    objectType: "Box",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "13:39:27",
    date: "2026-09-21",
    confidence: 89,
    status: "Logged",
    zone: "Dispatch",
    dimensions: "40x30x20 cm",
  },
  {
    id: "PL-0914",
    objectType: "Pallet",
    direction: "Inbound",
    camera: "CAM-02",
    timestamp: "13:25:50",
    date: "2026-09-21",
    confidence: 93,
    status: "Verified",
    zone: "Receiving",
    dimensions: "1200x800 mm",
  },
  {
    id: "BX-1088",
    objectType: "Box",
    direction: "Inbound",
    camera: "CAM-02",
    timestamp: "13:14:19",
    date: "2026-09-21",
    confidence: 95,
    status: "Verified",
    zone: "Receiving",
    dimensions: "55x40x35 cm",
  },
  {
    id: "BX-1092",
    objectType: "Box",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "12:59:04",
    date: "2026-09-21",
    confidence: 90,
    status: "Verified",
    zone: "Dispatch",
    dimensions: "35x25x20 cm",
  },
  {
    id: "PL-0331",
    objectType: "Pallet",
    direction: "Outbound",
    camera: "CAM-03",
    timestamp: "12:47:33",
    date: "2026-09-21",
    confidence: 91,
    status: "Verified",
    zone: "Dispatch",
    dimensions: "1200x1000 mm",
  },
  {
    id: "BX-1104",
    objectType: "Box",
    direction: "Inbound",
    camera: "CAM-01",
    timestamp: "12:35:12",
    date: "2026-09-21",
    confidence: 86,
    status: "Logged",
    zone: "Main Storage",
    dimensions: "40x40x30 cm",
  },
  {
    id: "BX-1110",
    objectType: "Box",
    direction: "Inbound",
    camera: "CAM-02",
    timestamp: "12:18:45",
    date: "2026-09-21",
    confidence: 94,
    status: "Verified",
    zone: "Receiving",
    dimensions: "50x30x25 cm",
  },
];

// --- Centralized Analytics Mock Data ---
export const analyticsKPIs = [
  {
    label: "Worker Utilization",
    value: "87.5%",
    detail: "+3.2% vs last shift",
    icon: Users,
    tone: "success",
  },
  {
    label: "Forklift Utilization",
    value: "83.3%",
    detail: "5 of 5 active units",
    icon: Forklift,
    tone: "primary",
  },
  {
    label: "Avg Dwell Time",
    value: "14.2 min",
    detail: "-1.8 min transit speed",
    icon: Clock,
    tone: "primary",
  },
  {
    label: "Zone Peak Occupancy",
    value: "88%",
    detail: "Packing zone high load",
    icon: Warehouse,
    tone: "danger",
  },
];

export const zoneDetailedMetrics = [
  {
    name: "Receiving",
    occupancy: 76,
    capacity: "19 / 25",
    avgDwellMinutes: 18.5,
    throughputUnits: 179,
    activeWorkers: 6,
    activeForklifts: 2,
  },
  {
    name: "Main Storage",
    occupancy: 58,
    capacity: "29 / 50",
    avgDwellMinutes: 34.0,
    throughputUnits: 245,
    activeWorkers: 7,
    activeForklifts: 2,
  },
  {
    name: "Packing",
    occupancy: 88,
    capacity: "22 / 25",
    avgDwellMinutes: 9.8,
    throughputUnits: 194,
    activeWorkers: 8,
    activeForklifts: 0,
  },
  {
    name: "Dispatch",
    occupancy: 44,
    capacity: "11 / 25",
    avgDwellMinutes: 12.4,
    throughputUnits: 165,
    activeWorkers: 3,
    activeForklifts: 1,
  },
];

export const safetyIncidentTrends = [
  { day: "Mon", proximity: 3, restricted: 1, ppe: 2, total: 6 },
  { day: "Tue", proximity: 2, restricted: 2, ppe: 1, total: 5 },
  { day: "Wed", proximity: 4, restricted: 1, ppe: 1, total: 6 },
  { day: "Thu", proximity: 1, restricted: 3, ppe: 2, total: 6 },
  { day: "Fri", proximity: 5, restricted: 2, ppe: 3, total: 10 },
  { day: "Sat", proximity: 2, restricted: 1, ppe: 1, total: 4 },
  { day: "Sun", proximity: 3, restricted: 2, ppe: 2, total: 7 },
];

export const workerForkliftTrends = [
  { time: "06:00", workers: 8, forklifts: 1, workerUtilization: 65, forkliftUtilization: 50 },
  { time: "08:00", workers: 17, forklifts: 3, workerUtilization: 82, forkliftUtilization: 75 },
  { time: "10:00", workers: 21, forklifts: 4, workerUtilization: 91, forkliftUtilization: 85 },
  { time: "12:00", workers: 19, forklifts: 5, workerUtilization: 86, forkliftUtilization: 95 },
  { time: "14:00", workers: 24, forklifts: 5, workerUtilization: 94, forkliftUtilization: 92 },
  { time: "16:00", workers: 22, forklifts: 4, workerUtilization: 89, forkliftUtilization: 88 },
  { time: "18:00", workers: 14, forklifts: 2, workerUtilization: 74, forkliftUtilization: 60 },
];

export const dwellTimeByZone = [
  { zone: "Receiving", time: 18.5, target: 15.0 },
  { zone: "Storage Aisle", time: 24.0, target: 25.0 },
  { zone: "Packing Line", time: 9.8, target: 10.0 },
  { zone: "Staging Bay", time: 14.2, target: 12.0 },
  { zone: "Dispatch Dock", time: 12.4, target: 15.0 },
];

// --- Centralized Reports Mock Data ---
export const reportsData = {
  dailySummary: {
    reportDate: "September 21, 2026",
    shift: "Day Shift (06:00 – 18:00)",
    facility: "North Distribution Center",
    totalFramesProcessed: "1,244,160",
    meanAccuracy: "96.8%",
    uptime: "99.94%",
    activeCameras: "3 / 4",
    totalDetections: "38,419",
  },
  safetySummary: {
    totalIncidents: 18,
    criticalIncidents: 3,
    meanTimeToResolve: "4.2 min",
    complianceScore: "94.6%",
    topIncidentZone: "Loading Zone (39%)",
    ppeComplianceRate: "97.1%",
  },
  inventorySummary: {
    totalDetectedUnits: 344,
    boxesDetected: 96,
    palletsDetected: 31,
    inboundTotal: 179,
    outboundTotal: 165,
    netFlow: "+14 units",
    peakMovementHour: "16:00 (71 units)",
  },
  equipmentSummary: {
    activeForklifts: 5,
    totalFleetOperatingHours: "42.8 hrs",
    idleVsMovingRatio: "22% / 78%",
    proximityEventsTotal: 7,
    safestOperator: "FL-02 (Zero events)",
  },
};

export { RadioTower };
