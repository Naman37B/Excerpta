export type DocumentSummary = {
  document_id: string;
  filename: string;
};

export type JobStatus = {
  job_id: string;
  document_id: string;
  filename: string;
  status: string;
};

export type Citation = {
  id: string;
  page: number | null;
  document_id: string | null;
  snippet: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  isNotFound?: boolean;
};
