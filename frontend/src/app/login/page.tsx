"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, login, setYo, type Yo } from "@/lib/api";

const RUTA_POR_ROL: Record<string, string> = {
  recepcion: "/recepcion",
  medico: "/consultorio/mi-cola",
  coordinador: "/gerencia",
  empresa_cliente: "/portal-empresa",
  psicologo_sst: "/psicosocial",
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await login(email, password);
      const yo = await apiFetch<Yo>("/me/");
      const destino = RUTA_POR_ROL[yo.rol];
      if (!destino) {
        // admin_sistema / superusuario: su puerta es el panel administrativo.
        const { setSesion } = await import("@/lib/api");
        setSesion(null);
        setError(
          "Esta cuenta es de administración de plataforma. Ingresa por el panel " +
            "administrativo (/admin del dominio del servidor). Para usar la app, " +
            "crea allí un usuario con rol operativo (p. ej. coordinador)."
        );
        setCargando(false);
        return;
      }
      setYo(yo);
      router.push(destino);
      router.refresh();
    } catch {
      setError("Correo o contraseña incorrectos.");
      setCargando(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      {/* Video de fondo institucional */}
      <video
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 h-full w-full object-cover"
      >
        <source src="/login-bg.mp4" type="video/mp4" />
      </video>
      {/* Velo para legibilidad de la tarjeta */}
      <div className="absolute inset-0 bg-slate-900/55 backdrop-blur-[2px]" />

      <div className="relative z-10 w-full max-w-sm">
        <div className="mb-6 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.png"
            alt="Halu Salud Ocupacional"
            className="mx-auto mb-3 h-20 w-auto drop-shadow-lg"
          />
          <h1 className="text-2xl font-bold text-white drop-shadow">
            Halu Salud Ocupacional
          </h1>
          <p className="mt-1 text-sm text-white/80">
            Prevención · Bienestar · Seguridad
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-white/20 bg-white/95 p-6 shadow-2xl backdrop-blur"
        >
          <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
            Correo
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@correo.com"
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none"
            />
          </label>
          <label className="mt-4 block text-xs font-medium uppercase tracking-wide text-gray-500">
            Contraseña
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none"
            />
          </label>

          {error && (
            <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}

          <button
            type="submit"
            disabled={cargando}
            className="mt-5 w-full rounded-lg bg-teal-600 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50"
          >
            {cargando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-white/70">
          Powered by <span className="font-semibold tracking-wide text-white">AXENTIA</span>{" "}
          <span className="font-light">technologies</span>
        </p>
      </div>
    </main>
  );
}
