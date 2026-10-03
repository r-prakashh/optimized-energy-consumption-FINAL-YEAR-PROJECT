import { useEffect, useRef, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { fetchAssistantStatus, sendChat, type ChatMessage } from "../api/client";
import { useInsights } from "../context/InsightsContext";
import { VoltMascot } from "./VoltMascot";

const STORAGE_KEY = "wattwise.chat.v1";
const GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Hi, I'm **Volt** ⚡ your WattWise assistant. Ask me about your bills, what a new appliance would cost to run, TNEB slabs, or how to save energy.",
};
const SUGGESTIONS = [
  "What if I add a 1.5 ton 5-star inverter AC for 8 hours?",
  "How much will 320 units cost?",
  "How do I upload my old bills?",
  "Give me tips to cut my bill this summer",
];

function renderInline(text: string) {
  // Minimal formatting: **bold** and line breaks; everything else is text.
  return text
    .split("\n")
    .map((line, i) => (
      <p key={i}>
        {line
          .split(/(\*\*[^*]+\*\*)/g)
          .map((part, j) =>
            part.startsWith("**") && part.endsWith("**") ? (
              <strong key={j}>{part.slice(2, -2)}</strong>
            ) : (
              part
            ),
          )}
      </p>
    ));
}

function loadHistory(): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return [GREETING];
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [llm, setLlm] = useState<boolean | null>(null);
  const [nudge, setNudge] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { analysis } = useInsights();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-30)));
    } catch {
      /* ignore */
    }
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => {
    if (open && llm === null) {
      fetchAssistantStatus()
        .then((s) => setLlm(s.llm_enabled))
        .catch(() => setLlm(false));
    }
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [open, llm]);

  useEffect(() => {
    const t = setTimeout(() => setNudge(false), 9000);
    return () => clearTimeout(t);
  }, []);

  function buildContext(): Record<string, unknown> {
    const ctx: Record<string, unknown> = { current_page: location.pathname };
    if (analysis) {
      ctx.bill_analysis = {
        avg_monthly_kwh: analysis.avg_monthly_kwh,
        avg_monthly_cost: analysis.avg_monthly_cost,
        trend_direction: analysis.trend_direction,
        trend_pct_per_month: analysis.trend_pct_per_month,
        baseload_kwh_per_day: analysis.baseload_kwh_per_day,
        peak_month: analysis.peak_month,
        anomalies: analysis.history.filter((h) => h.is_anomaly).map((h) => h.label),
        history: analysis.history.slice(-12).map((h) => ({ month: h.label, kwh: h.kwh })),
        forecast: analysis.forecast,
        optimal_target: analysis.optimal_target,
        forecast_model: analysis.model_used,
      };
    }
    return ctx;
  }

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user" as const, content }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      // Drop the canned greeting; the API expects the first turn to be the user's.
      let history = next.slice(-16);
      while (history.length && history[0].role === "assistant") history = history.slice(1);
      const res = await sendChat(history, buildContext());
      setMessages([...next, { role: "assistant", content: res.reply }]);
    } catch {
      setMessages([
        ...next,
        {
          role: "assistant",
          content: "I couldn't reach the WattWise server just now. Is the backend running?",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  function reset() {
    setMessages([GREETING]);
  }

  const showSuggestions = messages.length <= 1 && !busy;

  return (
    <>
      {!open && nudge && (
        <button
          className="volt-nudge"
          onClick={() => {
            setNudge(false);
            setOpen(true);
          }}
        >
          Need help? Ask Volt!
        </button>
      )}

      <button
        className={`volt-launcher ${open ? "open" : ""}`}
        onClick={() => {
          setNudge(false);
          setOpen((v) => !v);
        }}
        aria-label={open ? "Close assistant" : "Open Volt assistant"}
      >
        {open ? <span className="volt-close">×</span> : <VoltMascot size={58} wave={nudge} />}
      </button>

      {open && (
        <div className="volt-panel" role="dialog" aria-label="Volt assistant">
          <header className="volt-head">
            <VoltMascot size={44} mood={busy ? "thinking" : "happy"} />
            <div className="volt-head-text">
              <strong>Volt</strong>
              <span>
                {busy ? "thinking…" : llm ? "AI energy assistant · online" : "Energy assistant · online"}
              </span>
            </div>
            <button className="volt-reset" onClick={reset} title="Start a new chat">
              New chat
            </button>
          </header>

          <div className="volt-messages" ref={listRef}>
            {messages.map((m, i) => (
              <div key={i} className={`volt-msg ${m.role}`}>
                {m.role === "assistant" && <VoltMascot size={26} className="volt-msg-avatar" />}
                <div className="volt-bubble">{renderInline(m.content)}</div>
              </div>
            ))}
            {busy && (
              <div className="volt-msg assistant">
                <VoltMascot size={26} mood="thinking" className="volt-msg-avatar" />
                <div className="volt-bubble volt-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
            {showSuggestions && (
              <div className="volt-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
                {!analysis && (
                  <button
                    className="volt-cta"
                    onClick={() => {
                      setOpen(false);
                      navigate("/bills");
                    }}
                  >
                    📄 Upload my bills for personal advice
                  </button>
                )}
              </div>
            )}
          </div>

          <form className="volt-input" onSubmit={onSubmit}>
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              placeholder="Ask Volt about bills, appliances…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              maxLength={1500}
            />
            <button type="submit" className="primary" disabled={busy || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}
