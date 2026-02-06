import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSignals } from "@/lib/api";

export function SignalsPage() {
  const [signal, setSignal] = useState<"all" | "extreme" | "bullish" | "bearish" | "neutral">("all");
  const [category, setCategory] = useState("all");
  const [conflict, setConflict] = useState<"all" | "High" | "Medium" | "Low">("all");

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["signals", signal, category, conflict],
    queryFn: () =>
      fetchSignals({
        signal,
        category,
        conflict,
        limit: 300,
      }),
  });

  const items = data?.items ?? [];
  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const x of items) {
      if (x.category) set.add(x.category);
    }
    return ["all", ...Array.from(set).sort((a, b) => a.localeCompare(b))];
  }, [items]);

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Signals</h1>

      <div className="terminal-panel grid grid-cols-3 gap-4 p-4">
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

        <label className="space-y-1 text-xs text-[#9ba8b8]">
          <div>Conflict</div>
          <select
            className="h-9 w-full rounded-lg border border-[#2e3946] bg-[#141b23] px-2 text-sm text-[#e6ecf3]"
            value={conflict}
            onChange={(e) => setConflict(e.target.value as typeof conflict)}
          >
            <option value="all">all</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </label>
      </div>

      {isLoading && (
        <div className="terminal-panel p-3 text-sm text-[#9ba8b8]">
          Loading signals...
        </div>
      )}

      {isError && (
        <div className="terminal-panel border-[#7f1d1d] p-3 text-sm text-[#ef4444]">
          Failed to load signals: {(error as Error)?.message ?? "unknown error"}
        </div>
      )}

      <div className="terminal-panel p-4">
        <div className="mb-2 text-sm font-medium">Active Signals</div>
        <div className="mb-3 text-xs text-[#9ba8b8]">
          Total: <span className="font-mono text-[#e6ecf3]">{data?.total ?? 0}</span>
          {" | "}
          Report date: <span className="font-mono text-[#e6ecf3]">{data?.latest_report_date ?? "N/A"}</span>
        </div>
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
                <th className="px-3 py-2 text-right">Delta 1W</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {!isLoading && items.length === 0 && (
                <tr className="border-t border-[#2e3946]">
                  <td className="px-3 py-3 text-[#9ba8b8]" colSpan={7}>
                    No signals for current filters.
                  </td>
                </tr>
              )}
              {items.map((row, idx) => {
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
                const d1 = row.open_interest_chg_1w_pct;

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
                    <td className="px-3 py-2 text-right">
                      {typeof d1 === "number" ? `${(d1 * 100).toFixed(2)}%` : "N/A"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
