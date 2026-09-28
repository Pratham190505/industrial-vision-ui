import { useState } from "react";
import {
  AlertTriangle,
  Bell,
  Camera,
  CheckCircle2,
  Cpu,
  Edit2,
  Eye,
  Forklift,
  Layers,
  Menu,
  Monitor,
  Plus,
  Radio,
  Save,
  Shield,
  ShieldAlert,
  Sliders,
  SlidersHorizontal,
  Trash2,
  Warehouse,
  Wrench,
  X,
} from "lucide-react";
import { toast } from "sonner";

import warehouseAsset from "@/assets/warehouse-command-center.jpg.asset.json";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WarehouseSidebar } from "@/components/warehouse-sidebar";
import { cameraDevices, type CameraDevice } from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

export function SettingsPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("cameras");

  // Camera settings state
  const [cameras, setCameras] = useState<CameraDevice[]>(cameraDevices);
  const [editingCamera, setEditingCamera] = useState<CameraDevice | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newCamera, setNewCamera] = useState({
    id: `CAM-0${cameras.length + 1}`,
    name: "",
    location: "",
    zone: "Main Storage",
    status: "Active" as const,
    fps: 24,
    resolution: "1920x1080",
    rtspUrl: "",
    trackedObjects: 0,
  });

  // Safety settings state
  const [proximityThreshold, setProximityThreshold] = useState<number>(2.0);
  const [forkliftSpeedLimit, setForkliftSpeedLimit] = useState<number>(8);
  const [minConfidence, setMinConfidence] = useState<number>(85);
  const [escalationTimeout, setEscalationTimeout] = useState<string>("5");
  const [restrictedZoneActive, setRestrictedZoneActive] = useState(true);

  // Notification settings state
  const [notifyProximity, setNotifyProximity] = useState(true);
  const [notifyRestricted, setNotifyRestricted] = useState(true);
  const [notifyPpe, setNotifyPpe] = useState(true);
  const [notifyInventory, setNotifyInventory] = useState(false);
  const [soundAlarms, setSoundAlarms] = useState(true);
  const [emailDigest, setEmailDigest] = useState(true);

  // System & Model state
  const [selectedModel, setSelectedModel] = useState("yolov8x-warehouse");
  const [inferenceDevice, setInferenceDevice] = useState("cuda:0");
  const [showBoundingBoxes, setShowBoundingBoxes] = useState(true);
  const [showConfidenceScore, setShowConfidenceScore] = useState(true);
  const [enableScanlines, setEnableScanlines] = useState(true);

  // Handlers
  const handleSaveSafetySettings = () => {
    toast.success("Safety configuration saved to session state", {
      description: `Proximity limit set to ${proximityThreshold}m, Speed limit: ${forkliftSpeedLimit} km/h`,
    });
  };

  const handleSaveNotifications = () => {
    toast.success("Notification preferences updated", {
      description: "Alert triggers active in current monitoring session",
    });
  };

  const handleSaveSystemSettings = () => {
    toast.success("System & inference preferences updated", {
      description: `Model: ${selectedModel} on ${inferenceDevice}`,
    });
  };

  const handleSaveEditCamera = () => {
    if (!editingCamera) return;
    setCameras((prev) => prev.map((c) => (c.id === editingCamera.id ? editingCamera : c)));
    setEditingCamera(null);
    toast.success(`Camera ${editingCamera.id} updated`);
  };

  const handleAddCamera = () => {
    if (!newCamera.name.trim() || !newCamera.rtspUrl.trim()) {
      toast.error("Please fill in camera name and RTSP stream URL");
      return;
    }
    setCameras((prev) => [...prev, newCamera]);
    setIsAddModalOpen(false);
    toast.success(`Camera ${newCamera.id} added successfully`);
    setNewCamera({
      id: `CAM-0${cameras.length + 2}`,
      name: "",
      location: "",
      zone: "Main Storage",
      status: "Active",
      fps: 24,
      resolution: "1920x1080",
      rtspUrl: "",
      trackedObjects: 0,
    });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sidebar Navigation */}
      <WarehouseSidebar active="Settings" />

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-sidebar-border">
            <WarehouseSidebar active="Settings" mobile onNavigate={() => setMobileOpen(false)} />
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
                <h1 className="truncate text-lg font-semibold sm:text-xl">
                  System Settings & Configuration
                </h1>
                <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                  Camera streams, AI vision sensitivity, safety triggers & notification preferences
                </p>
              </div>

              {/* Status Badge */}
              <div className="flex items-center gap-2 border border-primary/30 bg-primary/10 px-3 py-2">
                <span className="size-2 rounded-full bg-primary" />
                <span className="text-[10px] font-semibold text-primary">
                  Session Config Active
                </span>
              </div>
            </div>
          </header>

          <div className="mx-auto max-w-[1600px] space-y-5 p-4 sm:p-6 xl:p-8">
            {/* Settings Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-5">
              <TabsList className="grid h-10 w-full grid-cols-2 border border-border bg-card/90 p-1 md:grid-cols-4">
                <TabsTrigger
                  value="cameras"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Camera className="size-3.5" />
                  Camera Configuration
                </TabsTrigger>
                <TabsTrigger
                  value="safety"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <ShieldAlert className="size-3.5" />
                  Safety Configuration
                </TabsTrigger>
                <TabsTrigger
                  value="notifications"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Bell className="size-3.5" />
                  Notification Preferences
                </TabsTrigger>
                <TabsTrigger
                  value="system"
                  className="gap-2 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Cpu className="size-3.5" />
                  System & Model
                </TabsTrigger>
              </TabsList>

              {/* SECTION 1: Camera Configuration */}
              <TabsContent value="cameras" className="space-y-5 outline-none">
                <div className="flex flex-wrap items-center justify-between gap-3 border border-border bg-card/95 p-5 shadow-panel">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">
                      Connected Vision Sensors & Cameras
                    </h2>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      Manage edge camera RTSP streams, resolution, target FPS, and zone assignments
                    </p>
                  </div>
                  <Button
                    onClick={() => setIsAddModalOpen(true)}
                    className="h-8 gap-1.5 border border-primary/40 bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                  >
                    <Plus className="size-3.5" /> Add Camera Stream
                  </Button>
                </div>

                {/* Camera Devices Grid */}
                <div className="grid gap-4 md:grid-cols-2">
                  {cameras.map((cam) => {
                    const isActive = cam.status === "Active";
                    const isStandby = cam.status === "Standby";
                    return (
                      <article
                        key={cam.id}
                        className="border border-border bg-card/95 p-4 shadow-panel transition-colors hover:border-primary/50"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="grid size-9 place-items-center rounded-md border border-primary/20 bg-primary/10 text-primary">
                              <Camera className="size-4.5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-xs font-bold text-primary">
                                  {cam.id}
                                </span>
                                <h3 className="font-semibold text-foreground">{cam.name}</h3>
                              </div>
                              <p className="text-[10px] text-muted-foreground">{cam.location}</p>
                            </div>
                          </div>
                          <span
                            className={cn(
                              "rounded-sm border px-2 py-0.5 font-mono text-[9px] font-bold uppercase",
                              isActive
                                ? "border-success/30 bg-success/10 text-success"
                                : isStandby
                                  ? "border-primary/30 bg-primary/10 text-primary"
                                  : "border-muted bg-muted/20 text-muted-foreground",
                            )}
                          >
                            {cam.status}
                          </span>
                        </div>

                        <div className="mt-4 grid grid-cols-2 gap-2.5 rounded bg-background/50 p-2.5 font-mono text-[11px]">
                          <div>
                            <span className="text-[9px] uppercase text-muted-foreground">Zone</span>
                            <p className="text-foreground">{cam.zone}</p>
                          </div>
                          <div>
                            <span className="text-[9px] uppercase text-muted-foreground">
                              Stream Rate
                            </span>
                            <p className="text-foreground">
                              {cam.resolution} @ {cam.fps} FPS
                            </p>
                          </div>
                          <div className="col-span-2 truncate">
                            <span className="text-[9px] uppercase text-muted-foreground">
                              RTSP Endpoint
                            </span>
                            <p className="truncate text-muted-foreground">{cam.rtspUrl}</p>
                          </div>
                        </div>

                        <div className="mt-3.5 flex items-center justify-between border-t border-border/60 pt-2.5 text-xs">
                          <span className="text-[11px] text-muted-foreground">
                            {cam.trackedObjects} objects currently in view
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingCamera(cam)}
                            className="h-7 gap-1 text-[11px] text-primary hover:bg-primary/10 hover:text-primary"
                          >
                            <Edit2 className="size-3" /> Edit Config
                          </Button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </TabsContent>

              {/* SECTION 2: Safety Configuration */}
              <TabsContent value="safety" className="space-y-5 outline-none">
                <section className="border border-border bg-card/95 p-5 shadow-panel">
                  <div className="flex items-center justify-between border-b border-border pb-4">
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">
                        Worker–Forklift Proximity & Restricted Zone Safety
                      </h2>
                      <p className="mt-0.5 text-[11px] text-muted-foreground">
                        Configure minimum clearance thresholds, zone alarms, and AI detection
                        confidence limits
                      </p>
                    </div>
                    <Button
                      onClick={handleSaveSafetySettings}
                      className="h-8 gap-1.5 border border-primary/40 bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                    >
                      <Save className="size-3.5" /> Save Safety Parameters
                    </Button>
                  </div>

                  <div className="mt-6 space-y-6">
                    {/* Proximity Threshold Slider */}
                    <div className="rounded-md border border-border/80 bg-background/50 p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <Label className="text-xs font-semibold text-foreground">
                            Worker–Forklift Proximity Warning Threshold
                          </Label>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            Triggers an automatic audio and visual alarm when a worker and forklift
                            breach separation
                          </p>
                        </div>
                        <span className="font-mono text-base font-bold text-danger">
                          {proximityThreshold.toFixed(1)} meters
                        </span>
                      </div>
                      <div className="mt-4">
                        <Slider
                          value={[proximityThreshold]}
                          onValueChange={(val) => setProximityThreshold(val[0] ?? 2.0)}
                          min={1.0}
                          max={5.0}
                          step={0.1}
                          className="w-full"
                        />
                        <div className="mt-1.5 flex justify-between font-mono text-[9px] text-muted-foreground">
                          <span>1.0m (Tight Aisle)</span>
                          <span>2.5m (Recommended Standard)</span>
                          <span>5.0m (High-Speed Zone)</span>
                        </div>
                      </div>
                    </div>

                    {/* Forklift Speed Limit */}
                    <div className="rounded-md border border-border/80 bg-background/50 p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <Label className="text-xs font-semibold text-foreground">
                            Forklift Optical Speed Limit Trigger
                          </Label>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            AI estimated travel velocity threshold inside pedestrian shared lanes
                          </p>
                        </div>
                        <span className="font-mono text-base font-bold text-primary">
                          {forkliftSpeedLimit} km/h
                        </span>
                      </div>
                      <div className="mt-4">
                        <Slider
                          value={[forkliftSpeedLimit]}
                          onValueChange={(val) => setForkliftSpeedLimit(val[0] ?? 8)}
                          min={4}
                          max={16}
                          step={1}
                          className="w-full"
                        />
                        <div className="mt-1.5 flex justify-between font-mono text-[9px] text-muted-foreground">
                          <span>4 km/h (Creep)</span>
                          <span>8 km/h (Warehouse Default)</span>
                          <span>16 km/h (Max Safe)</span>
                        </div>
                      </div>
                    </div>

                    {/* AI Confidence Cutoff */}
                    <div className="rounded-md border border-border/80 bg-background/50 p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <Label className="text-xs font-semibold text-foreground">
                            Minimum AI Detection Confidence Threshold
                          </Label>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            Detections below this score are filtered to prevent false positive
                            safety alerts
                          </p>
                        </div>
                        <span className="font-mono text-base font-bold text-success">
                          {minConfidence}%
                        </span>
                      </div>
                      <div className="mt-4">
                        <Slider
                          value={[minConfidence]}
                          onValueChange={(val) => setMinConfidence(val[0] ?? 85)}
                          min={70}
                          max={98}
                          step={1}
                          className="w-full"
                        />
                        <div className="mt-1.5 flex justify-between font-mono text-[9px] text-muted-foreground">
                          <span>70% (Permissive)</span>
                          <span>85% (Optimal Balance)</span>
                          <span>98% (High Precision)</span>
                        </div>
                      </div>
                    </div>

                    {/* Restricted Zone & Escalation */}
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="flex items-center justify-between rounded-md border border-border/80 bg-background/50 p-4">
                        <div>
                          <Label className="text-xs font-semibold text-foreground">
                            Restricted Zone Enforcement
                          </Label>
                          <p className="mt-0.5 text-[10px] text-muted-foreground">
                            Alarm on unauthorized personnel entering Zone A & B
                          </p>
                        </div>
                        <Switch
                          checked={restrictedZoneActive}
                          onCheckedChange={setRestrictedZoneActive}
                        />
                      </div>

                      <div className="rounded-md border border-border/80 bg-background/50 p-4">
                        <Label className="text-xs font-semibold text-foreground">
                          Alert Escalation Timeout
                        </Label>
                        <p className="mt-0.5 text-[10px] text-muted-foreground">
                          Minutes before unresolved alerts notify operations supervisor
                        </p>
                        <Select value={escalationTimeout} onValueChange={setEscalationTimeout}>
                          <SelectTrigger className="mt-2 h-8 border-border bg-background text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="2">2 Minutes (Urgent)</SelectItem>
                            <SelectItem value="5">5 Minutes (Standard)</SelectItem>
                            <SelectItem value="10">10 Minutes (Extended)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                </section>
              </TabsContent>

              {/* SECTION 3: Notification Preferences */}
              <TabsContent value="notifications" className="space-y-5 outline-none">
                <section className="border border-border bg-card/95 p-5 shadow-panel">
                  <div className="flex items-center justify-between border-b border-border pb-4">
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">
                        Operational & Safety Notification Channels
                      </h2>
                      <p className="mt-0.5 text-[11px] text-muted-foreground">
                        Choose which events send push triggers, audio beeps, and supervisor digests
                      </p>
                    </div>
                    <Button
                      onClick={handleSaveNotifications}
                      className="h-8 gap-1.5 border border-primary/40 bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                    >
                      <Save className="size-3.5" /> Save Notification Rules
                    </Button>
                  </div>

                  <div className="mt-6 space-y-4">
                    <div className="flex items-center justify-between rounded border border-border/80 bg-background/50 p-4">
                      <div>
                        <p className="text-xs font-semibold text-foreground">
                          Worker–Forklift Proximity Alerts
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          Immediate visual banner and high-priority siren badge
                        </p>
                      </div>
                      <Switch checked={notifyProximity} onCheckedChange={setNotifyProximity} />
                    </div>

                    <div className="flex items-center justify-between rounded border border-border/80 bg-background/50 p-4">
                      <div>
                        <p className="text-xs font-semibold text-foreground">
                          Restricted Zone Intrusion Alerts
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          Notifies security console upon unauthorized zone entry
                        </p>
                      </div>
                      <Switch checked={notifyRestricted} onCheckedChange={setNotifyRestricted} />
                    </div>

                    <div className="flex items-center justify-between rounded border border-border/80 bg-background/50 p-4">
                      <div>
                        <p className="text-xs font-semibold text-foreground">
                          PPE Compliance Notifications
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          Log warning when hard hat or safety vest is not detected
                        </p>
                      </div>
                      <Switch checked={notifyPpe} onCheckedChange={setNotifyPpe} />
                    </div>

                    <div className="flex items-center justify-between rounded border border-border/80 bg-background/50 p-4">
                      <div>
                        <p className="text-xs font-semibold text-foreground">
                          Inventory Flow & Low Stock Alerts
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          Trigger updates when tracked inventory counts drop below threshold
                        </p>
                      </div>
                      <Switch checked={notifyInventory} onCheckedChange={setNotifyInventory} />
                    </div>

                    <div className="flex items-center justify-between rounded border border-border/80 bg-background/50 p-4">
                      <div>
                        <p className="text-xs font-semibold text-foreground">
                          Console Audio Beeps & Chimes
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          Play acoustic signals for critical safety events
                        </p>
                      </div>
                      <Switch checked={soundAlarms} onCheckedChange={setSoundAlarms} />
                    </div>

                    <div className="flex items-center justify-between rounded border border-border/80 bg-background/50 p-4">
                      <div>
                        <p className="text-xs font-semibold text-foreground">
                          Daily End-of-Shift Email Digest
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          Automatically dispatch shift executive summary report at 18:00
                        </p>
                      </div>
                      <Switch checked={emailDigest} onCheckedChange={setEmailDigest} />
                    </div>
                  </div>
                </section>
              </TabsContent>

              {/* SECTION 4: System & Model Preferences */}
              <TabsContent value="system" className="space-y-5 outline-none">
                <section className="border border-border bg-card/95 p-5 shadow-panel">
                  <div className="flex items-center justify-between border-b border-border pb-4">
                    <div>
                      <h2 className="text-sm font-semibold text-foreground">
                        Computer Vision Model & UI Preferences
                      </h2>
                      <p className="mt-0.5 text-[11px] text-muted-foreground">
                        Select inference model weights, hardware accelerator & HUD overlay options
                      </p>
                    </div>
                    <Button
                      onClick={handleSaveSystemSettings}
                      className="h-8 gap-1.5 border border-primary/40 bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                    >
                      <Save className="size-3.5" /> Save System Preferences
                    </Button>
                  </div>

                  <div className="mt-6 space-y-5">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="rounded border border-border/80 bg-background/50 p-4">
                        <Label className="text-xs font-semibold text-foreground">
                          Computer Vision Model Pipeline
                        </Label>
                        <p className="mt-0.5 text-[10px] text-muted-foreground">
                          Neural network architecture optimized for multi-object tracking
                        </p>
                        <Select value={selectedModel} onValueChange={setSelectedModel}>
                          <SelectTrigger className="mt-2 h-9 border-border bg-background text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="yolov8x-warehouse">
                              YOLOv8x Warehouse Custom (High Accuracy)
                            </SelectItem>
                            <SelectItem value="yolov11-industrial">
                              YOLOv11 Industrial (Low Latency 14ms)
                            </SelectItem>
                            <SelectItem value="rt-detr-large">
                              RT-DETR Large (Transformer Tracking)
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="rounded border border-border/80 bg-background/50 p-4">
                        <Label className="text-xs font-semibold text-foreground">
                          Edge Inference Hardware
                        </Label>
                        <p className="mt-0.5 text-[10px] text-muted-foreground">
                          Target accelerator device on local compute node
                        </p>
                        <Select value={inferenceDevice} onValueChange={setInferenceDevice}>
                          <SelectTrigger className="mt-2 h-9 border-border bg-background text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="cuda:0">
                              CUDA:0 · NVIDIA RTX 4090 (24GB VRAM)
                            </SelectItem>
                            <SelectItem value="tensorrt">
                              TensorRT Engine · INT8 Quantized
                            </SelectItem>
                            <SelectItem value="cpu">CPU Fallback · OpenVINO</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="rounded border border-border/80 bg-background/50 p-4">
                      <h3 className="text-xs font-semibold text-foreground">
                        Camera Feed Overlay (HUD) Preferences
                      </h3>
                      <div className="mt-3 divide-y divide-border/60">
                        <div className="flex items-center justify-between py-2.5">
                          <div>
                            <p className="text-xs font-medium text-foreground">
                              Show Bounding Box Labels & Tracking IDs
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              Overlays e.g. "Worker #12", "Forklift #3"
                            </p>
                          </div>
                          <Switch
                            checked={showBoundingBoxes}
                            onCheckedChange={setShowBoundingBoxes}
                          />
                        </div>

                        <div className="flex items-center justify-between py-2.5">
                          <div>
                            <p className="text-xs font-medium text-foreground">
                              Display Real-time Confidence Percentage
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              Shows detection score e.g. "94%" on top label
                            </p>
                          </div>
                          <Switch
                            checked={showConfidenceScore}
                            onCheckedChange={setShowConfidenceScore}
                          />
                        </div>

                        <div className="flex items-center justify-between py-2.5">
                          <div>
                            <p className="text-xs font-medium text-foreground">
                              CRT Scanline Effect on Camera Streams
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              Industrial CCTV monitor aesthetic overlay
                            </p>
                          </div>
                          <Switch checked={enableScanlines} onCheckedChange={setEnableScanlines} />
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </TabsContent>
            </Tabs>

            {/* Footer */}
            <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 py-2 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
              <span>WarehouseVision AI · System Configuration Console</span>
              <span>Node: edge-srv-01 · Local mock session</span>
            </footer>
          </div>
        </div>
      </main>

      {/* Edit Camera Modal */}
      <Dialog
        open={Boolean(editingCamera)}
        onOpenChange={(open) => {
          if (!open) setEditingCamera(null);
        }}
      >
        <DialogContent className="border-border bg-popover sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base text-foreground">
              <Camera className="size-4 text-primary" />
              Edit Stream: {editingCamera?.id}
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Update stream connection parameters and zone mapping
            </DialogDescription>
          </DialogHeader>

          {editingCamera && (
            <div className="space-y-3 pt-2 text-xs">
              <div>
                <Label className="text-xs text-foreground">Camera Label / Name</Label>
                <Input
                  value={editingCamera.name}
                  onChange={(e) => setEditingCamera({ ...editingCamera, name: e.target.value })}
                  className="mt-1 h-8 border-border bg-background"
                />
              </div>

              <div>
                <Label className="text-xs text-foreground">Location Description</Label>
                <Input
                  value={editingCamera.location}
                  onChange={(e) => setEditingCamera({ ...editingCamera, location: e.target.value })}
                  className="mt-1 h-8 border-border bg-background"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs text-foreground">Assigned Zone</Label>
                  <Select
                    value={editingCamera.zone}
                    onValueChange={(val) => setEditingCamera({ ...editingCamera, zone: val })}
                  >
                    <SelectTrigger className="mt-1 h-8 border-border bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Main Storage">Main Storage</SelectItem>
                      <SelectItem value="Receiving">Receiving Bay</SelectItem>
                      <SelectItem value="Packing">Packing Line</SelectItem>
                      <SelectItem value="Dispatch">Dispatch Dock</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-xs text-foreground">Stream Status</Label>
                  <Select
                    value={editingCamera.status}
                    onValueChange={(val: "Active" | "Standby" | "Offline") =>
                      setEditingCamera({ ...editingCamera, status: val })
                    }
                  >
                    <SelectTrigger className="mt-1 h-8 border-border bg-background">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Active">Active</SelectItem>
                      <SelectItem value="Standby">Standby</SelectItem>
                      <SelectItem value="Offline">Offline</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label className="text-xs text-foreground">RTSP Stream URL</Label>
                <Input
                  value={editingCamera.rtspUrl}
                  onChange={(e) => setEditingCamera({ ...editingCamera, rtspUrl: e.target.value })}
                  className="mt-1 h-8 font-mono border-border bg-background"
                />
              </div>
            </div>
          )}

          <DialogFooter className="mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditingCamera(null)}
              className="h-8 border-border text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSaveEditCamera}
              className="h-8 bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Camera Modal */}
      <Dialog open={isAddModalOpen} onOpenChange={setIsAddModalOpen}>
        <DialogContent className="border-border bg-popover sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base text-foreground">
              <Plus className="size-4 text-primary" />
              Add New Camera Stream
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Register a new RTSP camera stream on the edge vision node
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 pt-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs text-foreground">Camera ID</Label>
                <Input
                  value={newCamera.id}
                  disabled
                  className="mt-1 h-8 font-mono border-border bg-background/50 text-muted-foreground"
                />
              </div>
              <div>
                <Label className="text-xs text-foreground">Camera Name</Label>
                <Input
                  placeholder="e.g. Aisle 5 North"
                  value={newCamera.name}
                  onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                  className="mt-1 h-8 border-border bg-background"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs text-foreground">Location Description</Label>
              <Input
                placeholder="e.g. High-bay pallet rack 08"
                value={newCamera.location}
                onChange={(e) => setNewCamera({ ...newCamera, location: e.target.value })}
                className="mt-1 h-8 border-border bg-background"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs text-foreground">Assigned Zone</Label>
                <Select
                  value={newCamera.zone}
                  onValueChange={(val) => setNewCamera({ ...newCamera, zone: val })}
                >
                  <SelectTrigger className="mt-1 h-8 border-border bg-background">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Main Storage">Main Storage</SelectItem>
                    <SelectItem value="Receiving">Receiving Bay</SelectItem>
                    <SelectItem value="Packing">Packing Line</SelectItem>
                    <SelectItem value="Dispatch">Dispatch Dock</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs text-foreground">Target FPS</Label>
                <Select
                  value={String(newCamera.fps)}
                  onValueChange={(val) => setNewCamera({ ...newCamera, fps: Number(val) })}
                >
                  <SelectTrigger className="mt-1 h-8 border-border bg-background">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 FPS</SelectItem>
                    <SelectItem value="20">20 FPS</SelectItem>
                    <SelectItem value="24">24 FPS (Optimal)</SelectItem>
                    <SelectItem value="30">30 FPS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs text-foreground">RTSP Stream URL</Label>
              <Input
                placeholder="rtsp://edge-node-01.local:8554/cam05"
                value={newCamera.rtspUrl}
                onChange={(e) => setNewCamera({ ...newCamera, rtspUrl: e.target.value })}
                className="mt-1 h-8 font-mono border-border bg-background"
              />
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAddModalOpen(false)}
              className="h-8 border-border text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleAddCamera}
              className="h-8 bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Add Camera
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
