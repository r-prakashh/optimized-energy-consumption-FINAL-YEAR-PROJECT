import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="footer-brand">
          <span className="brand-mark" />
          <div>
            <div className="footer-title">WattWise</div>
            <div className="footer-sub">
              AI-based personalized energy forecasting &amp; cost optimization.
            </div>
          </div>
        </div>
        <div className="footer-links">
          <Link to="/">Home</Link>
          <Link to="/methodology">Methodology</Link>
          <Link to="/plan">Planner</Link>
          <Link to="/bills">Bill Insights</Link>
          <Link to="/simulator">What-If</Link>
        </div>
      </div>
      <div className="footer-bottom">
        Built on the REFIT Electrical Load Measurements dataset. Estimates are
        approximate, not meter-accurate billing.
      </div>
    </footer>
  );
}
