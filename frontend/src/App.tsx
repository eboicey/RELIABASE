import { Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "./layouts/Shell";
import Dashboard from "./pages/Dashboard";
import AllAssets from "./pages/AllAssets";
import AssetDeepDive from "./pages/AssetDeepDive";
import Assets from "./pages/Assets";
import Exposures from "./pages/Exposures";
import Events from "./pages/Events";
import FailureModes from "./pages/FailureModes";
import Parts from "./pages/Parts";
import EventDetails from "./pages/EventDetails";
import Operations from "./pages/Operations";

function App() {
  return (
    <Shell>
      <Routes>
        {/* Analytics-first flow */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analytics" element={<AllAssets />} />
        <Route path="/analytics/asset/:assetId" element={<AssetDeepDive />} />

        {/* Configuration pages (admin) */}
        <Route path="/config/assets" element={<Assets />} />
        <Route path="/config/exposures" element={<Exposures />} />
        <Route path="/config/events" element={<Events />} />
        <Route path="/config/event-details" element={<EventDetails />} />
        <Route path="/config/failure-modes" element={<FailureModes />} />
        <Route path="/config/parts" element={<Parts />} />
        <Route path="/config/operations" element={<Operations />} />

        {/* Legacy redirects */}
        <Route path="/assets" element={<Navigate to="/config/assets" replace />} />
        <Route path="/exposures" element={<Navigate to="/config/exposures" replace />} />
        <Route path="/events" element={<Navigate to="/config/events" replace />} />
        <Route path="/event-details" element={<Navigate to="/config/event-details" replace />} />
        <Route path="/failure-modes" element={<Navigate to="/config/failure-modes" replace />} />
        <Route path="/parts" element={<Navigate to="/config/parts" replace />} />
        <Route path="/operations" element={<Navigate to="/config/operations" replace />} />
      </Routes>
    </Shell>
  );
}

export default App;
