"use client";

import type { DocumentSummary } from "@/lib/types";

type Props = {
  documents: DocumentSummary[];
  selected: string | null;
  onSelect: (documentId: string | null) => void;
};

export default function DocumentPicker({ documents, selected, onSelect }: Props) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto py-1">
      <button
        onClick={() => onSelect(null)}
        className={`shrink-0 rounded-sm px-3 py-1.5 font-mono text-xs tracking-wide transition-colors ${
          selected === null
            ? "bg-brass text-ink"
            : "bg-panel2 text-muted hover:text-parchment"
        }`}
      >
        ALL DOCUMENTS
      </button>
      {documents.map((doc) => (
        <button
          key={doc.document_id}
          onClick={() => onSelect(doc.document_id)}
          title={doc.filename}
          className={`shrink-0 max-w-[180px] truncate rounded-sm px-3 py-1.5 font-mono text-xs tracking-wide transition-colors ${
            selected === doc.document_id
              ? "bg-brass text-ink"
              : "bg-panel2 text-muted hover:text-parchment"
          }`}
        >
          {doc.filename}
        </button>
      ))}
      {documents.length === 0 && (
        <span className="font-mono text-xs text-muted/70">
          no documents in the archive yet
        </span>
      )}
    </div>
  );
}
