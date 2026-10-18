// Project
export interface ProjectResponse {
  id: number;
  name: string;
  status: string;
  file_count?: number;
  created_at: string;
  updated_at?: string;
}

// File within a project
export interface ProjectFile {
  id: number;
  file_path: string;
  status: string;
}

// Slither analysis detection (matches backend DetectionResponse)
export interface SlitherDetection {
  id: number;
  analysis_result_id: number;
  detection_ref: string;
  check_name: string;
  description: string;
  impact?: string;
  confidence?: string;
}

// Fuzz result (matches backend FuzzResultResponse)
export interface FuzzResult {
  id: number;
  failures_count: number;
  raw_output?: string;
  created_at?: string;
}

// LLM Audit finding
export interface AuditFinding {
  id: number;
  contract_name: string;
  function_name?: string;
  vulnerability_description: string;
  severity: string;
  suggested_fix?: string;
  gas_optimization?: string;
  created_at: string;
}

// LLM audit trigger response
export interface AuditTriggerResponse {
  status: string;
  project_id: number;
  task_id: string;
}

// Audit run (one LLM audit execution; full or incremental)
export interface AuditRunSummary {
  id: number;
  status: string;
  mode: string;
  files_total: number;
  functions_extracted: number;
  functions_audited: number;
  functions_skipped: number;
  functions_failed: number;
  functions_filtered: number;
  functions_unchanged: number;
  findings: number;
  model?: string | null;
  prompt_version?: string | null;
  kb_version?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface IncrementalPlanFile {
  file: string;
  changed: string[];
  unchanged: string[];
  whole_file: boolean;
  hunks: number;
}

export interface AuditUnit {
  file: string;
  function: string;
  line: number;
  status: string;
  reason: string | null;
  findings: number;
  rag_hits: number;
}

export interface AuditRunDetail extends AuditRunSummary {
  incremental?: {
    files: IncrementalPlanFile[];
    missing: string[];
    changed_total: number;
    unchanged_total: number;
  } | null;
  units: AuditUnit[];
}

export interface CompareFinding {
  contract: string;
  function: string;
  severity: string;
}

export interface CompareResult {
  base: { run_id: number; status: string; functions_audited: number; findings: number };
  head: { run_id: number; status: string; functions_audited: number; findings: number };
  added: CompareFinding[];
  removed: CompareFinding[];
  persisted: CompareFinding[];
  counts: { added: number; removed: number; persisted: number };
}

// Vulnerability from SWC knowledge base
export interface VulnerabilityEntry {
  id: number;
  swc_id: string;
  title: string;
  description: string;
  severity: string;
  code_example?: string;
}

// Report
export interface ReportResponse {
  id: number;
  project_id: number;
  format: string;
  status: string;
  created_at: string;
}

// Report