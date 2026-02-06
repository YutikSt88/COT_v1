export type SignalState = "extreme" | "bullish" | "bearish" | "neutral";

export interface SignalItem {
  market_id?: string;
  market_name?: string;
  category?: string;
  signal_state?: SignalState;
  cot_traffic_signal?: number | null;
  hot_score?: number | null;
  conflict_level?: string | null;
  oi_risk_level?: string | null;
  net_z_52w_funds?: number | null;
  open_interest_chg_1w_pct?: number | null;
  is_hot?: boolean | null;
}

export interface SignalsResponse {
  items: SignalItem[];
  total: number;
  latest_report_date: string | null;
}

export interface DashboardResponse {
  summary: {
    bullish: number;
    bearish: number;
    extreme: number;
    neutral: number;
  };
  items: SignalItem[];
  total: number;
  latest_report_date: string | null;
  categories: string[];
}

export interface MarketOption {
  market_id?: string;
  market_name?: string;
  category?: string;
}

export interface MarketsResponse {
  items: MarketOption[];
}

export interface MarketDetailPoint {
  report_date?: string | null;
  nc_net?: number | null;
  comm_net?: number | null;
  open_interest?: number | null;
  net_z_52w_funds?: number | null;
  net_z_52w_commercials?: number | null;
  nc_net_chg_1w?: number | null;
  comm_net_chg_1w?: number | null;
  open_interest_chg_1w_pct?: number | null;
}

export interface MarketDetailResponse {
  latest: {
    market_id?: string;
    report_date?: string | null;
    signal_state?: SignalState;
    nc_net?: number | null;
    comm_net?: number | null;
    net_z_52w_funds?: number | null;
    net_z_52w_commercials?: number | null;
    open_interest?: number | null;
    open_interest_chg_1w?: number | null;
  };
  series: MarketDetailPoint[];
  table: MarketDetailPoint[];
  range: "4W" | "12W" | "YTD" | "1Y" | "ALL";
  points: number;
}

export interface SignalsQuery {
  signal?: "all" | SignalState;
  category?: string;
  conflict?: "all" | "High" | "Medium" | "Low";
  limit?: number;
}

export interface DashboardQuery {
  signal?: "all" | SignalState;
  category?: string;
  limit?: number;
}

export async function fetchSignals(query: SignalsQuery): Promise<SignalsResponse> {
  const params = new URLSearchParams();
  params.set("signal", query.signal ?? "all");
  params.set("category", query.category ?? "all");
  params.set("conflict", query.conflict ?? "all");
  params.set("limit", String(query.limit ?? 200));

  const res = await fetch(`/api/signals?${params.toString()}`);
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `API error: ${res.status}`);
  }
  return (await res.json()) as SignalsResponse;
}

export async function fetchDashboard(query: DashboardQuery): Promise<DashboardResponse> {
  const params = new URLSearchParams();
  params.set("signal", query.signal ?? "all");
  params.set("category", query.category ?? "all");
  params.set("limit", String(query.limit ?? 50));

  const res = await fetch(`/api/dashboard?${params.toString()}`);
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `API error: ${res.status}`);
  }
  return (await res.json()) as DashboardResponse;
}

export async function fetchMarkets(): Promise<MarketsResponse> {
  const res = await fetch("/api/markets");
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `API error: ${res.status}`);
  }
  return (await res.json()) as MarketsResponse;
}

export async function fetchMarketDetail(
  marketId: string,
  range: "4W" | "12W" | "YTD" | "1Y" | "ALL",
): Promise<MarketDetailResponse> {
  const params = new URLSearchParams();
  params.set("market_id", marketId);
  params.set("range", range);
  const res = await fetch(`/api/market-detail?${params.toString()}`);
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || `API error: ${res.status}`);
  }
  return (await res.json()) as MarketDetailResponse;
}
