import React from "react";
import { AlertTriangle, HardHat, Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import { LiveSafetyResult, LivePPEResult } from "@/services/liveMonitoringApi";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SafetyPanelProps {
  safety: LiveSafetyResult | null;
  ppe: LivePPEResult | null;
}

export const SafetyPanel: React.FC<SafetyPanelProps> = ({ safety, ppe }) => {
  const riskLevel = safety?.risk_level || "normal";
  const events = safety?.events || [];
  const workers = ppe?.workers || [];
  const ppeViolations = ppe?.violations_count || 0;

  const riskBadgeClasses = {
    normal: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    warning: "bg-amber-500/15 text-amber-400 border-amber-500/30 animate-pulse",
    high: "bg-orange-500/15 text-orange-400 border-orange-500/30 animate-pulse",
    critical: "bg-rose-500/20 text-rose-400 border-rose-500/40 animate-pulse",
  }[riskLevel] || "bg-muted text-muted-foreground";

  return (
    <div className="rounded-lg border border-border bg-card/90 p-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          {riskLevel === "normal" ? (
            <ShieldCheck className="size-5 text-emerald-400" />
          ) : (
            <ShieldAlert className="size-5 text-rose-400 animate-bounce" />
          )}
          <h3 className="text-sm font-semibold text-foreground">Safety & Compliance</h3>
        </div>
        <Badge variant="outline" className={cn("px-2.5 py-0.5 font-mono text-xs uppercase", riskBadgeClasses)}>
          {riskLevel}
        </Badge>
      </div>

      {/* Safety Events Stream */}
      <div className="mt-3 space-y-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Active Alerts</span>
          <span className="font-mono font-medium text-foreground">{events.length}</span>
        </div>

        {events.length === 0 ? (
          <div className="rounded-md border border-border/40 bg-muted/20 py-3 text-center text-xs text-muted-foreground">
            No active safety violations detected
          </div>
        ) : (
          <div className="max-h-40 space-y-1.5 overflow-y-auto pr-1">
            {events.map((ev, idx) => {
              const isCrit = ev.severity === "critical" || ev.severity === "high";
              return (
                <div
                  key={`${ev.event_type}-${idx}`}
                  className={cn(
                    "flex items-start gap-2 rounded border px-2.5 py-1.5 text-xs transition-colors",
                    isCrit
                      ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-200"
                  )}
                >
                  <AlertTriangle className={cn("size-3.5 shrink-0 mt-0.5", isCrit ? "text-rose-400" : "text-amber-400")} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-semibold uppercase tracking-wide">
                        {ev.event_type.replace(/_/g, " ")}
                      </span>
                      {ev.distance && (
                        <span className="font-mono text-[10px] opacity-80">
                          {Math.round(ev.distance)} px
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-[11px] opacity-90 truncate">{ev.message}</p>
                    {ev.track_ids && ev.track_ids.length > 0 && (
                      <div className="mt-1 flex items-center gap-1 font-mono text-[10px] opacity-75">
                        <span>Affected Tracks:</span>
                        {ev.track_ids.map((id) => (
                          <span key={id} className="rounded bg-black/40 px-1">
                            #{id}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* PPE Compliance Section */}
      {ppe?.enabled && (
        <div className="mt-4 border-t border-border/60 pt-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span className="flex items-center gap-1.5">
              <HardHat className="size-3.5 text-primary" />
              PPE Compliance
            </span>
            <span className={cn("font-mono text-xs font-semibold", ppeViolations > 0 ? "text-rose-400" : "text-emerald-400")}>
              {ppeViolations > 0 ? `${ppeViolations} Non-compliant` : "All Compliant"}
            </span>
          </div>

          {workers.length > 0 ? (
            <div className="space-y-1">
              {workers.map((w) => (
                <div
                  key={w.track_id}
                  className="flex items-center justify-between rounded bg-muted/20 px-2 py-1 text-[11px]"
                >
                  <span className="font-mono font-medium">Worker #{w.track_id}</span>
                  <div className="flex items-center gap-1">
                    {w.status === "compliant" ? (
                      <span className="text-emerald-400">✓ Full PPE</span>
                    ) : (
                      <span className="text-rose-400">
                        Missing: {w.missing_ppe.join(", ") || "Safety Gear"}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground">
              {ppe.available ? "No workers currently visible." : "PPE model not configured for live feed."}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
