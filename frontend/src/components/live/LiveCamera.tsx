import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Camera,
  CameraOff,
  CheckCircle2,
  Gauge,
  Play,
  Square,
  Video,
  VideoOff,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  createLiveSession,
  getLiveSession,
  LiveFrameResponse,
  sendLiveFrame,
  stopLiveSession,
} from "@/services/liveMonitoringApi";
import { DetectionOverlay } from "./DetectionOverlay";
import { cn } from "@/lib/utils";

interface LiveCameraProps {
  onAnalysisUpdate?: (analysis: LiveFrameResponse | null) => void;
  onSessionChange?: (sessionId: string | null) => void;
  frameIntervalMs?: number;
}

export const LiveCamera: React.FC<LiveCameraProps> = ({
  onAnalysisUpdate,
  onSessionChange,
  frameIntervalMs = 250, // Default ~4 FPS
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isProcessingRef = useRef<boolean>(false);
  const monitoringRef = useRef<boolean>(false);
  const sessionIdRef = useRef<string | null>(null);

  // Component state
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [monitoring, setMonitoring] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [latestAnalysis, setLatestAnalysis] = useState<LiveFrameResponse | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<"connected" | "unavailable">("connected");
  const [videoDims, setVideoDims] = useState<{ width: number; height: number }>({
    width: 640,
    height: 480,
  });

  // Performance telemetry
  const [backendLatencyMs, setBackendLatencyMs] = useState<number>(0);
  const [fps, setFps] = useState<number>(0);
  const frameCountRef = useRef<number>(0);
  const lastFpsTimeRef = useRef<number>(Date.now());

  // --------------------------------------------------------------------------
  // Camera Stream Lifecycle
  // --------------------------------------------------------------------------

  const startCamera = async () => {
    setCameraError(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError("Your browser does not support webcam streaming (getUserMedia not found).");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user",
        },
        audio: false, // Critical: explicitly no microphone access
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
    } catch (err: any) {
      console.error("Webcam error:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setCameraError("Camera permission denied. Please allow camera access in browser settings.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setCameraError("No webcam hardware detected on this device.");
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        setCameraError("Camera is currently in use by another application or tab.");
      } else {
        setCameraError(err.message || "Failed to initialize camera.");
      }
      setCameraActive(false);
    }
  };

  const stopCamera = useCallback(() => {
    if (monitoringRef.current) {
      stopMonitoring();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraActive(false);
    setLatestAnalysis(null);
    if (onAnalysisUpdate) onAnalysisUpdate(null);
  }, []);

  // --------------------------------------------------------------------------
  // Live Monitoring Session & Controlled Frame Loop
  // --------------------------------------------------------------------------

  const startMonitoring = async () => {
    if (!cameraActive || !videoRef.current) {
      setCameraError("Please start the camera first.");
      return;
    }

    try {
      const session = await createLiveSession();
      setSessionId(session.session_id);
      sessionIdRef.current = session.session_id;
      if (onSessionChange) onSessionChange(session.session_id);

      setMonitoring(true);
      monitoringRef.current = true;
      setBackendStatus("connected");
      lastFpsTimeRef.current = Date.now();
      frameCountRef.current = 0;
    } catch (err: any) {
      console.error("Session creation error:", err);
      setBackendStatus("unavailable");
      setCameraError(`Could not start live session on backend: ${err.message}`);
    }
  };

  const stopMonitoring = async () => {
    monitoringRef.current = false;
    setMonitoring(false);

    const activeId = sessionIdRef.current;
    if (activeId) {
      try {
        await stopLiveSession(activeId);
      } catch (err) {
        console.warn("Error stopping session on backend:", err);
      }
      setSessionId(null);
      sessionIdRef.current = null;
      if (onSessionChange) onSessionChange(null);
    }

    setLatestAnalysis(null);
    if (onAnalysisUpdate) onAnalysisUpdate(null);
    setFps(0);
  };

  // Offscreen canvas frame extraction
  const captureAndSendFrame = useCallback(async () => {
    if (!monitoringRef.current || isProcessingRef.current || !videoRef.current) {
      return;
    }

    const video = videoRef.current;
    if (video.readyState < 2 || video.videoWidth === 0 || video.videoHeight === 0) {
      return;
    }

    const currentSessionId = sessionIdRef.current;
    if (!currentSessionId) return;

    isProcessingRef.current = true;

    try {
      // Offscreen canvas for frame capture
      const offscreen = document.createElement("canvas");
      // Scale resolution slightly to optimize network transport and inference latency
      const targetWidth = Math.min(video.videoWidth, 960);
      const targetHeight = Math.round((targetWidth / video.videoWidth) * video.videoHeight);
      offscreen.width = targetWidth;
      offscreen.height = targetHeight;

      const ctx = offscreen.getContext("2d");
      if (!ctx) {
        isProcessingRef.current = false;
        return;
      }

      ctx.drawImage(video, 0, 0, targetWidth, targetHeight);

      // Convert frame to JPEG blob (~70% quality, well under 2MB limit)
      offscreen.toBlob(
        async (blob) => {
          if (!blob) {
            isProcessingRef.current = false;
            return;
          }

          try {
            const result = await sendLiveFrame(currentSessionId, blob);
            setBackendStatus("connected");
            setLatestAnalysis(result);
            setBackendLatencyMs(result.processing_time_ms);
            if (onAnalysisUpdate) onAnalysisUpdate(result);

            // Calculate rolling client FPS
            frameCountRef.current += 1;
            const now = Date.now();
            const elapsed = (now - lastFpsTimeRef.current) / 1000;
            if (elapsed >= 1.0) {
              setFps(Number((frameCountRef.current / elapsed).toFixed(1)));
              frameCountRef.current = 0;
              lastFpsTimeRef.current = now;
            }
          } catch (apiErr: any) {
            console.error("Frame upload error:", apiErr);
            if (apiErr.message?.includes("expired") || apiErr.message?.includes("no longer active")) {
              stopMonitoring();
              setCameraError("Live session expired. Please start monitoring again.");
            } else {
              setBackendStatus("unavailable");
            }
          } finally {
            isProcessingRef.current = false;
          }
        },
        "image/jpeg",
        0.7
      );
    } catch (captureErr) {
      console.error("Frame capture error:", captureErr);
      isProcessingRef.current = false;
    }
  }, [onAnalysisUpdate]);

  // Throttled frame loop
  useEffect(() => {
    if (!monitoring) return;

    const intervalId = setInterval(() => {
      captureAndSendFrame();
    }, frameIntervalMs);

    return () => clearInterval(intervalId);
  }, [monitoring, frameIntervalMs, captureAndSendFrame]);

  // Handle video element loadedmetadata
  const handleVideoLoadedMetadata = () => {
    if (videoRef.current) {
      setVideoDims({
        width: videoRef.current.videoWidth || 640,
        height: videoRef.current.videoHeight || 480,
      });
    }
  };

  // Cleanup MediaStream tracks on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (sessionIdRef.current) {
        stopLiveSession(sessionIdRef.current).catch(() => {});
      }
    };
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* Video Viewport Container */}
      <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-border bg-black shadow-2xl">
        {/* Native Browser Video Element */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          onLoadedMetadata={handleVideoLoadedMetadata}
          className={cn(
            "size-full object-contain transition-opacity duration-300",
            cameraActive ? "opacity-100" : "opacity-0"
          )}
        />

        {/* Real-time Bounding Box & Track ID Canvas Overlay */}
        {cameraActive && monitoring && (
          <DetectionOverlay
            analysis={latestAnalysis}
            videoWidth={videoDims.width}
            videoHeight={videoDims.height}
          />
        )}

        {/* Camera Inactive Placeholder */}
        {!cameraActive && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-muted/10 p-6 text-center">
            <div className="rounded-full bg-panel/80 p-4 border border-border">
              <CameraOff className="size-8 text-muted-foreground" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-foreground">Webcam Stream Disconnected</h4>
              <p className="mt-1 text-xs text-muted-foreground max-w-sm">
                Click <strong>Start Camera</strong> to authorize browser access. Frames are sampled locally at ~4 FPS and analyzed securely.
              </p>
            </div>
            <Button onClick={startCamera} size="sm" className="mt-2 gap-2">
              <Camera className="size-4" />
              Start Camera
            </Button>
          </div>
        )}

        {/* HUD Status Bar Overlay */}
        <div className="pointer-events-none absolute left-3 top-3 z-20 flex flex-wrap items-center gap-2">
          {/* Camera Status */}
          <Badge
            variant="outline"
            className={cn(
              "backdrop-blur-md px-2.5 py-1 text-xs font-mono font-medium shadow-sm",
              cameraActive
                ? "bg-black/60 border-emerald-500/50 text-emerald-400"
                : "bg-black/60 border-border text-muted-foreground"
            )}
          >
            <span
              className={cn(
                "mr-1.5 size-2 rounded-full inline-block",
                cameraActive ? "bg-emerald-400 animate-pulse" : "bg-muted-foreground"
              )}
            />
            CAM: {cameraActive ? "Connected" : "Disconnected"}
          </Badge>

          {/* Backend Status */}
          <Badge
            variant="outline"
            className={cn(
              "backdrop-blur-md px-2.5 py-1 text-xs font-mono font-medium shadow-sm",
              backendStatus === "connected"
                ? "bg-black/60 border-emerald-500/50 text-emerald-400"
                : "bg-black/60 border-rose-500/50 text-rose-400"
            )}
          >
            {backendStatus === "connected" ? (
              <Wifi className="mr-1.5 size-3 inline-block" />
            ) : (
              <WifiOff className="mr-1.5 size-3 inline-block" />
            )}
            API: {backendStatus === "connected" ? "Online" : "Unavailable"}
          </Badge>

          {/* Monitoring Status */}
          <Badge
            variant="outline"
            className={cn(
              "backdrop-blur-md px-2.5 py-1 text-xs font-mono font-medium shadow-sm",
              monitoring
                ? "bg-black/60 border-cyan-500/50 text-cyan-400"
                : "bg-black/60 border-border text-muted-foreground"
            )}
          >
            AI: {monitoring ? "Active" : "Stopped"}
          </Badge>

          {/* Telemetry (Latency & FPS) */}
          {monitoring && (
            <Badge
              variant="outline"
              className="bg-black/60 border-border text-xs font-mono backdrop-blur-md px-2.5 py-1 text-muted-foreground shadow-sm"
            >
              <Gauge className="mr-1.5 size-3 inline-block text-primary" />
              Inference: {backendLatencyMs} ms · {fps} FPS
            </Badge>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {cameraError && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          <AlertCircle className="size-4 shrink-0 text-rose-400" />
          <span className="flex-1">{cameraError}</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-rose-300 hover:text-rose-100 hover:bg-rose-500/20"
            onClick={() => setCameraError(null)}
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Control Buttons Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card/60 p-3 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          {!cameraActive ? (
            <Button onClick={startCamera} variant="outline" className="gap-2 text-xs">
              <Camera className="size-3.5 text-primary" />
              Start Camera
            </Button>
          ) : (
            <Button onClick={stopCamera} variant="outline" className="gap-2 text-xs text-rose-400 hover:text-rose-300">
              <CameraOff className="size-3.5" />
              Stop Camera
            </Button>
          )}

          {!monitoring ? (
            <Button
              onClick={startMonitoring}
              disabled={!cameraActive}
              className="gap-2 text-xs bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Play className="size-3.5 fill-current" />
              Start Monitoring
            </Button>
          ) : (
            <Button
              onClick={stopMonitoring}
              variant="destructive"
              className="gap-2 text-xs"
            >
              <Square className="size-3.5 fill-current" />
              Stop Monitoring
            </Button>
          )}
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
          {sessionId && (
            <span className="hidden sm:inline-block">
              Session: <span className="text-foreground">{sessionId.slice(0, 8)}...</span>
            </span>
          )}
          <span>Interval: ~{frameIntervalMs}ms (~4 FPS)</span>
        </div>
      </div>
    </div>
  );
};
