import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "@/lib/api";

export function DashboardPage() {
  const [signal, setSignal] = useState<"all" | "extreme" | "bullish" | "bearish" | "neutral">("all");
  const [category, setCategory] = useState("all");

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard", signal, category],
    queryFn: () => fetchDashboard({ signal, category, limit: 100 }),
  });

  const summary = data?.summary ?? { bullish: 0, bearish: 0, extreme: 0, neutral: 0 };
  const rows = data?.items ?? [];
  const categories = ["all", ...(data?.categories ?? [])];

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <div className="terminal-panel grid grid-cols-2 gap-4 p-4">
        <label className="space-y-1 text-xs text-[#9ba8b8]">
          <div>Signal</div>
          <select
            className="h-9 w-full rounded-lg border border-[#2e3946] bg-[#141b23] px-2 text-sm text-[#e6ecf3]"
            value={signal}
            onChange={(e) => setSignal(e.target.value as typeof signal)}
          >
            <option value="all">all</option>
            <option value="extreme">extreme</option>
            <option value="bullish">bullish</option>
            <option value="bearish">bearish</option>
            <option value="neutral">neutral</option>
          </select>
        </label>
        <label className="space-y-1 text-xs text-[#9ba8b8]">
          <div>Category</div>
          <select
            className="h-9 w-full rounded-lg border border-[#2e3946] bg-[#141b23] px-2 text-sm text-[#e6ecf3]"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="terminal-panel p-4">
          <div className="text-xs text-[#9ba8b8]">Bullish</div>
          <div className="mt-2 font-mono text-2xl text-[#22c55e]">{summary.bullish}</div>
        </div>
        <div className="terminal-panel p-4">
          <div className="text-xs text-[#9ba8b8]">Bearish</div>
          <div className="mt-2 font-mono text-2xl text-[#ef4444]">{summary.bearish}</div>
        </div>
        <div className="terminal-panel p-4">
          <div className="text-xs text-[#9ba8b8]">Extreme</div>
          <div className="mt-2 font-mono text-2xl text-[#f59e0b]">{summary.extreme}</div>
        </div>
        <div className="terminal-panel p-4">
          <div className="text-xs text-[#9ba8b8]">Neutral</div>
          <div className="mt-2 font-mono text-2xl text-[#38bdf8]">{summary.neutral}</div>
        </div>
      </div>

      <div className="terminal-panel p-4">
        <div className="mb-2 text-sm font-medium">Market Scan</div>
        {isLoading && <div className="text-sm text-[#9ba8b8]">Loading dashboard...</div>}
        {isError && (
          <div className="text-sm text-[#ef4444]">Failed to load dashboard: {(error as Error)?.message}</div>
        )}
        {!isLoading && !isError && (
          <div className="overflow-hidden rounded-lg border border-[#2e3946]">
            <table className="w-full border-collapse text-sm">
              <thead className="bg-[#141b23] text-xs text-[#9ba8b8]">
                <tr>
                  <th className="px-3 py-2 text-left">Market</th>
                  <th className="px-3 py-2 text-left">Category</th>
                  <th className="px-3 py-2 text-left">Signal</th>
                  <th className="px-3 py-2 text-right">Score</th>
                  <th className="px-3 py-2 text-left">Conflict</th>
                  <th className="px-3 py-2 text-right">Z-score</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {rows.map((row, idx) => {
                  const signalClass =
                    row.signal_state === "bullish"
                      ? "text-[#22c55e]"
                      : row.signal_state === "bearish"
                        ? "text-[#ef4444]"
                        : row.signal_state === "extreme"
                          ? "text-[#f59e0b]"
                          : "text-[#38bdf8]";
                  const z = row.net_z_52w_funds;
                  const zClass = z !== null && z !== undefined && Math.abs(z) >= 1.5 ? "text-[#f59e0b]" : "";
                  return (
                    <tr key={`${row.market_id ?? "m"}-${idx}`} className="border-t border-[#2e3946]">
                      <td className="px-3 py-2 font-sans">{row.market_name ?? row.market_id ?? "N/A"}</td>
                      <td className="px-3 py-2 font-sans">{row.category ?? "N/A"}</td>
                      <td className={`px-3 py-2 ${signalClass}`}>{row.signal_state ?? "neutral"}</td>
                      <td className="px-3 py-2 text-right">{row.hot_score?.toFixed(2) ?? "N/A"}</td>
                      <td className="px-3 py-2 font-sans">{row.conflict_level ?? "N/A"}</td>
                      <td className={`px-3 py-2 text-right ${zClass}`}>
                        {typeof z === "number" ? z.toFixed(2) : "N/A"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
