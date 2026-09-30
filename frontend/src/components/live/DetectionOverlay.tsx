import React, { useEffect, useRef } from "react";
import { LiveFrameResponse, LiveTrackedObject } from "@/services/liveMonitoringApi";

interface DetectionOverlayProps {
  analysis: LiveFrameResponse | null;
  videoWidth: number;
  videoHeight: number;
}

const CLASS_COLORS: Record<string, { stroke: string; fill: string; text: string }> = {
  person: { stroke: "#10b981", fill: "rgba(16, 185, 129, 0.15)", text: "#ecfdf5" },
  worker: { stroke: "#10b981", fill: "rgba(16, 185, 129, 0.15)", text: "#ecfdf5" },
  forklift: { stroke: "#06b6d4", fill: "rgba(6, 182, 212, 0.15)", text: "#ecfeff" },
  box: { stroke: "#f59e0b", fill: "rgba(245, 158, 11, 0.15)", text: "#fffbeb" },
  pallet: { stroke: "#8b5cf6", fill: "rgba(139, 92, 246, 0.15)", text: "#f5f3ff" },
  crate: { stroke: "#f97316", fill: "rgba(249, 115, 22, 0.15)", text: "#fff7ed" },
  default: { stroke: "#3b82f6", fill: "rgba(59, 130, 246, 0.15)", text: "#eff6ff" },
};

const HAZARD_COLOR = {
  stroke: "#ef4444",
  fill: "rgba(239, 68, 68, 0.25)",
  text: "#fef2f2",
};

export const DetectionOverlay: React.FC<DetectionOverlayProps> = ({
  analysis,
  videoWidth,
  videoHeight,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Synchronize canvas buffer resolution with container display size
    const rect = canvas.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!analysis || !analysis.objects || analysis.objects.length === 0) {
      return;
    }

    const frameWidth = analysis.frame_width || videoWidth || 640;
    const frameHeight = analysis.frame_height || videoHeight || 480;

    const scaleX = canvas.width / frameWidth;
    const scaleY = canvas.height / frameHeight;

    // Gather tracks involved in safety hazards to highlight them with hazard borders
    const hazardTrackIds = new Set<number>();
    if (analysis.safety?.events) {
      analysis.safety.events.forEach((ev) => {
        ev.track_ids?.forEach((id) => hazardTrackIds.add(id));
      });
    }

    // Draw each detected & tracked object
    analysis.objects.forEach((obj: LiveTrackedObject) => {
      const isHazard = hazardTrackIds.has(obj.track_id);
      const colorScheme = isHazard
        ? HAZARD_COLOR
        : CLASS_COLORS[obj.class_name.toLowerCase()] || CLASS_COLORS.default;

      const x = obj.bbox.x1 * scaleX;
      const y = obj.bbox.y1 * scaleY;
      const w = Math.max(1, (obj.bbox.x2 - obj.bbox.x1) * scaleX);
      const h = Math.max(1, (obj.bbox.y2 - obj.bbox.y1) * scaleY);

      // Bounding box fill & outline
      ctx.fillStyle = colorScheme.fill;
      ctx.fillRect(x, y, w, h);

      ctx.strokeStyle = colorScheme.stroke;
      ctx.lineWidth = isHazard ? 3 : 2;
      ctx.strokeRect(x, y, w, h);

      // Corner accent markers
      const cornerLen = Math.min(12, w / 4, h / 4);
      ctx.lineWidth = isHazard ? 4 : 3;
      ctx.beginPath();
      // Top-Left
      ctx.moveTo(x, y + cornerLen);
      ctx.lineTo(x, y);
      ctx.lineTo(x + cornerLen, y);
      // Top-Right
      ctx.moveTo(x + w - cornerLen, y);
      ctx.lineTo(x + w, y);
      ctx.lineTo(x + w, y + cornerLen);
      // Bottom-Left
      ctx.moveTo(x, y + h - cornerLen);
      ctx.lineTo(x, y + h);
      ctx.lineTo(x + cornerLen, y + h);
      // Bottom-Right
      ctx.moveTo(x + w - cornerLen, y + h);
      ctx.lineTo(x + w, y + h);
      ctx.lineTo(x + w, y + h - cornerLen);
      ctx.stroke();

      // Label Badge: "[Class] #[TrackID] (Conf%)"
      const labelText = `${obj.class_name.toUpperCase()} #${obj.track_id} (${Math.round(
        obj.confidence * 100
      )}%)`;
      ctx.font = "bold 11px ui-monospace, SFMono-Regular, Menlo, monospace";
      const textMetrics = ctx.measureText(labelText);
      const paddingX = 6;
      const badgeHeight = 18;
      const badgeWidth = textMetrics.width + paddingX * 2;
      const badgeY = Math.max(0, y - badgeHeight);

      // Badge background
      ctx.fillStyle = colorScheme.stroke;
      ctx.fillRect(x, badgeY, badgeWidth, badgeHeight);

      // Badge text
      ctx.fillStyle = colorScheme.text;
      ctx.fillText(labelText, x + paddingX, badgeY + 13);

      // If hazard, show exclamation badge
      if (isHazard) {
        ctx.fillStyle = "#ef4444";
        ctx.fillRect(x + badgeWidth + 2, badgeY, 18, badgeHeight);
        ctx.fillStyle = "#ffffff";
        ctx.fillText("⚠", x + badgeWidth + 6, badgeY + 13);
      }
    });
  }, [analysis, videoWidth, videoHeight]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 size-full z-10"
      aria-label="Real-time detection and tracking overlay"
    />
  );
};
