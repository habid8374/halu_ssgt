"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch, login, setYo, type Yo } from "@/lib/api";

const RUTA_POR_ROL: Record<string, string> = {
  recepcion: "/recepcion",
  medico: "/consultorio/mi-cola",
  coordinador: "/gerencia",
  empresa_cliente: "/portal-empresa",
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
      setYo(yo); // guarda identidad + cookie de rol para el middleware
      router.push(RUTA_POR_ROL[yo.rol] ?? "/login");
      router.refresh();
    } catch {
      setError("Correo o contraseña incorrectos.");
      setCargando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-500/15 text-3xl">
            🩺
          </div>
          <h1 className="text-2xl font-bold text-white">Halu Salud Ocupacional</h1>
          <p className="mt-1 text-sm text-slate-400">Ingresa con tu cuenta institucional</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl"
        >
          <label className="block text-xs font-medium uppercase tracking-wide text-slate-400">
            Correo
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="recepcion@demo.com"
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none"
            />
          </label>
          <label className="mt-4 block text-xs font-medium uppercase tracking-wide text-slate-400">
            Contraseña
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none"
            />
          </label>

          {error && (
            <p className="mt-3 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={cargando}
            className="mt-5 w-full rounded-lg bg-teal-500 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-teal-400 disabled:opacity-50"
          >
            {cargando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>

        <div className="mt-4 rounded-xl border border-slate-800/60 bg-slate-900/50 p-3 text-xs text-slate-500">
          <p className="font-semibold text-slate-400">Cuentas demo (contraseña: demo1234)</p>
          <p className="mt-1">recepcion@demo.com · medico@demo.com · coordinador@demo.com · empresa@demo.com</p>
        </div>
      </div>
    </main>
  );
}
