import React from "react";
import { Boxes, Package, Layers, Info } from "lucide-react";
import { LiveInventoryResult } from "@/services/liveMonitoringApi";
import { Badge } from "@/components/ui/badge";

interface InventoryPanelProps {
  inventory: LiveInventoryResult | null;
}

export const InventoryPanel: React.FC<InventoryPanelProps> = ({ inventory }) => {
  const counts = inventory?.counts || {};
  const uniqueCounts = inventory?.unique_counts || {};
  const isAvailable = inventory?.available ?? false;

  const classIcons: Record<string, React.ReactNode> = {
    box: <Package className="size-4 text-amber-400" />,
    pallet: <Layers className="size-4 text-purple-400" />,
    crate: <Boxes className="size-4 text-orange-400" />,
  };

  const totalVisible = Object.values(counts).reduce((acc, curr) => acc + curr, 0);

  return (
    <div className="rounded-lg border border-border bg-card/90 p-4 shadow-sm backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <Boxes className="size-5 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Visible Inventory</h3>
        </div>
        <Badge variant="outline" className="font-mono text-xs text-primary border-primary/30">
          {totalVisible} Items Visible
        </Badge>
      </div>

      <div className="mt-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(counts).length > 0 ? (
            Object.entries(counts).map(([itemClass, count]) => (
              <div
                key={itemClass}
                className="flex flex-col justify-between rounded-md border border-border/50 bg-background/50 p-2.5"
              >
                <div className="flex items-center justify-between">
                  <span className="capitalize text-xs text-muted-foreground">{itemClass}</span>
                  {classIcons[itemClass.toLowerCase()] || <Package className="size-4 text-muted-foreground" />}
                </div>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="font-mono text-lg font-bold text-foreground">{count}</span>
                  {uniqueCounts[itemClass] !== undefined && (
                    <span className="font-mono text-[10px] text-muted-foreground" title="Total unique tracks seen">
                      {uniqueCounts[itemClass]} unique
                    </span>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full py-4 text-center text-xs text-muted-foreground">
              {isAvailable
                ? "No inventory objects currently visible in camera frame."
                : "Inventory classes not supported by current detection model."}
            </div>
          )}
        </div>

        <div className="mt-3 flex items-start gap-1.5 rounded bg-muted/20 p-2 text-[11px] text-muted-foreground">
          <Info className="size-3.5 shrink-0 mt-0.5 text-primary/70" />
          <span>
            Counts reflect <strong>visible camera objects</strong> in current frame, not guaranteed physical warehouse inventory.
          </span>
        </div>
      </div>
    </div>
  );
};
