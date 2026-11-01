export type Overview = {
  summary: {
    candidates: number;
    messages: number;
    pending_approvals: number;
    open_tickets: number;
  };
  top_cards: Array<{ title: string; value: string; trend: string }>;
};

export type MessageRow = {
  id: string;
  sender: string;
  subject: string;
  body?: string;
  priority: string;
  category: string;
  department?: string | null;
  intent: string;
  destination: string;
  confidence: number;
};

export type CandidateRow = {
  id: string;
  full_name: string;
  email: string;
  score: number;
};

export type ApprovalRow = {
  id: number;
  action: string;
  status: string;
  required_role: string;
  payload: Record<string, unknown>;
  requested_by?: string;
  expires_at?: string | null;
  draft?: {
    recipient: string;
    subject: string;
    body: string;
    status: string;
  } | null;
};

export type DigestRow = {
  period: string;
  html: string;
};

export type AuditResult = {
  valid: boolean;
  count: number;
  broken_at?: number;
};

export type SupportAnswer = {
  answer: string;
  sources: string[];
  answerable: boolean;
  escalated: boolean;
  ticket_id?: number | null;
};

export type TicketRow = {
  id: number;
  subject: string;
  body: string;
  status: string;
  assigned_to: string | null;
  employee_id: number;
  employee_name: string;
  employee_email: string;
};

export type WorkflowIntakeResponse = {
  request_id: string;
  execution_id: string | null;
  message_id: string;
  status: string;
  duplicate: boolean;
  classification: {
    category: string;
    intent: string;
    priority: string;
    destination: string;
    confidence: number;
    reason: string;
    source: string;
    department?: string | null;
  };
};
