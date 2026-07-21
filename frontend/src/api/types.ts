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