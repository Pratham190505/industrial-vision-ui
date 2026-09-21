import { Link } from "@tanstack/react-router";
import { ScanLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { navigationItems } from "@/lib/dashboard-data";
import { cn } from "@/lib/utils";

const routeByLabel = {
  Dashboard: "/",
  "Live Camera": "/live-camera",
  Inventory: "/inventory",
  Safety: "/safety",
  Analytics: "/analytics",
  Reports: "/reports",
  Settings: "/settings",
} as const;

function Brand() {
  return (
    <div className="flex h-18 items-center gap-3 border-b border-sidebar-border px-5">
      <div className="grid size-9 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground shadow-amber">
        <ScanLine className="size-5" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-bold text-sidebar-foreground">WarehouseVision</div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
          AI Command Center
        </div>
      </div>
    </div>
  );
}

export function WarehouseSidebar({
  active,
  mobile = false,
  onNavigate,
}: {
  active: string;
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col bg-sidebar",
        mobile
          ? "w-full"
          : "fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-sidebar-border lg:flex",
      )}
    >
      <Brand />
      <nav className="flex-1 space-y-1 px-3 py-5" aria-label="Main navigation">
        <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          Operations
        </p>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const selected = active === item.label;
          const classes = cn(
            "h-10 w-full justify-start gap-3 border-l-2 px-3 text-sm shadow-none",
            selected
              ? "border-l-primary bg-sidebar-accent text-primary hover:bg-sidebar-accent hover:text-primary"
              : "border-l-transparent text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
          );
          const content = (
            <>
              <Icon className="size-[18px]" aria-hidden="true" />
              {item.label}
            </>
          );
          const route = routeByLabel[item.label as keyof typeof routeByLabel];

          return route ? (
            <Button key={item.label} variant="ghost" asChild className={classes}>
              <Link to={route} onClick={onNavigate}>
                {content}
              </Link>
            </Button>
          ) : (
            <Button key={item.label} variant="ghost" className={classes} onClick={onNavigate}>
              {content}
            </Button>
          );
        })}
      </nav>
      <div className="m-4 border-t border-sidebar-border pt-4">
        <div className="flex items-center gap-3 rounded-md border border-success/20 bg-success/5 px-3 py-3">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-50" />
            <span className="relative inline-flex size-2.5 rounded-full bg-success" />
          </span>
          <div>
            <p className="text-xs font-semibold text-sidebar-foreground">AI Engine Online</p>
            <p className="mt-0.5 text-[10px] text-muted-foreground">All systems nominal</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
