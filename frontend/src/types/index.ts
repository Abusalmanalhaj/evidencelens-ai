export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  sector: string | null;
  stage: string | null;
  analysis_status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: number;
  project_id: number;
  filename: string;
  file_size: number;
  mime_type: string;
  page_count: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface Evidence {
  id: number;
  text: string;
  evidence_type: string;
  source_page: number | null;
  is_relevant: boolean | null;
  human_marked_relevant: boolean | null;
  created_at: string;
}

export interface Assessment {
  id: number;
  support_score: number;
  support_level: string;
  evidence_strength: number;
  source_traceability: number;
  evidence_pages: number[] | null;
  source_page_verified: boolean;
  verification_status: string;
  evidence_relevance: number;
  evidence_sufficiency: number;
  specificity: number;
  contradictory_penalty: number;
  missing_info_penalty: number;
  explanation: string;
  ai_explanation: string | null;
  human_override_score: number | null;
}

export interface Claim {
  id: number;
  project_id: number;
  text: string;
  category: string;
  source_page: number | null;
  source_pages: number[] | null;
  claim_basis: string | null;
  claim_kind: string | null;
  ai_category: string | null;
  human_category: string | null;
  requires_review: boolean;
  evidence_items: Evidence[];
  assessment: Assessment | null;
  created_at: string;
}

export interface DashboardMetrics {
  total_claims: number;
  support_breakdown: {
    strong: number;
    partial: number;
    weak: number;
    missing: number;
  };
  evidence_coverage: number;
  category_breakdown: { category: string; count: number }[];
  requires_review_count: number;
  analysis_status: string;
  last_run_status: string | null;
}

export interface AnalysisStatus {
  project_id: number;
  analysis_status: string;
  current_run: {
    id: number;
    status: string;
    model_name: string | null;
    claims_extracted: number;
    error_message: string | null;
  } | null;
  llm_enabled: boolean;
}
