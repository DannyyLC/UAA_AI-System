"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  createConversation,
  getModels,
  sendMessageStream,
} from "@/lib/api";
import type { ChatPanelMessage, LLMModel } from "@/lib/types";
import Sidebar from "@/components/Sidebar";
import ChatPanel from "@/components/ChatPanel";

interface ModelChatState {
  model: LLMModel;
  conversationId: string | null;
  messages: ChatPanelMessage[];
  isLoading: boolean;
  isSearchingRAG: boolean;
  isClassifying: boolean;
}

export default function ChatPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const [chatStates, setChatStates] = useState<ModelChatState[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Redirect if not logged in
  useEffect(() => {
    if (!loading && !user) router.replace("/");
  }, [user, loading, router]);

  // Load models
  useEffect(() => {
    if (!user) return;
    getModels()
      .then((m) => {
        setChatStates(
          m.map((model) => ({
            model,
            conversationId: null,
            messages: [],
            isLoading: false,
            isSearchingRAG: false,
            isClassifying: false,
          }))
        );
      })
      .catch(console.error);
  }, [user]);

  const handleLogout = async () => {
    await logout();
    router.replace("/");
  };

  // Helper to update a specific model's state
  const updateModelState = useCallback(
    (idx: number, updater: (prev: ModelChatState) => ModelChatState) => {
      setChatStates((prev) =>
        prev.map((s, i) => (i === idx ? updater(s) : s))
      );
    },
    []
  );

  // Send prompt to all 3 models in parallel
  const handleSend = async () => {
    const content = input.trim();
    if (!content || sending) return;

    setInput("");
    setSending(true);

    // Add user message to all panels
    const userMsg: ChatPanelMessage = { role: "user", content };

    setChatStates((prev) =>
      prev.map((s) => ({
        ...s,
        messages: [...s.messages, userMsg],
        isLoading: true,
        isSearchingRAG: false,
        isClassifying: false,
      }))
    );

    // For each model, ensure we have a conversation, then stream
    const promises = chatStates.map(async (state, idx) => {
      try {
        // Create conversation if needed
        let convId = state.conversationId;
        if (!convId) {
          const res = await createConversation({
            title: content.slice(0, 60),
          });
          convId = res.conversation.id;
          updateModelState(idx, (s) => ({
            ...s,
            conversationId: convId,
          }));
        }

        // Stream the response (assistant message will be created on first token)
        const stream = sendMessageStream(convId!, { content, model: state.model.id });
        
        for await (const chunk of stream) {
          if (chunk.type === "token") {
            updateModelState(idx, (s) => {
              const msgs = [...s.messages];
              const last = msgs[msgs.length - 1];
              // If there's already an assistant message, append to it
              if (last && last.role === "assistant") {
                msgs[msgs.length - 1] = {
                  ...last,
                  content: last.content + chunk.token,
                  isStreaming: true,
                };
              } else {
                // First token: create the assistant message
                msgs.push({ role: "assistant", content: chunk.token, isStreaming: true });
              }
              return { ...s, messages: msgs, isClassifying: false, isSearchingRAG: false };
            });
          } else if (chunk.type === "classifying") {
            updateModelState(idx, (s) => ({ ...s, isClassifying: true }));
          } else if (chunk.type === "rag_start") {
            updateModelState(idx, (s) => ({ ...s, isClassifying: false, isSearchingRAG: true }));
          } else if (chunk.type === "rag_done") {
            updateModelState(idx, (s) => ({ ...s, isSearchingRAG: false }));
          } else if (chunk.type === "done") {
            updateModelState(idx, (s) => {
              const msgs = [...s.messages];
              const last = msgs[msgs.length - 1];
              if (last && last.role === "assistant") {
                msgs[msgs.length - 1] = {
                  ...last,
                  isStreaming: false,
                  used_rag: chunk.used_rag,
                };
              }
              return {
                ...s,
                messages: msgs,
                isLoading: false,
                isSearchingRAG: false,
                isClassifying: false,
              };
            });
          } else if (chunk.type === "error") {
            updateModelState(idx, (s) => {
              const msgs = [...s.messages];
              // Add error as a new assistant message or update existing one
              const last = msgs[msgs.length - 1];
              if (last && last.role === "assistant") {
                msgs[msgs.length - 1] = {
                  ...last,
                  content: last.content || `Error: ${chunk.message || "Error desconocido"}`,
                  isStreaming: false,
                };
              } else {
                msgs.push({
                  role: "assistant",
                  content: `Error: ${chunk.message || "Error desconocido"}`,
                });
              }
              return {
                ...s,
                messages: msgs,
                isLoading: false,
                isSearchingRAG: false,
                isClassifying: false,
              };
            });
          }
        }
      } catch (err) {
        updateModelState(idx, (s) => ({
          ...s,
          isLoading: false,
          messages: [
            ...s.messages,
            {
              role: "assistant",
              content: `Error: ${
                err instanceof Error ? err.message : "Error desconocido"
              }`,
            },
          ],
        }));
      }
    });

    await Promise.allSettled(promises);
    setSending(false);
    inputRef.current?.focus();
  };

  // Handle Enter key (Shift+Enter for new line)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-950">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-gray-800 bg-gray-900 px-6 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-white">RAG System</h1>
          <span className="text-xs text-gray-500">
            Comparación Multi-Modelo
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-300">
            {user.full_name || user.email}
          </span>
          <button
            onClick={handleLogout}
            className="rounded-lg bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-300 transition hover:bg-gray-700 hover:text-white"
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Chat area */}
        <div className="flex flex-1 flex-col min-w-0">
          {/* Chat panels */}
          <div className="flex flex-1 overflow-hidden">
            {chatStates.length === 0 ? (
              <div className="flex flex-1 items-center justify-center text-gray-500">
                Cargando modelos...
              </div>
            ) : (
              chatStates.map((state) => (
                <ChatPanel
                  key={state.model.id}
                  modelName={state.model.name}
                  provider={state.model.provider}
                  messages={state.messages}
                  isLoading={state.isLoading}
                  isSearchingRAG={state.isSearchingRAG}
                  isClassifying={state.isClassifying}
                />
              ))
            )}
          </div>

          {/* Input area */}
          <div className="border-t border-gray-800 bg-gray-900 p-4">
            <div className="mx-auto flex max-w-5xl items-end gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Escribe tu pregunta... (Enter para enviar, Shift+Enter para nueva línea)"
                rows={1}
                className="flex-1 resize-none rounded-xl border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 max-h-32"
                style={{ minHeight: "44px" }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = Math.min(el.scrollHeight, 128) + "px";
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || sending}
                className="rounded-xl bg-indigo-600 p-3 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {sending ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19V5m0 0l-7 7m7-7l7 7"
                    />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
