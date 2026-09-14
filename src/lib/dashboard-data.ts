import {
  Boxes,
  ChartNoAxesCombined,
  CircleGauge,
  Forklift,
  LayoutDashboard,
  RadioTower,
  Settings,
  ShieldAlert,
  Users,
  Video,
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
  { label: "Active Forklifts", value: "5", detail: "All operational", icon: Forklift, tone: "primary" },
  { label: "Visible Inventory", value: "127", detail: "98.4% accounted", icon: Boxes, tone: "primary" },
  { label: "Safety Alerts", value: "3", detail: "1 high priority", icon: ShieldAlert, tone: "danger" },
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

export { RadioTower };