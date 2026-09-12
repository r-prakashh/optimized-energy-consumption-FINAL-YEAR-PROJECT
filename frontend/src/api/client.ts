import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const api = axios.create({ baseURL: API_BASE_URL });

export interface ApplianceCatalogEntry {
  category: string;
  label: string;
  avg_watts: number;
  flexibility: "none" | "low" | "medium" | "high";
  min_hours: number;
  max_hours: number;
}

export interface ApplianceInput {
  category: string;
  hours_per_day: number;
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
