"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Empresa { id: number; nombre: string }
interface Prueba { tipo_prueba: string; detalle?: string }
interface Profesiograma {
  id: number; empresa: number; empresa_nombre: string; cargo: string; activo: boolean;
  pruebas: Prueba[];
}

const PRUEBAS = [
  ["medicina", "Evaluación médica"], ["visiometria", "Visiometría"],
  ["audiometria", "Audiometría"], ["espirometria", "Espirometría"],
  ["laboratorio", "Laboratorio"], ["psicologia", "Psicología"], ["otro", "Otro paraclínico"],
] as const;
const LABEL: Record<string, string> = Object.fromEntries(PRUEBAS);

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Profesiogramas (rol coordinador): batería de pruebas por empresa y cargo.
 * La admisión la carga automáticamente al elegir empresa + cargo.
 */
export default function ProfesiogramasPage() {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [lista, setLista] = useState<Profesiograma[]>([]);
  const [empresa, setEmpresa] = useState("");
  const [cargo, setCargo] = useState("");
  const [sel, setSel] = useState<string[]>(["medicina"]);
  const [editId, setEditId] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setEmpresas(await apiFetch<Empresa[]>("/empresas/"));
    setLista(await apiFetch<Profesiograma[]>("/profesiogramas/"));
  }, []);
  useEffect(() => { void cargar(); }, [cargar]);

  const toggle = (t: string) => setSel((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]));

  function nuevo() { setEditId(null); setEmpresa(""); setCargo(""); setSel(["medicina"]); }
  function editar(p: Profesiograma) {
    setEditId(p.id); setEmpresa(String(p.empresa)); setCargo(p.cargo);
    setSel(p.pruebas.map((x) => x.tipo_prueba));
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    setMsg(null); setError(null);
    const body = JSON.stringify({
      empresa: Number(empresa), cargo, activo: true,
      pruebas: sel.map((t) => ({ tipo_prueba: t, detalle: "" })),
    });
    try {
      if (editId) await apiFetch(`/profesiogramas/${editId}/`, { method: "PATCH", body });
      else await apiFetch("/profesiogramas/", { method: "POST", body });
      setMsg("Profesiograma guardado."); nuevo(); void cargar();
    } catch (e) {
      setError((e as Error).message.replace(/^API \d+:\s*/, "").slice(0, 200));
    }
  }

  return (
    <AppShell titulo="Profesiogramas (batería por cargo)">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <form onSubmit={guardar} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
            {editId ? "Editar profesiograma" : "Nuevo profesiograma"}
          </h2>
          <label className={labelCls}>Empresa *
            <select value={empresa} onChange={(e) => setEmpresa(e.target.value)} className={inputCls} required disabled={!!editId}>
              <option value="">Seleccionar…</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>Cargo *
            <input value={cargo} onChange={(e) => setCargo(e.target.value)} className={inputCls} placeholder="Operario de máquina" required disabled={!!editId} />
          </label>
          <p className="mb-2 mt-4 text-[11px] font-semibold uppercase tracking-wide text-gray-500">Batería de pruebas</p>
          <div className="flex flex-wrap gap-2">
            {PRUEBAS.map(([v, l]) => (
              <button type="button" key={v} onClick={() => toggle(v)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                  sel.includes(v) ? "bg-teal-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
                {sel.includes(v) ? "✓ " : ""}{l}
              </button>
            ))}
          </div>
          <div className="mt-5 flex gap-2">
            <button type="submit" className="rounded-lg bg-teal-600 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-700">
              {editId ? "Guardar cambios" : "Crear profesiograma"}
            </button>
            {editId && (
              <button type="button" onClick={nuevo} className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-200">
                Cancelar
              </button>
            )}
          </div>
        </form>

        <section className="space-y-2">
          <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-gray-500">Definidos ({lista.length})</h2>
          {lista.map((p) => (
            <article key={p.id} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900">{p.cargo}</p>
                  <p className="text-xs text-gray-500">{p.empresa_nombre}</p>
                </div>
                <button onClick={() => editar(p)} className="rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 hover:bg-teal-100">
                  Editar
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {p.pruebas.map((x) => (
                  <span key={x.tipo_prueba} className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600">
                    {LABEL[x.tipo_prueba] ?? x.tipo_prueba}
                  </span>
                ))}
                {p.pruebas.length === 0 && <span className="text-xs text-gray-400">Sin pruebas.</span>}
              </div>
            </article>
          ))}
          {lista.length === 0 && (
            <p className="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-400">
              Aún no hay profesiogramas. Crea el primero a la izquierda.
            </p>
          )}
        </section>
      </div>
    </AppShell>
  );
}
