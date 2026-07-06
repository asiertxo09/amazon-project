import { Route, Routes } from "react-router-dom";
import { OpportunityProvider } from "./context/OpportunityContext";
import { OpportunityPicker } from "./components/OpportunityPicker";
import { Dashboard } from "./components/Dashboard";
import { PitchDeckView } from "./components/PitchDeckView";
import { TopBar } from "./components/ui/TopBar";

function App() {
  return (
    <OpportunityProvider>
      <div className="flex min-h-svh flex-col">
        <TopBar />
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<OpportunityPicker />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/pitch-deck" element={<PitchDeckView />} />
          </Routes>
        </main>
      </div>
    </OpportunityProvider>
  );
}

export default App;
