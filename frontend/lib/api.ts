import type { DocumentSummary, JobStatus } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${API_URL}/documents`);
  if (!res.ok) throw new Error("Could not reach the backend for the document list.");
  return res.json();
}

export async function uploadDocument(file: File): Promise<{ job_id: string; document_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Upload failed." }));
    throw new Error(body.detail || "Upload failed.");
  }
  return res.json();
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_URL}/status/${jobId}`);
  if (!res.ok) throw new Error("Could not check ingestion status.");
  return res.json();
}

/** Polls a job until it reaches "Complete" or a "Failed: ..." status. */
export function pollJobStatus(
  jobId: string,
  onUpdate: (status: JobStatus) => void,
  intervalMs = 1500
): () => void {
  let cancelled = false;
  const tick = async () => {
    if (cancelled) return;
    try {
      const status = await fetchJobStatus(jobId);
      onUpdate(status);
      if (!cancelled && status.status !== "Complete" && !status.status.startsWith("Failed")) {
        setTimeout(tick, intervalMs);
      }
    } catch {
      if (!cancelled) setTimeout(tick, intervalMs);
    }
  };
  tick();
  return () => {
    cancelled = true;
  };
}

export function chatUrl(query: string, documentId: string | null): string {
  const params = new URLSearchParams({ query });
  if (documentId) params.set("document_id", documentId);
  return `${API_URL}/chat?${params.toString()}`;
}
