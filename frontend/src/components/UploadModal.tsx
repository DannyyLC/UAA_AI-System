"use client";

import { useState, useRef, useCallback, type DragEvent } from "react";
import { uploadDocument } from "@/lib/api";

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".docx"];
const MAX_SIZE = 20 * 1024 * 1024; // 20 MB

interface UploadModalProps {
  existingTopics: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function UploadModal({
  existingTopics,
  onClose,
  onSuccess,
}: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [topic, setTopic] = useState(existingTopics[0] ?? "");
  const [isNewTopic, setIsNewTopic] = useState(existingTopics.length === 0);
  const [newTopicName, setNewTopicName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (f: File): string | null => {
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Formato no soportado (${ext}). Usa: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }
    if (f.size > MAX_SIZE) {
      return "El archivo excede el límite de 20 MB";
    }
    return null;
  };

  const handleFile = (f: File) => {
    const err = validateFile(f);
    if (err) {
      setError(err);
      return;
    }
    setError("");
    setFile(f);
  };

  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setDragOver(false), []);

  const handleSubmit = async () => {
    if (!file) return;
    const selectedTopic = isNewTopic ? newTopicName.trim().toLowerCase() : topic;
    if (!selectedTopic) {
      setError("Selecciona o crea una categoría");
      return;
    }

    setUploading(true);
    setError("");

    try {
      await uploadDocument(file, selectedTopic);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al subir archivo");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-gray-700 bg-gray-900 p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white">Subir documento</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 transition hover:bg-gray-800 hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Drag & Drop */}
        <div
          onClick={() => inputRef.current?.click()}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition ${
            dragOver
              ? "border-indigo-500 bg-indigo-900/20"
              : file
              ? "border-green-600 bg-green-900/10"
              : "border-gray-700 hover:border-gray-500"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ALLOWED_EXTENSIONS.join(",")}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          {file ? (
            <div className="space-y-1">
              <svg className="mx-auto h-8 w-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm font-medium text-green-300">{file.name}</p>
              <p className="text-xs text-gray-500">
                {(file.size / 1024).toFixed(0)} KB — Click para cambiar
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <svg className="mx-auto h-10 w-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm text-gray-300">
                Arrastra un archivo aquí o haz click para seleccionar
              </p>
              <p className="text-xs text-gray-500">
                PDF, TXT, MD, DOCX — Máx 20 MB
              </p>
            </div>
          )}
        </div>

        {/* Topic selector */}
        <div className="mt-5 space-y-3">
          <label className="block text-sm font-medium text-gray-300">
            Categoría
          </label>

          {existingTopics.length > 0 && (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setIsNewTopic(false)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  !isNewTopic
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:text-white"
                }`}
              >
                Existente
              </button>
              <button
                type="button"
                onClick={() => setIsNewTopic(true)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  isNewTopic
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:text-white"
                }`}
              >
                Nueva categoría
              </button>
            </div>
          )}

          {isNewTopic ? (
            <input
              type="text"
              value={newTopicName}
              onChange={(e) => setNewTopicName(e.target.value)}
              placeholder="Nombre de la nueva categoría"
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          ) : (
            <select
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {existingTopics.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mt-3 rounded-lg bg-red-900/40 border border-red-700 p-2 text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="mt-5 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-gray-400 transition hover:text-white"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || uploading}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? (
              <span className="flex items-center gap-2">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Subiendo...
              </span>
            ) : (
              "Subir archivo"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
