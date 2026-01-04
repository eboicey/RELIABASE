import { Routes, Route, Navigate } from "react-router-dom";
import { Shell } from "./layouts/Shell";
import Dashboard from "./pages/Dashboard";
import Assets from "./pages/Assets";
import Exposures from "./pages/Exposures";
import Events from "./pages/Events";
import FailureModes from "./pages/FailureModes";
import Parts from "./pages/Parts";
import EventDetails from "./pages/EventDetails";

function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/assets" element={<Assets />} />
        <Route path="/exposures" element={<Exposures />} />
        <Route path="/events" element={<Events />} />
        <Route path="/failure-modes" element={<FailureModes />} />
        <Route path="/event-details" element={<EventDetails />} />
        <Route path="/parts" element={<Parts />} />
      </Routes>
    </Shell>
  );
}

export default App;
