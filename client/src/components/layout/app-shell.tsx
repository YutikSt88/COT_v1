import { BarChart3, ChartCandlestick, Radar } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Dashboard", icon: Radar },
  { to: "/market", label: "Market Detail", icon: ChartCandlestick },
  { to: "/signals", label: "Signals", icon: BarChart3 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#12171d] text-[#e6ecf3]">
      <header className="flex h-14 items-center justify-between border-b border-[#2e3946] px-5">
        <div className="text-sm font-semibold tracking-[0.08em] text-[#f3f6fb]">COT ANALYTICS</div>
        <div className="flex items-center gap-4 text-xs text-[#9ba8b8]">
          <span className="rounded border border-[#2e3946] bg-[#1a212b] px-2 py-1">Market: EUR</span>
          <span className="rounded border border-[#2e3946] bg-[#1a212b] px-2 py-1">Range: 12W</span>
          <span className="rounded border border-[#2e3946] bg-[#1a212b] px-2 py-1 text-[#86efac]">Data: Updated</span>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1700px]">
        <aside className="w-60 border-r border-[#2e3946] p-4">
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
                    active
                      ? "border border-[#2e3946] bg-[#1f2732] text-[#f4f7fc]"
                      : "text-[#9ba8b8] hover:bg-[#1a212b] hover:text-[#e6ecf3]",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
