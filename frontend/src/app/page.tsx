"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

export default function LoginPage() {
  const { user, loading, login, register } = useAuth();
  const router = useRouter();

  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState("");

  // Redirect if already logged in
  useEffect(() => {
    if (!loading && user) router.replace("/chat");
  }, [user, loading, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setRegisterSuccess("");
    setSubmitting(true);

    try {
      if (isRegister) {
        await register({ email, password, full_name: fullName });
        setRegisterSuccess(
          "Cuenta creada exitosamente. Por favor inicia sesión."
        );
        setIsRegister(false);
        setPassword("");
      } else {
        await login({ email, password });
        router.replace("/chat");
      }
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Error desconocido";
      // Mapear mensajes técnicos a textos amigables
      const friendly: Record<string, string> = {
        "Credenciales inválidas": "Correo o contraseña incorrectos. Verifica tus datos e intenta de nuevo.",
        "El email ya está registrado": "Este correo ya tiene una cuenta. Inicia sesión o usa otro correo.",
        "Datos de entrada inválidos": "Revisa que todos los campos estén correctos.",
        "Servicio de autenticación no disponible": "El servicio no está disponible en este momento. Intenta más tarde.",
        "Error interno del servidor": "Ocurrió un error inesperado. Intenta de nuevo en unos momentos.",
      };
      setError(friendly[raw] ?? raw);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-gray-800 bg-gray-900 p-8 shadow-xl">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-white">
            RAG System
          </h1>
          <p className="mt-2 text-sm text-gray-400">
            {isRegister
              ? "Crea una cuenta para comenzar"
              : "Inicia sesión para continuar"}
          </p>
        </div>

        {/* Success message */}
        {registerSuccess && (
          <div className="rounded-lg bg-green-900/40 border border-green-700 p-3 text-sm text-green-300">
            {registerSuccess}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 rounded-lg bg-red-900/30 border border-red-700/50 p-3.5 text-sm text-red-300">
            <svg className="mt-0.5 h-4 w-4 shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {isRegister && (
            <div>
              <label
                htmlFor="fullName"
                className="mb-1 block text-sm font-medium text-gray-300"
              >
                Nombre completo
              </label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                minLength={2}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                placeholder="Juan Pérez"
              />
            </div>
          )}

          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-sm font-medium text-gray-300"
            >
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="usuario@uaa.edu.mx"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-gray-300"
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting
              ? "Cargando..."
              : isRegister
              ? "Crear cuenta"
              : "Iniciar sesión"}
          </button>
        </form>

        {/* Toggle */}
        <p className="text-center text-sm text-gray-400">
          {isRegister ? "¿Ya tienes cuenta?" : "¿No tienes cuenta?"}{" "}
          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister);
              setError("");
              setRegisterSuccess("");
            }}
            className="font-medium text-indigo-400 hover:text-indigo-300"
          >
            {isRegister ? "Inicia sesión" : "Regístrate"}
          </button>
        </p>
      </div>
    </div>
  );
}
