"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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
  const [esDev, setEsDev] = useState(false);

  useEffect(() => {
    setEsDev(window.location.hostname.endsWith("localhost"));
  }, []);

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
      setYo(yo); // guarda identidad + cookie de rol para el middleware
      router.push(destino);
      router.refresh();
    } catch {
      setError("Correo o contraseña incorrectos.");
      setCargando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-3xl">
            🩺
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Halu Salud Ocupacional</h1>
          <p className="mt-1 text-sm text-gray-500">Ingresa con tu cuenta institucional</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-gray-200 bg-white p-6 shadow-xl"
        >
          <label className="block text-xs font-medium uppercase tracking-wide text-gray-500">
            Correo
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="recepcion@demo.com"
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

        {esDev && (
        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-500">
          <p className="font-semibold text-gray-500">Cuentas demo (contraseña: demo1234)</p>
          <p className="mt-1">recepcion@demo.com · medico@demo.com · coordinador@demo.com · empresa@demo.com</p>
        </div>
        )}
      </div>
    </main>
  );
}
