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
    // Escritorio: video | formulario (mitad y mitad). Móvil: video arriba,
    // formulario debajo.
    <main className="flex min-h-screen flex-col lg:flex-row">
      {/* ------------------------------ Video ------------------------------ */}
      <section className="relative h-64 w-full shrink-0 overflow-hidden sm:h-80 lg:h-auto lg:min-h-screen lg:w-1/2">
        <video
          autoPlay
          muted
          loop
          playsInline
          className="absolute inset-0 h-full w-full object-cover"
        >
          <source src="/login-bg.mp4" type="video/mp4" />
        </video>
      </section>

      {/* --------------------------- Formulario ---------------------------- */}
      <section className="flex flex-1 items-center justify-center bg-gray-50 px-6 py-10 lg:px-12">
        <div className="w-full max-w-sm">
          {/* Marca del software, encima del formulario */}
          <div className="mb-8 flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="Halu Salud Ocupacional" className="h-14 w-auto lg:h-16" />
            <div>
              <p className="text-lg font-bold leading-tight text-gray-900 lg:text-xl">
                Halu Salud Ocupacional
              </p>
              <p className="text-xs text-gray-500">Prevención · Bienestar · Seguridad</p>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-gray-900">Bienvenido</h1>
          <p className="mt-1 text-sm text-gray-500">
            Ingresa con tu cuenta institucional
          </p>

          <form onSubmit={onSubmit} className="mt-6">
            <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
              Correo
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@correo.com"
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none"
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
                className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none"
              />
            </label>

            {error && (
              <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={cargando}
              className="mt-6 w-full rounded-lg bg-teal-600 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50"
            >
              {cargando ? "Ingresando…" : "Ingresar"}
            </button>
          </form>

          <p className="mt-8 flex items-center justify-center gap-1.5 text-xs text-gray-400">
            Powered by
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/axentia.png" alt="Axentia" className="h-4 w-auto" />
            <span className="font-semibold tracking-wide text-gray-600">AXENTIA</span>{" "}
            <span className="font-light">technologies</span>
          </p>
        </div>
      </section>
    </main>
  );
}
