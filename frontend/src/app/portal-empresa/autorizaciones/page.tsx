"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch, TIPO_EXAMEN_LABEL } from "@/lib/api";

interface Auth {
  id: number; trabajador_documento: string; trabajador_nombre: string;
  tipo_examen: string; cargo: string; numero: string; vigencia_hasta: string | null; estado: string;
}
const inputCls = "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";
const VACIO = { trabajador_documento: "", trabajador_nombre: "", tipo_examen: "pre_ingreso", cargo: "", numero: "", vigencia_hasta: "" };

/** Autorizaciones de servicio (empresa cliente): pre-aprueba a sus trabajadores. */
export default function AutorizacionesPage() {
  const [lista, setLista] = useState<Auth[]>([]);
  const [f, setF] = useState<Record<string, string>>({ ...VACIO });
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  const cargar = useCallback(async () => { setLista(await apiFetch<Auth[]>("/autorizaciones/")); }, []);
  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(ev: React.FormEvent) {
    ev.preventDefault(); setMsg(null); setError(null);
    try {
      await apiFetch("/autorizaciones/", { method: "POST", body: JSON.stringify({ ...f, vigencia_hasta: f.vigencia_hasta || null }) });
      setF({ ...VACIO }); setMsg("Autorización emitida."); void cargar();
    } catch (e) { setError((e as Error).message.replace(/^API \d+:\s*/, "").slice(0, 200)); }
  }
  async function anular(a: Auth) {
    await apiFetch(`/autorizaciones/${a.id}/`, { method: "PATCH", body: JSON.stringify({ estado: "anulada" }) });
    void cargar();
  }

  return (
    <AppShell titulo="Autorizaciones de servicio">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <form onSubmit={crear} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Nueva autorización</h2>
          <label className={labelCls}>Documento del trabajador *
            <input value={f.trabajador_documento} onChange={(e) => set("trabajador_documento", e.target.value)} className={inputCls} required /></label>
          <label className={`${labelCls} mt-3`}>Nombre
            <input value={f.trabajador_nombre} onChange={(e) => set("trabajador_nombre", e.target.value)} className={inputCls} /></label>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>Tipo de examen
              <select value={f.tipo_examen} onChange={(e) => set("tipo_examen", e.target.value)} className={inputCls}>
                {Object.entries(TIPO_EXAMEN_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></label>
            <label className={labelCls}>Cargo
              <input value={f.cargo} onChange={(e) => set("cargo", e.target.value)} className={inputCls} /></label>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>N.º autorización
              <input value={f.numero} onChange={(e) => set("numero", e.target.value)} className={inputCls} /></label>
            <label className={labelCls}>Vigencia hasta
              <input type="date" value={f.vigencia_hasta} onChange={(e) => set("vigencia_hasta", e.target.value)} className={inputCls} /></label>
          </div>
          <button type="submit" className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white hover:bg-teal-700">Emitir autorización</button>
        </form>
        <section className="space-y-2">
          <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-gray-500">Emitidas ({lista.length})</h2>
          {lista.map((a) => (
            <article key={a.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-gray-900">{a.trabajador_nombre || a.trabajador_documento}</p>
                <p className="text-xs text-gray-500">Doc {a.trabajador_documento} · {TIPO_EXAMEN_LABEL[a.tipo_examen] ?? a.tipo_examen}{a.numero ? ` · N.º ${a.numero}` : ""}{a.vigencia_hasta ? ` · vence ${a.vigencia_hasta}` : ""}</p>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${a.estado === "activa" ? "bg-emerald-50 text-emerald-600" : "bg-gray-100 text-gray-500"}`}>{a.estado}</span>
              {a.estado === "activa" && (
                <button onClick={() => anular(a)} className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-200">Anular</button>
              )}
            </article>
          ))}
          {lista.length === 0 && <p className="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-400">Aún no hay autorizaciones.</p>}
        </section>
      </div>
    </AppShell>
  );
}
