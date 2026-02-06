import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchMarketDetail, fetchMarkets } from "@/lib/api";

type RangeCode = "4W" | "12W" | "YTD" | "1Y" | "ALL";

type ChartSeries = {
  name: string;
  color: string;
  values: Array<number | null>;
};

function fmtNum(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "N/A";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(x);
}

function SimpleLineChart({
  dates,
  series,
  yMin,
  yMax,
  thresholds = [],
}: {
  dates: string[];
  series: ChartSeries[];
  yMin?: number;
  yMax?: number;
  thresholds?: number[];
}) {
  const width = 1000;
  const height = 280;
  const padLeft = 44;
  const padRight = 16;
  const padTop = 12;
  const padBottom = 28;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const allValues = series.flatMap((s) => s.values.filter((v): v is number => typeof v === "number"));
  const minV = yMin ?? (allValues.length ? Math.min(...allValues) : 0);
  const maxV = yMax ?? (allValues.length ? Math.max(...allValues) : 1);
  const safeMin = minV === maxV ? minV - 1 : minV;
  const safeMax = minV === maxV ? maxV + 1 : maxV;

  const xPos = (idx: number) => {
    if (dates.length <= 1) return padLeft + plotW / 2;
    return padLeft + (idx / (dates.length - 1)) * plotW;
  };

  const yPos = (v: number) => {
    const t = (v - safeMin) / (safeMax - safeMin);
    return padTop + (1 - t) * plotH;
  };

  const polyline = (vals: Array<number | null>) => {
    const pts: string[] = [];
    vals.forEach((v, i) => {
      if (typeof v !== "number") return;
      pts.push(`${xPos(i)},${yPos(v)}`);
    });
    return pts.join(" ");
  };

  const firstLabel = dates[0] ?? "";
  const lastLabel = dates[dates.length - 1] ?? "";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full">
      <rect x={0} y={0} width={width} height={height} fill="transparent" />

      <line x1={padLeft} y1={padTop} x2={padLeft} y2={padTop + plotH} stroke="#334155" strokeWidth="1" />
      <line x1={padLeft} y1={padTop + plotH} x2={padLeft + plotW} y2={padTop + plotH} stroke="#334155" strokeWidth="1" />

      {[0.25, 0.5, 0.75].map((t) => {
        const y = padTop + t * plotH;
        return <line key={`g-${t}`} x1={padLeft} y1={y} x2={padLeft + plotW} y2={y} stroke="#1f2937" strokeWidth="1" />;
      })}

      {thresholds.map((v) => {
        if (v < safeMin || v > safeMax) return null;
        const y = yPos(v);
        return (
          <line
            key={`th-${v}`}
            x1={padLeft}
            y1={y}
            x2={padLeft + plotW}
            y2={y}
            stroke="#64748b"
            strokeWidth="1"
            strokeDasharray="5 5"
          />
        );
      })}

      {series.map((s) => (
        <polyline
          key={s.name}
          fill="none"
          stroke={s.color}
          strokeWidth="2"
          points={polyline(s.values)}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ))}

      <text x={padLeft} y={height - 8} fill="#9ba8b8" fontSize="11">
        {firstLabel}
      </text>
      <text x={padLeft + plotW} y={height - 8} fill="#9ba8b8" fontSize="11" textAnchor="end">
        {lastLabel}
      </text>
      <text x={6} y={padTop + 10} fill="#9ba8b8" fontSize="11">
        {safeMax.toFixed(1)}
      </text>
      <text x={6} y={padTop + plotH} fill="#9ba8b8" fontSize="11">
        {safeMin.toFixed(1)}
      </text>
    </svg>
  );
}

