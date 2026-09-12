import { useState } from "react";
import { Link } from "react-router-dom";
import { ApplianceIcon } from "../components/ApplianceIcons";

const STATS = [
  { value: "5", label: "REFIT houses trained on" },
  { value: "2,704", label: "house-days of real data" },
  { value: "23.3%", label: "WMAPE forecast accuracy" },
  { value: "8", label: "appliance categories" },
];

const STEPS = [
  {
    n: "01",
    title: "Forecast",
    body: "A LightGBM model trained on REFIT household data learns your weekday, weekend, and seasonal consumption patterns to project the days ahead.",
  },
  {
    n: "02",
    title: "Estimate",
    body: "Appliance-level energy is estimated from your selected devices and usage hours, then converted into a projected electricity bill using slab-based tariffs.",
  },
  {
    n: "03",
    title: "Optimize",
    body: "If the projection exceeds your budget, a transparent rule-based optimizer trims hours on your most flexible, highest-draw appliances first — never touching essentials.",
  },
];

const APPLIANCES = [
  "air_conditioner",
  "fan",
  "television",
  "lighting",
  "refrigerator",
  "washing_machine",
  "computer",
  "microwave",
];

const FAQS = [
  {
    q: "Is this connected to a real smart meter?",
    a: "No — this is a software forecasting and planning platform, not a hardware metering system. It estimates consumption from historical patterns and your own appliance inputs, not live sensor readings.",
  },
  {
    q: "How accurate are the cost estimates?",
    a: "They're approximate, grounded in REFIT-trained forecasting and nameplate appliance ratings — intended for proactive planning, not meter-accurate billing reconciliation.",
  },
  {
    q: "What dataset powers the forecasting model?",
    a: "The REFIT Electrical Load Measurements dataset — two years of real household energy data across 20 UK homes, at whole-house and appliance level.",
  },
  {
    q: "Why rule-based optimization instead of reinforcement learning?",
    a: "Every recommendation needs to be explainable to a household — traceable to appliance flexibility, consumption share, and remaining budget gap. A transparent greedy optimizer gives that; a black-box RL agent doesn't.",
  },
];

export function Home() {
  return (
    <>
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-content">
          <span className="eyebrow">AI-based household energy planning</span>
          <h1>
            Forecast your energy.
            <br />
            Optimize your <em>budget</em>.
          </h1>
          <p className="hero-sub">
            WattWise predicts your household electricity consumption, estimates
            what it will cost, and builds a personalized appliance schedule
            that keeps you inside the budget you set — all grounded in real
            REFIT household data.
          </p>
          <div className="hero-actions">
            <Link to="/plan" className="btn-primary">
              Launch the Planner
            </Link>
            <Link to="/methodology" className="btn-ghost">
              How it works
            </Link>
          </div>
        </div>
      </section>

      <section className="stats-bar">
        {STATS.map((s) => (
          <div className="stat-item" key={s.label}>
            <div className="stat-item-value">{s.value}</div>
            <div className="stat-item-label">{s.label}</div>
          </div>
        ))}
      </section>

      <section className="section">
        <div className="section-head">
          <span className="eyebrow">The pipeline</span>
          <h2>
            From data to decision <em>in three steps</em>
          </h2>
        </div>
        <div className="steps-grid">
          {STEPS.map((step) => (
            <div className="step-card" key={step.n}>
              <span className="step-n">{step.n}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <span className="eyebrow">Supported appliances</span>
          <h2>
            Built around <em>how you actually live</em>
          </h2>
        </div>
        <div className="appliance-showcase">
          {APPLIANCES.map((category) => (
            <div className="showcase-card" key={category}>
              <ApplianceIcon category={category} />
              <span>{category.replace(/_/g, " ")}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <span className="eyebrow">FAQ</span>
          <h2>
            Frequently asked <em>questions</em>
          </h2>
        </div>
        <div className="faq-list">
          {FAQS.map((item) => (
            <FaqItem key={item.q} q={item.q} a={item.a} />
          ))}
        </div>
      </section>

      <section className="cta-band">
        <h2>
          Ready to plan your <em>next billing cycle</em>?
        </h2>
        <p>Set a budget, pick your appliances, and see your personalized plan.</p>
        <Link to="/plan" className="btn-primary">
          Launch the Planner
        </Link>
      </section>
    </>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`faq-item ${open ? "open" : ""}`}>
      <button className="faq-question" onClick={() => setOpen((v) => !v)}>
        {q}
        <span className="faq-toggle">{open ? "−" : "+"}</span>
      </button>
      {open && <p className="faq-answer">{a}</p>}
    </div>
  );
}
