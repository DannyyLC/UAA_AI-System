"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getDocumentSources,
  deleteDocument,
} from "@/lib/api";
import type { DocumentSources } from "@/lib/types";
import UploadModal from "./UploadModal";

interface SidebarProps {
  onRefresh?: () => void;
}

export default function Sidebar({ onRefresh }: SidebarProps) {
  const [sources, setSources] = useState<DocumentSources | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());

  const fetchSources = useCallback(async () => {
    try {
      const data = await getDocumentSources();
      setSources(data);
      // Auto-expand all topics
      setExpandedTopics(new Set(data.topics));
    } catch {
      /* user may not have docs yet */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const toggleTopic = (topic: string) => {
    setExpandedTopics((prev) => {
      const next = new Set(prev);
      if (next.has(topic)) next.delete(topic);
      else next.add(topic);
      return next;
    });
  };

  const handleDelete = async (filename: string, topic: string) => {
    if (!confirm(`¿Eliminar "${filename}" de ${topic}?`)) return;
    setDeletingFile(filename);
    try {
      await deleteDocument(filename, topic);
      await fetchSources();
      onRefresh?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setDeletingFile(null);
    }
  };

  const handleUploadSuccess = () => {
    setShowUpload(false);
    fetchSources();
    onRefresh?.();
  };

  return (
    <>
      <aside className="flex h-full w-72 flex-col border-r border-gray-800 bg-gray-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Documentos
          </h2>
          <button
            onClick={() => setShowUpload(true)}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500"
            title="Subir documento"
          >
            + Archivo
          </button>
        </div>

        {/* File tree */}
        <div className="flex-1 overflow-y-auto p-3">
          {loading ? (
            <div className="flex justify-center pt-8">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            </div>
          ) : !sources || sources.total === 0 ? (
            <p className="pt-8 text-center text-xs text-gray-500">
              No hay documentos indexados.
              <br />
              Sube tu primer archivo.
            </p>
          ) : (
            <div className="space-y-1">
              {sources.topics.map((topic) => (
                <div key={topic}>
                  {/* Topic header */}
                  <button
                    onClick={() => toggleTopic(topic)}
                    className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm font-medium text-gray-300 hover:bg-gray-800 transition"
                  >
                    <svg
                      className={`h-3 w-3 text-gray-500 transition-transform ${
                        expandedTopics.has(topic) ? "rotate-90" : ""
                      }`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M6 4l8 6-8 6V4z" />
                    </svg>
                    <svg
                      className="h-4 w-4 text-indigo-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-5l-2-2H5a2 2 0 00-2 2z"
                      />
                    </svg>
                    <span className="truncate capitalize">{topic}</span>
                    <span className="ml-auto text-xs text-gray-500">
                      {sources.sources[topic]?.length ?? 0}
                    </span>
                  </button>

                  {/* Files */}
                  {expandedTopics.has(topic) && (
                    <div className="ml-5 space-y-0.5 pb-1">
                      {sources.sources[topic]?.map((doc) => (
                        <div
                          key={doc.job_id}
                          className="group flex items-center gap-2 rounded-md px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 transition"
                        >
                          <svg
                            className="h-3.5 w-3.5 shrink-0 text-gray-500"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          <span className="flex-1 truncate" title={doc.filename}>
                            {doc.filename}
                          </span>
                          <span className="text-gray-600">{doc.chunks}ch</span>
                          <button
                            onClick={() => handleDelete(doc.filename, topic)}
                            disabled={deletingFile === doc.filename}
                            className="hidden rounded p-0.5 text-gray-500 transition hover:bg-red-900/50 hover:text-red-400 group-hover:inline-flex disabled:opacity-50"
                            title="Eliminar documento"
                          >
                            {deletingFile === doc.filename ? (
                              <div className="h-3 w-3 animate-spin rounded-full border border-red-400 border-t-transparent" />
                            ) : (
                              <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                />
                              </svg>
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer stats */}
        {sources && sources.total > 0 && (
          <div className="border-t border-gray-800 px-4 py-2 text-xs text-gray-500">
            {sources.total} documento{sources.total !== 1 ? "s" : ""} en{" "}
            {sources.topics.length} categoría{sources.topics.length !== 1 ? "s" : ""}
          </div>
        )}
      </aside>

      {/* Upload Modal */}
      {showUpload && (
        <UploadModal
          existingTopics={sources?.topics ?? []}
          onClose={() => setShowUpload(false)}
          onSuccess={handleUploadSuccess}
        />
      )}
    </>
  );
}
