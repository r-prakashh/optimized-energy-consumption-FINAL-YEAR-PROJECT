import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const api = axios.create({ baseURL: API_BASE_URL });

export interface SpecFieldSchema {
  key: string;
  label: string;
  type: "select" | "boolean";
  options: (string | number)[];
  default: string | number | boolean;
  unit: string;
}

export interface ApplianceCatalogEntry {
  category: string;
  label: string;
  avg_watts: number;
  flexibility: "none" | "low" | "medium" | "high";
  min_hours: number;
  max_hours: number;
  shiftable: boolean;
  specs: SpecFieldSchema[];
}

export type ApplianceSpecs = Record<string, string | number | boolean>;

export interface ApplianceInput {
  category: string;
  hours_per_day: number;
  specs: ApplianceSpecs;
}

export interface PlanRequest {
  budget: number;
  duration_days: number;
  appliances: ApplianceInput[];
}

export interface ApplianceResult {
  category: string;
  label: string;
  original_hours: number;
  recommended_hours: number;
  daily_kwh: number;
  reduced: boolean;
}

export interface TodShiftOpportunity {
  category: string;
  label: string;
  daily_kwh: number;
  estimated_saving_per_day: number;
}

export interface PlanResponse {
  projected_daily_kwh: number;
  projected_total_kwh: number;
  projected_cost: number;
  original_cost: number;
  budget: number;
  budget_met: boolean;
  duration_days: number;
  appliances: ApplianceResult[];
  forecast_daily_kwh: number[];
  tod_shift_opportunities: TodShiftOpportunity[];
  tod_total_saving_for_period: number;
  action_plan: string[];
}

export async function fetchApplianceCatalog(): Promise<ApplianceCatalogEntry[]> {
  const res = await api.get<ApplianceCatalogEntry[]>("/appliances");
  return res.data;
}

export async function createPlan(payload: PlanRequest): Promise<PlanResponse> {
  const res = await api.post<PlanResponse>("/plan", payload);
  return res.data;
}

export async function whatIf(payload: PlanRequest): Promise<PlanResponse> {
  const res = await api.post<PlanResponse>("/what-if", payload);
  return res.data;
}

// ---------------------------------------------------------------- bills / OCR

export interface ParsedReading {
  period_end: string | null;
  period_days: number;
  units_kwh: number | null;
  amount_inr: number | null;
  previous_reading: number | null;
  current_reading: number | null;
  confidence: number;
  source: string;
  notes: string[];
}

export interface BillUploadResult {
  filename: string;
  method: string;
  ocr_confidence: number | null;
  readings: ParsedReading[];
  raw_text_preview: string;
  error: string | null;
}

export interface BillUploadResponse {
  files: BillUploadResult[];
  ai_vision_used: boolean;
}

export interface BillReadingInput {
  period_end: string;
  period_days: number;
  units_kwh: number;
  amount_inr: number | null;
}

export interface MonthPoint {
  label: string;
  month: number;
  year: number;
  kwh: number;
  daily_kwh: number;
  amount_inr: number | null;
  estimated_cost: number;
  is_anomaly: boolean;
  anomaly_score: number;
}

export interface ForecastPoint {
  label: string;
  month: number;
  year: number;
  kwh: number;
  lower: number;
  upper: number;
  estimated_cost: number;
}

export interface AdviceCard {
  kind: "ok" | "warn" | "info";
  title: string;
  body: string;
}

export interface OptimalTarget {
  target_monthly_kwh: number;
  target_daily_kwh: number;
  current_monthly_kwh: number;
  monthly_saving_inr: number;
  reason: string;
}

export interface BillAnalysis {
  history: MonthPoint[];
  forecast: ForecastPoint[];
  model_used: string;
  model_scores: Record<string, number>;
  trend_pct_per_month: number;
  trend_direction: "rising" | "falling" | "stable";
  avg_monthly_kwh: number;
  avg_monthly_cost: number;
  baseload_kwh_per_day: number;
  peak_month: string;
  low_month: string;
  billing_cycle_days: number;
  advice: AdviceCard[];
  optimal_target: OptimalTarget;
  notes: string[];
}

export async function uploadBills(files: File[]): Promise<BillUploadResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await api.post<BillUploadResponse>("/bills/upload", form, { timeout: 120_000 });
  return res.data;
}

export async function analyzeBills(readings: BillReadingInput[], horizonMonths = 3): Promise<BillAnalysis> {
  const res = await api.post<BillAnalysis>("/bills/analyze", { readings, horizon_months: horizonMonths });
  return res.data;
}

// ------------------------------------------------------------------ scenario

export interface ApplianceChangeInput {
  action: "add" | "remove";
  category: string;
  quantity: number;
  hours_per_day: number;
  specs: ApplianceSpecs;
}

export interface ScenarioRequest {
  changes: ApplianceChangeInput[];
  baseline_monthly_kwh?: number | null;
  baseline_months?: [string, number][] | null;
}

export interface ScenarioResponse {
  baseline_monthly_kwh: number;
  new_monthly_kwh: number;
  baseline_monthly_cost: number;
  new_monthly_cost: number;
  delta_monthly_kwh: number;
  delta_monthly_cost: number;
  delta_pct: number;
  changes: {
    action: string;
    category: string;
    label: string;
    quantity: number;
    hours_per_day: number;
    daily_kwh: number;
    monthly_kwh: number;
  }[];
  months: { label: string; baseline_kwh: number; new_kwh: number; baseline_cost: number; new_cost: number }[];
  verdict: string;
  tips: string[];
}

export async function runScenario(payload: ScenarioRequest): Promise<ScenarioResponse> {
  const res = await api.post<ScenarioResponse>("/scenario", payload);
  return res.data;
}

// ----------------------------------------------------------------- assistant

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  engine: "claude" | "offline";
  tools_used: string[];
}

export async function sendChat(messages: ChatMessage[], context: Record<string, unknown>): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/chat", { messages, context }, { timeout: 120_000 });
  return res.data;
}

export async function fetchAssistantStatus(): Promise<{ llm_enabled: boolean }> {
  const res = await api.get<{ llm_enabled: boolean }>("/assistant/status");
  return res.data;
}
