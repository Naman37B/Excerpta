"use client";

import type { Citation, DocumentSummary } from "@/lib/types";

type Props = {
  citations: Citation[];
  isStreaming: boolean;
  documents: DocumentSummary[];
};

function filenameFor(documents: DocumentSummary[], documentId: string | null): string {
  if (!documentId) return "unknown source";
  return documents.find((d) => d.document_id === documentId)?.filename ?? documentId.slice(0, 8);
}

export default function SpecimenRail({ citations, isStreaming, documents }: Props) {
  return (
    <aside className="flex h-full w-full flex-col border-l border-rule bg-panel">
      <div className="border-b border-rule px-5 py-4">
        <h2 className="rule-label">Specimen rail</h2>
        <p className="mt-1 text-[13px] text-muted">
          Every answer is built only from what's pinned here.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
        {citations.length === 0 && !isStreaming && (
          <div className="mt-10 text-center">
            <p className="font-mono text-xs text-muted/70">
              nothing pinned yet — ask a question
            </p>
          </div>
        )}

        {citations.map((c, i) => (
          <div
            key={c.id}
            style={{ animationDelay: `${i * 70}ms` }}
            className={`animate-fadeUp relative rounded-b-sm bg-panel2 pt-4 pb-4 px-4 specimen-card ${
              isStreaming ? "animate-glowPulse" : ""
            }`}
          >
            <span className="specimen-tag">
              p.{c.page ?? "?"}
            </span>
            <p className="font-serif text-[13px] leading-relaxed text-parchment/90 line-clamp-4">
              {c.snippet.replace(/^.*?\n\n/s, "")}
            </p>
            <div className="mt-3 flex items-center justify-between border-t border-rule/70 pt-2">
              <span className="rule-label truncate max-w-[60%]" title={filenameFor(documents, c.document_id)}>
                {filenameFor(documents, c.document_id)}
              </span>
              <span className="font-mono text-[11px] text-brass">#{c.id.slice(-6)}</span>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
