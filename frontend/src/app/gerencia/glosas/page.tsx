"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Factura { id: number; numero: string; total: string; empresa: number }
interface Glosa {
  id: number; factura: number | null; factura_numero: string | null;
  codigo: string; descripcion: string; valor: string; estado: string; respuesta: string;
}
const ESTADOS = [
  ["pendiente", "Pendiente"], ["aceptada", "Aceptada (IPS acepta)"],
  ["rechazada", "Rechazada (IPS ratifica)"], ["subsanada", "Subsanada"], ["conciliada", "Conciliada"],
] as const;
const COLOR: Record<string, string> = {
  pendiente: "bg-amber-50 text-amber-700", aceptada: "bg-red-50 text-red-600",
  rechazada: "bg-blue-50 text-blue-700", subsanada: "bg-teal-50 text-teal-700", conciliada: "bg-emerald-50 text-emerald-700",
};
const inputCls = "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/** Glosas: registro y conciliación de discrepancias de facturación (coordinador). */
export default function GlosasPage() {
  const [glosas, setGlosas] = useState<Glosa[]>([]);
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [f, setF] = useState({ factura: "", codigo: "", descripcion: "", valor: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  const cargar = useCallback(async () => {
    setGlosas(await apiFetch<Glosa[]>("/glosas/"));
    setFacturas(await apiFetch<Factura[]>("/facturas/"));
  }, []);
  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(ev: React.FormEvent) {
    ev.preventDefault(); setMsg(null);
    await apiFetch("/glosas/", { method: "POST", body: JSON.stringify({
      factura: f.factura ? Number(f.factura) : null, codigo: f.codigo, descripcion: f.descripcion, valor: f.valor || 0,
    }) });
    setF({ factura: "", codigo: "", descripcion: "", valor: "" }); setMsg("Glosa registrada."); void cargar();
  }
  async function conciliar(g: Glosa, estado: string) {
    const respuesta = window.prompt(`Respuesta / soporte de conciliación (${estado}):`, g.respuesta) ?? g.respuesta;
    await apiFetch(`/glosas/${g.id}/`, { method: "PATCH", body: JSON.stringify({ estado, respuesta }) });
    void cargar();
  }

  return (
    <AppShell titulo="Glosas y conciliación">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <form onSubmit={crear} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Registrar glosa</h2>
          <label className={labelCls}>Factura
            <select value={f.factura} onChange={(e) => set("factura", e.target.value)} className={inputCls}>
              <option value="">Sin asociar</option>
              {facturas.map((x) => <option key={x.id} value={x.id}>{x.numero || `Borrador #${x.id}`} · ${x.total}</option>)}
            </select></label>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>Código
              <input value={f.codigo} onChange={(e) => set("codigo", e.target.value)} className={inputCls} placeholder="Ej. 101" /></label>
            <label className={labelCls}>Valor
              <input type="number" value={f.valor} onChange={(e) => set("valor", e.target.value)} className={inputCls} /></label>
          </div>
          <label className={`${labelCls} mt-3`}>Descripción *
            <input value={f.descripcion} onChange={(e) => set("descripcion", e.target.value)} className={inputCls} required /></label>
          <button type="submit" className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white hover:bg-teal-700">Registrar</button>
        </form>
        <section className="space-y-2">
          <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-gray-500">Glosas ({glosas.length})</h2>
          {glosas.map((g) => (
            <article key={g.id} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900">{g.descripcion}</p>
                  <p className="text-xs text-gray-500">{g.factura_numero ? `${g.factura_numero} · ` : ""}{g.codigo ? `Cód. ${g.codigo} · ` : ""}${Number(g.valor).toLocaleString("es-CO")}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${COLOR[g.estado] ?? "bg-gray-100"}`}>{g.estado}</span>
              </div>
              {g.respuesta && <p className="mt-1 text-xs text-gray-500">↳ {g.respuesta}</p>}
              <div className="mt-2 flex flex-wrap gap-2">
                {ESTADOS.filter(([v]) => v !== g.estado).map(([v, l]) => (
                  <button key={v} onClick={() => conciliar(g, v)} className="rounded-lg bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-600 hover:bg-gray-200">{l}</button>
                ))}
              </div>
            </article>
          ))}
          {glosas.length === 0 && <p className="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-400">Sin glosas registradas.</p>}
        </section>
      </div>
    </AppShell>
  );
}
