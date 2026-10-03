import { Route, Routes, useLocation } from "react-router-dom";
import { useEffect } from "react";
import "./App.css";
import "./insights.css";
import { Navbar } from "./components/Navbar";
import { Footer } from "./components/Footer";
import { Home } from "./pages/Home";
import { Plan } from "./pages/Plan";
import { Methodology } from "./pages/Methodology";
import { Bills } from "./pages/Bills";
import { Simulator } from "./pages/Simulator";
import { ChatWidget } from "./components/ChatWidget";
import { InsightsProvider } from "./context/InsightsContext";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function App() {
  return (
    <InsightsProvider>
      <div className="site">
        <ScrollToTop />
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/bills" element={<Bills />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/methodology" element={<Methodology />} />
        </Routes>
        <Footer />
        <ChatWidget />
      </div>
    </InsightsProvider>
  );
}

export default App;
