"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { uploadDocument, pollJobStatus } from "@/lib/api";

type Props = {
  onIngested: () => void;
};

type UploadState =
  | { phase: "idle" }
  | { phase: "uploading"; filename: string }
  | { phase: "processing"; filename: string; status: string }
  | { phase: "done"; filename: string }
  | { phase: "error"; filename: string; message: string };

export default function UploadZone({ onIngested }: Props) {
  const [state, setState] = useState<UploadState>({ phase: "idle" });
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (file.type !== "application/pdf") {
        setState({ phase: "error", filename: file.name, message: "Only PDF files can be added to the archive." });
        return;
      }
      setState({ phase: "uploading", filename: file.name });
      try {
        const { job_id } = await uploadDocument(file);
        setState({ phase: "processing", filename: file.name, status: "Processing" });
        pollJobStatus(job_id, (job) => {
          if (job.status === "Complete") {
            setState({ phase: "done", filename: file.name });
            onIngested();
            setTimeout(() => setState({ phase: "idle" }), 2200);
          } else if (job.status.startsWith("Failed")) {
            setState({ phase: "error", filename: file.name, message: job.status.replace("Failed: ", "") });
          } else {
            setState({ phase: "processing", filename: file.name, status: job.status });
          }
        });
      } catch (err) {
        setState({
          phase: "error",
          filename: file.name,
          message: err instanceof Error ? err.message : "Upload failed.",
        });
      }
    },
    [onIngested]
  );

  const busy = state.phase === "uploading" || state.phase === "processing";

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!busy) setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        if (!busy && e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
      }}
      onClick={() => !busy && inputRef.current?.click()}
      className={`rounded-md border border-dashed p-4 transition-colors cursor-pointer ${
        dragActive ? "border-brass bg-brass/5" : "border-rule hover:border-brassDim"
      } ${busy ? "cursor-default" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      {state.phase === "idle" && (
        <div className="flex items-center gap-3 text-muted">
          <UploadCloud size={18} className="text-brassDim" />
          <span className="font-mono text-xs tracking-wide">
            Drop a PDF here, or click to add it to the archive
          </span>
        </div>
      )}

      {(state.phase === "uploading" || state.phase === "processing") && (
        <div className="flex items-center gap-3">
          <Loader2 size={18} className="animate-spin text-verdigris" />
          <span className="font-mono text-xs text-parchment truncate">{state.filename}</span>
          <span className="rule-label">
            {state.phase === "uploading" ? "sending…" : (state as any).status}
          </span>
        </div>
      )}

      {state.phase === "done" && (
        <div className="flex items-center gap-3">
          <CheckCircle2 size={18} className="text-verdigris" />
          <span className="font-mono text-xs text-parchment truncate">{state.filename}</span>
          <span className="rule-label text-verdigris">indexed</span>
        </div>
      )}

      {state.phase === "error" && (
        <div className="flex items-center gap-3">
          <XCircle size={18} className="text-danger shrink-0" />
          <span className="font-mono text-xs text-danger">{state.message}</span>
        </div>
      )}
    </div>
  );
}
