"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, FileSearch } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { chatUrl } from "@/lib/api";
import type { ChatMessage, Citation } from "@/lib/types";

type Props = {
  documentId: string | null;
  hasDocuments: boolean;
  onCitations: (citations: Citation[], isStreaming: boolean) => void;
};

const NOT_FOUND_TEXT = "I could not find information regarding this in the uploaded document.";

export default function ChatThread({ documentId, hasDocuments, onCitations }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => () => esRef.current?.close(), []);

  const ask = (query: string) => {
    if (!query.trim() || streaming) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: query };
    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      citations: [],
      isStreaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setStreaming(true);
    onCitations([], true);

    const es = new EventSource(chatUrl(query, documentId));
    esRef.current = es;
    let finished = false;
    
    let currentCitations: Citation[] = [];

    es.addEventListener("citations", (e) => {
      const citations: Citation[] = JSON.parse(e.data);
      currentCitations = citations; 
      
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, citations } : m))
      );
      onCitations(citations, true);
    });

    es.addEventListener("token", (e) => {
      const { token } = JSON.parse(e.data);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: m.content + token,
                isNotFound: m.content + token === NOT_FOUND_TEXT,
              }
            : m
        )
      );
    });

    es.addEventListener("done", () => {
      finished = true;
      setStreaming(false);
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m)));
      onCitations(currentCitations, false);
      es.close();
    });

    es.onerror = () => {
      if (!finished) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, isStreaming: false, content: m.content || "Connection to the backend was lost." }
              : m
          )
        );
        setStreaming(false);
        onCitations([], false);
      }
      es.close();
    };
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="mx-auto max-w-md pt-16 text-center">
            <FileSearch size={28} className="mx-auto text-brassDim" />
            <p className="mt-4 font-serif text-lg text-parchment/90">
              Ask something. The answer will point back to the page it came from.
            </p>
            <p className="mt-2 rule-label">
              {hasDocuments ? "the archive is ready" : "add a document below to begin"}
            </p>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={`max-w-[85%] rounded-md px-4 py-3 ${
                m.role === "user"
                  ? "bg-panel2 font-mono text-[13px] text-parchment"
                  : m.isNotFound
                  ? "border border-danger/40 bg-danger/5 font-mono text-[13px] text-danger"
                  : "font-serif text-[15px] leading-relaxed text-parchment"
              }`}
            >
              {m.isNotFound && (
                <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-danger/80">
                  not found in record
                </div>
              )}
              
              {/* MARKDOWN RENDERER */}
              {m.role === "assistant" && !m.isNotFound ? (
                <div className="space-y-4 [&_strong]:font-semibold [&_strong]:text-white [&_em]:italic [&_code]:font-mono [&_code]:text-[13px] [&_code]:text-brass [&_code]:bg-brass/10 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-sm [&_a]:text-verdigris [&_a]:underline [&_a]:underline-offset-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5">
                  <ReactMarkdown>{m.content + (m.isStreaming ? " ▍" : "")}</ReactMarkdown>
                </div>
              ) : (
                <>
                  {m.content || (m.isStreaming ? "" : "…")}
                  {m.isStreaming && <span className="animate-blink text-brass ml-1">▍</span>}
                </>
              )}

              {m.role === "assistant" && !m.isNotFound && m.citations && m.citations.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-1.5 md:hidden">
                  {m.citations.map((c) => (
                    <span
                      key={c.id}
                      className="rounded-sm bg-brass/15 px-1.5 py-0.5 font-mono text-[10px] text-brass"
                    >
                      p.{c.page ?? "?"}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={scrollRef} />
      </div>

      <div className="border-t border-rule px-6 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="flex items-center gap-3"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming || !hasDocuments}
            placeholder={hasDocuments ? "Ask about the archive…" : "Add a document to begin asking questions"}
            className="flex-1 rounded-md border border-rule bg-panel2 px-4 py-3 font-serif text-[15px] text-parchment placeholder:text-muted focus:border-verdigris outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim() || !hasDocuments}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-brass text-ink transition-opacity disabled:opacity-30 cursor-pointer"
            aria-label="Send question"
          >
            <ArrowUp size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}