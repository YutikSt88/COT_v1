import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/app-shell";
import { DashboardPage } from "@/pages/dashboard-page";
import { MarketDetailPage } from "@/pages/market-detail-page";
import { SignalsPage } from "@/pages/signals-page";

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/market" element={<MarketDetailPage />} />
        <Route path="/signals" element={<SignalsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

export default App;
