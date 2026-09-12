import { NavLink } from "react-router-dom";

export function Navbar() {
  return (
    <header className="site-nav">
      <div className="site-nav-inner">
        <NavLink to="/" className="brand">
          <span className="brand-mark" />
          WattWise
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Home
          </NavLink>
          <NavLink to="/methodology" className={({ isActive }) => (isActive ? "active" : "")}>
            Methodology
          </NavLink>
          <NavLink to="/plan" className="nav-cta">
            Launch Planner
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
