"use client";

import { useEffect, useRef } from "react";
import type { ChatPanelMessage } from "@/lib/types";

interface ChatPanelProps {
  modelName: string;
  provider: string;
  messages: ChatPanelMessage[];
  isLoading: boolean;
  isSearchingRAG: boolean;
  isClassifying: boolean;
}

export default function ChatPanel({
  modelName,
  provider,
  messages,
  isLoading,
  isSearchingRAG,
  isClassifying,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-1 flex-col border-r border-gray-800 last:border-r-0 min-w-0">
      {/* Model header */}
      <div className="flex items-center gap-2 border-b border-gray-800 bg-gray-900/80 px-4 py-2.5">
        <div className="h-2 w-2 rounded-full bg-green-500" />
        <span className="text-sm font-semibold text-white truncate">
          {modelName}
        </span>
        <span className="ml-auto rounded-full bg-gray-800 px-2 py-0.5 text-[10px] font-medium text-gray-400 uppercase">
          {provider}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-600">
              Envía un mensaje para comenzar
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-md"
                  : "bg-gray-800 text-gray-200 rounded-bl-md"
              }`}
            >
              {msg.role === "assistant" && msg.used_rag && (
                <div className="mb-1.5 flex items-center gap-1 text-[10px] font-medium text-indigo-400">
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Respuesta con RAG
                </div>
              )}
              <div className="whitespace-pre-wrap break-words">
                {msg.content}
                {msg.isStreaming && (
                  <span className="inline-block ml-0.5 w-1.5 h-4 bg-indigo-400 animate-pulse" />
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Status indicators: classification, RAG search, loading */}
        {isLoading && (() => {
          const lastMsg = messages[messages.length - 1];
          const hasAssistantContent = lastMsg?.role === "assistant" && lastMsg.content;
          // Don't show indicators if assistant is already streaming content
          if (hasAssistantContent) return null;

          if (isClassifying) {
            return (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md border border-indigo-500/30 bg-indigo-950/40 px-4 py-3 text-sm text-indigo-300">
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Clasificando pregunta...
                  </span>
                </div>
              </div>
            );
          }

          if (isSearchingRAG) {
            return (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-sm text-amber-300">
                  <span className="flex items-center gap-2">
                    <svg className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    Buscando en documentos...
                  </span>
                </div>
              </div>
            );
          }

          // Default: bouncing dots while waiting
          return (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md bg-gray-800 px-4 py-3 text-sm text-gray-400">
                <span className="flex items-center gap-1.5">
                  <span className="flex gap-1">
                    <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce [animation-delay:0ms]" />
                    <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce [animation-delay:150ms]" />
                    <span className="h-2 w-2 rounded-full bg-gray-500 animate-bounce [animation-delay:300ms]" />
                  </span>
                </span>
              </div>
            </div>
          );
        })()}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
