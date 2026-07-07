"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchDocuments } from "@/lib/api";
import type { Citation, DocumentSummary } from "@/lib/types";
import DocumentPicker from "@/components/DocumentPicker";
import UploadZone from "@/components/UploadZone";
import ChatThread from "@/components/ChatThread";
import SpecimenRail from "@/components/SpecimenRail";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [scope, setScope] = useState<string | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const refreshDocuments = useCallback(() => {
    fetchDocuments().then(setDocuments).catch(() => {});
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  return (
    <main className="flex h-screen flex-col bg-ink">
      <header className="flex items-center justify-between border-b border-rule px-6 py-4">
        <div className="flex items-baseline gap-3">
          <h1 className="font-mono text-sm font-semibold tracking-[0.2em] text-parchment">
            EXCERPTA
          </h1>
          <span className="rule-label hidden sm:inline">
            local · hybrid retrieval · cited answers
          </span>
        </div>
        <DocumentPicker documents={documents} selected={scope} onSelect={setScope} />
      </header>

      <div className="grid flex-1 grid-cols-1 overflow-hidden md:grid-cols-[1fr_360px]">
        <section className="flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <ChatThread
              documentId={scope}
              hasDocuments={documents.length > 0}
              onCitations={(c, streaming) => {
                setCitations(c);
                setIsStreaming(streaming);
              }}
            />
          </div>
          <div className="border-t border-rule px-6 py-4">
            <UploadZone onIngested={refreshDocuments} />
          </div>
        </section>

        <div className="hidden md:block overflow-hidden">
          <SpecimenRail citations={citations} isStreaming={isStreaming} documents={documents} />
        </div>
      </div>
    </main>
  );
}
