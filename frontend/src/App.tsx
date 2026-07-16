import { Route, Routes } from "react-router-dom";

import { AppShell } from "./layouts/AppShell";
import { AddWebsitePage } from "./pages/AddWebsitePage";
import { FoundationPage } from "./pages/FoundationPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ScanDetailPage } from "./pages/ScanDetailPage";
import { WebsiteAssetsPage } from "./pages/WebsiteAssetsPage";
import { WebsiteDetailPage } from "./pages/WebsiteDetailPage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<FoundationPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/websites" element={<WebsiteAssetsPage />} />
        <Route path="/websites/new" element={<AddWebsitePage />} />
        <Route path="/websites/:websiteId" element={<WebsiteDetailPage />} />
        <Route path="/scans/:scanId" element={<ScanDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}
