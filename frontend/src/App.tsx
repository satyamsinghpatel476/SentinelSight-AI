import { Route, Routes } from "react-router-dom";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { AppShell } from "./layouts/AppShell";
import { AddWebsitePage } from "./pages/AddWebsitePage";
import { AISettingsPage } from "./pages/AISettingsPage";
import { AuditPage } from "./pages/AuditPage";
import { FoundationPage } from "./pages/FoundationPage";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { IncidentsPage } from "./pages/IncidentsPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ScanDetailPage } from "./pages/ScanDetailPage";
import { WebsiteAssetsPage } from "./pages/WebsiteAssetsPage";
import { WebsiteDetailPage } from "./pages/WebsiteDetailPage";

export function App() {
  return (
    <AppShell>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<FoundationPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/websites" element={<WebsiteAssetsPage />} />
          <Route path="/websites/new" element={<AddWebsitePage />} />
          <Route path="/websites/:websiteId" element={<WebsiteDetailPage />} />
          <Route path="/scans/:scanId" element={<ScanDetailPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/settings/ai" element={<AISettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ErrorBoundary>
    </AppShell>
  );
}
