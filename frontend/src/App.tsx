import { BrowserRouter, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Analyze from "./pages/Analyze";
import AnalysisDetail from "./pages/AnalysisDetail";
import Compare from "./pages/Compare";
import History from "./pages/History";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <Navbar />
        <main className="mx-auto max-w-5xl px-4 py-8">
          <Routes>
            <Route path="/" element={<Analyze />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/history" element={<History />} />
            <Route path="/analysis/:id" element={<AnalysisDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
