/// <reference types="vite/client" />

export type TradeEventType =
  | "agent.dispatch"
  | "tool.invoke"
  | "tool.result"
  | "token.delta"
  | "plan.update"
  | "workflow.progress"
  | "memory.applied"
  | "context.compressed"
  | "model.fallback"
  | "cache.hit"
  | "task.queued"
  | "task.started"
  | "final.result"
  | "error";

export interface TradeEvent {
  type: TradeEventType;
  payload: Record<string, any>;
  occurred_at: string;
}

export interface SupplierCard {
  supplier_id: string;
  company_name: string;
  business_type: string;
  categories: string[];
  moq: number | null;
  unit_price: number | null;
  currency: string;
  incoterms: string[];
  lead_time_days: number | null;
  certifications: string[] | null;
  customization: string[] | null;
  reliability_score: number | null;
  source: string;
  score: number;
  hard_constraints_passed: boolean;
}

export interface FilteredSupplier {
  supplier_id: string;
  company_name?: string;
  reason_codes: string[];
  details?: Record<string, any>;
}

export interface RFQSummary {
  product: string;
  quantity: number;
  target_price?: number | null;
  currency: string;
  required_certifications: string[];
  max_lead_time_days?: number | null;
  customization: string[];
  missing_required_fields: string[];
}

export interface ShortlistItem {
  rank: number;
  supplier_id: string;
  company_name: string;
  final_score: number;
  hard_constraints_passed: boolean;
  unit_price: number | null;
  currency: string | null;
  effective_unit_cost: number | null;
  cost_is_partial: boolean;
  incoterm: string | null;
  lead_time_days: number | null;
  moq: number | null;
  strengths: string[];
  risks: string[];
  next_action: string;
  needs_human_approval: boolean;
  source: string;
}