export function MarketDetailPage() {
  const [marketId, setMarketId] = useState<string>("");
  const [range, setRange] = useState<RangeCode>("12W");

  const marketsQ = useQuery({
    queryKey: ["markets"],
    queryFn: fetchMarkets,
  });

  const marketOptions = marketsQ.data?.items ?? [];
  useEffect(() => {
    if (!marketId && marketOptions.length > 0) {
      setMarketId(String(marketOptions[0].market_id ?? ""));
    }
  }, [marketId, marketOptions]);

  const detailQ = useQuery({
    queryKey: ["market-detail", marketId, range],
    queryFn: () => fetchMarketDetail(marketId, range),
    enabled: !!marketId,
  });

  const latest = detailQ.data?.latest;
  const series = detailQ.data?.series ?? [];
  const rows = detailQ.data?.table ?? [];
  const dates = series.map((r) => r.report_date ?? "");

  const selectedMarketName = useMemo(() => {
    const x = marketOptions.find((m) => String(m.market_id) === marketId);
    return x?.market_name ?? marketId;
  }, [marketId, marketOptions]);

  const signalClass =
    latest?.signal_state === "bullish"
      ? "text-[#22c55e]"
      : latest?.signal_state === "bearish"
        ? "text-[#ef4444]"
        : latest?.signal_state === "extreme"
          ? "text-[#f59e0b]"
          : "text-[#38bdf8]";

  const priceSeries: ChartSeries[] = [
    {
      name: "Funds Net",
      color: "#22c55e",
      values: series.map((r) => (typeof r.nc_net === "number" ? r.nc_net : null)),
    },
    {
      name: "Commercials Net",
      color: "#ef4444",
      values: series.map((r) => (typeof r.comm_net === "number" ? r.comm_net : null)),
    },
    {
      name: "Open Interest",
      color: "#38bdf8",
      values: series.map((r) => (typeof r.open_interest === "number" ? r.open_interest : null)),
    },
  ];

  const zSeries: ChartSeries[] = [
    {
      name: "Funds Z",
      color: "#f59e0b",
      values: series.map((r) => (typeof r.net_z_52w_funds === "number" ? r.net_z_52w_funds : null)),
    },
    {
      name: "Commercials Z",
      color: "#38bdf8",
      values: series.map((r) => (typeof r.net_z_52w_commercials === "number" ? r.net_z_52w_commercials : null)),
    },
  ];

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Market Detail</h1>

      <div className="terminal-panel grid grid-cols-2 gap-4 p-4">
        <label className="space-y-1 text-xs text-[#9ba8b8]">
          <div>Market</div>
          <select
            className="h-9 w-full rounded-lg border border-[#2e3946] bg-[#141b23] px-2 text-sm text-[#e6ecf3]"
            value={marketId}
            onChange={(e) => setMarketId(e.target.value)}
          >
            {marketOptions.map((m) => (
              <option key={String(m.market_id)} value={String(m.market_id)}>
                {m.market_name ?? m.market_id}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-xs text-[#9ba8b8]">
          <div>Range</div>
          <select
            className="h-9 w-full rounded-lg border border-[#2e3946] bg-[#141b23] px-2 text-sm text-[#e6ecf3]"
            value={range}
            onChange={(e) => setRange(e.target.value as RangeCode)}
          >
            <option value="4W">4W</option>
            <option value="12W">12W</option>
            <option value="YTD">YTD</option>
            <option value="1Y">1Y</option>
            <option value="ALL">ALL</option>
          </select>
        </label>
      </div>

      {detailQ.isLoading && <div className="terminal-panel p-4 text-sm text-[#9ba8b8]">Loading market detail...</div>}
      {detailQ.isError && (
        <div className="terminal-panel border-[#7f1d1d] p-4 text-sm text-[#ef4444]">
          Failed to load market detail: {(detailQ.error as Error)?.message}
        </div>
      )}

      {!detailQ.isLoading && !detailQ.isError && (
        <>
          <div className="text-sm text-[#9ba8b8]">
            Market: <span className="font-semibold text-[#e6ecf3]">{selectedMarketName}</span>
            {" | "}
            Points: <span className="font-mono text-[#e6ecf3]">{detailQ.data?.points ?? 0}</span>
          </div>

          <div className="grid grid-cols-5 gap-4">
            <div className="terminal-panel p-4">
              <div className="text-xs text-[#9ba8b8]">Signal</div>
              <div className={`mt-2 font-mono text-sm ${signalClass}`}>{latest?.signal_state?.toUpperCase() ?? "N/A"}</div>
            </div>
            <div className="terminal-panel p-4">
              <div className="text-xs text-[#9ba8b8]">Funds Net</div>
              <div className="mt-2 font-mono text-sm">{fmtNum(latest?.nc_net)}</div>
            </div>
            <div className="terminal-panel p-4">
              <div className="text-xs text-[#9ba8b8]">Commercials Net</div>
              <div className="mt-2 font-mono text-sm">{fmtNum(latest?.comm_net)}</div>
            </div>
            <div className="terminal-panel p-4">
              <div className="text-xs text-[#9ba8b8]">Z-score (Funds)</div>
              <div className="mt-2 font-mono text-sm text-[#f59e0b]">
                {typeof latest?.net_z_52w_funds === "number" ? latest.net_z_52w_funds.toFixed(2) : "N/A"}
              </div>
            </div>
            <div className="terminal-panel p-4">
              <div className="text-xs text-[#9ba8b8]">Updated</div>
              <div className="mt-2 font-mono text-sm">{latest?.report_date ?? "N/A"}</div>
            </div>
          </div>

          <div className="terminal-panel p-4">
            <div className="mb-2 text-sm font-medium">Price + COT</div>
            <div className="h-72 rounded-lg border border-[#2e3946] bg-[#141b23] p-3">
              <div className="mb-2 flex gap-4 text-xs text-[#9ba8b8]">
                <span className="font-mono text-[#22c55e]">Funds Net</span>
                <span className="font-mono text-[#ef4444]">Commercials Net</span>
                <span className="font-mono text-[#38bdf8]">Open Interest</span>
              </div>
              <SimpleLineChart dates={dates} series={priceSeries} />
            </div>
          </div>

          <div className="terminal-panel p-4">
            <div className="mb-2 text-sm font-medium">Z-score / Extremes</div>
            <div className="h-56 rounded-lg border border-[#2e3946] bg-[#141b23] p-3">
              <div className="mb-2 flex gap-4 text-xs text-[#9ba8b8]">
                <span className="font-mono text-[#f59e0b]">Funds Z</span>
                <span className="font-mono text-[#38bdf8]">Commercials Z</span>
                <span className="font-mono text-[#64748b]">Lines: +2 / 0 / -2</span>
              </div>
              <SimpleLineChart dates={dates} series={zSeries} yMin={-3.5} yMax={3.5} thresholds={[2, 0, -2]} />
            </div>
          </div>

          <div className="terminal-panel p-4">
            <div className="mb-2 text-sm font-medium">Recent Weekly Data</div>
            <div className="overflow-hidden rounded-lg border border-[#2e3946]">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-[#141b23] text-xs text-[#9ba8b8]">
                  <tr>
                    <th className="px-3 py-2 text-left">Date</th>
                    <th className="px-3 py-2 text-right">Funds Net</th>
                    <th className="px-3 py-2 text-right">Com Net</th>
                    <th className="px-3 py-2 text-right">Funds Z</th>
                    <th className="px-3 py-2 text-right">Com Z</th>
                    <th className="px-3 py-2 text-right">OI</th>
                    <th className="px-3 py-2 text-right">OI Delta %</th>
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {rows.map((r, idx) => (
                    <tr key={`${r.report_date ?? "d"}-${idx}`} className="border-t border-[#2e3946]">
                      <td className="px-3 py-2 font-sans">{r.report_date ?? "N/A"}</td>
                      <td className="px-3 py-2 text-right">{fmtNum(r.nc_net)}</td>
                      <td className="px-3 py-2 text-right">{fmtNum(r.comm_net)}</td>
                      <td className="px-3 py-2 text-right">
                        {typeof r.net_z_52w_funds === "number" ? r.net_z_52w_funds.toFixed(2) : "N/A"}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {typeof r.net_z_52w_commercials === "number" ? r.net_z_52w_commercials.toFixed(2) : "N/A"}
                      </td>
                      <td className="px-3 py-2 text-right">{fmtNum(r.open_interest)}</td>
                      <td className="px-3 py-2 text-right">
                        {typeof r.open_interest_chg_1w_pct === "number"
                          ? `${(r.open_interest_chg_1w_pct * 100).toFixed(2)}%`
                          : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
