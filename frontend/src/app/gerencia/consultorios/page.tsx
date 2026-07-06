"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Sede { id: number; nombre: string; codigo: string; direccion: string; activa: boolean }
interface Consultorio { id: number; sede: number; sede_nombre: string; nombre: string; activo: boolean }

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Sedes y consultorios de la IPS (rol coordinador). Cada IPS configura sus
 * propias sedes y los consultorios de cada una, sin pasar por el admin.
 */
export default function ConsultoriosPage() {
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [consultorios, setConsultorios] = useState<Consultorio[]>([]);
  const [nuevaSede, setNuevaSede] = useState({ nombre: "", codigo: "", direccion: "" });
  const [nuevoConsul, setNuevoConsul] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setSedes(await apiFetch<Sede[]>("/sedes/"));
    setConsultorios(await apiFetch<Consultorio[]>("/consultorios/"));
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  async function crearSede(ev: React.FormEvent) {
    ev.preventDefault();
    setMsg(null); setError(null);
    try {
      await apiFetch("/sedes/", { method: "POST", body: JSON.stringify(nuevaSede) });
      setNuevaSede({ nombre: "", codigo: "", direccion: "" });
      setMsg("Sede creada.");
      void cargar();
    } catch (e) {
      setError((e as Error).message.replace(/^API \d+:\s*/, ""));
    }
  }

  async function crearConsultorio(sedeId: number) {
    const nombre = (nuevoConsul[sedeId] ?? "").trim();
    if (!nombre) return;
    setMsg(null); setError(null);
    try {
      await apiFetch("/consultorios/", {
        method: "POST",
        body: JSON.stringify({ sede: sedeId, nombre }),
      });
      setNuevoConsul((p) => ({ ...p, [sedeId]: "" }));
      void cargar();
    } catch (e) {
      setError((e as Error).message.replace(/^API \d+:\s*/, ""));
    }
  }

  async function alternarSede(s: Sede) {
    await apiFetch(`/sedes/${s.id}/`, { method: "PATCH", body: JSON.stringify({ activa: !s.activa }) });
    void cargar();
  }
  async function alternarConsultorio(c: Consultorio) {
    await apiFetch(`/consultorios/${c.id}/`, { method: "PATCH", body: JSON.stringify({ activo: !c.activo }) });
    void cargar();
  }

  return (
    <AppShell titulo="Sedes y consultorios">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        {/* ----------------------------- Nueva sede ----------------------------- */}
        <form onSubmit={crearSede} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Nueva sede</h2>
          <label className={labelCls}>Nombre *
            <input value={nuevaSede.nombre} onChange={(e) => setNuevaSede((p) => ({ ...p, nombre: e.target.value }))} className={inputCls} placeholder="Sede Norte" required />
          </label>
          <label className={`${labelCls} mt-3`}>Código de habilitación (REPS)
            <input value={nuevaSede.codigo} onChange={(e) => setNuevaSede((p) => ({ ...p, codigo: e.target.value }))} className={inputCls} placeholder="Opcional" />
          </label>
          <label className={`${labelCls} mt-3`}>Dirección
            <input value={nuevaSede.direccion} onChange={(e) => setNuevaSede((p) => ({ ...p, direccion: e.target.value }))} className={inputCls} />
          </label>
          <button type="submit"
            className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700">
            Crear sede
          </button>
        </form>

        {/* --------------------------- Sedes + consultorios --------------------------- */}
        <section className="space-y-4">
          {sedes.map((s) => {
            const propios = consultorios.filter((c) => c.sede === s.id);
            return (
              <article key={s.id} className="rounded-xl border border-gray-200 bg-white p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900">
                      {s.nombre}{s.codigo ? <span className="font-normal text-gray-400"> · {s.codigo}</span> : null}
                    </p>
                    {s.direccion && <p className="text-xs text-gray-500">{s.direccion}</p>}
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                    s.activa ? "bg-emerald-50 text-emerald-600" : "bg-gray-100 text-gray-500"
                  }`}>{s.activa ? "Activa" : "Inactiva"}</span>
                  <button onClick={() => alternarSede(s)}
                    className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 transition hover:bg-gray-200">
                    {s.activa ? "Desactivar" : "Activar"}
                  </button>
                </div>

                <div className="mt-4 rounded-lg bg-gray-50 p-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Consultorios ({propios.length})
                  </p>
                  <div className="mb-3 flex flex-wrap gap-2">
                    {propios.map((c) => (
                      <button key={c.id} onClick={() => alternarConsultorio(c)}
                        title={c.activo ? "Clic para desactivar" : "Clic para activar"}
                        className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                          c.activo
                            ? "bg-white text-gray-700 ring-1 ring-gray-200 hover:ring-gray-300"
                            : "bg-gray-100 text-gray-400 line-through hover:bg-gray-200"
                        }`}>
                        {c.nombre}
                      </button>
                    ))}
                    {propios.length === 0 && <span className="text-xs text-gray-400">Sin consultorios.</span>}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={nuevoConsul[s.id] ?? ""}
                      onChange={(e) => setNuevoConsul((p) => ({ ...p, [s.id]: e.target.value }))}
                      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void crearConsultorio(s.id); } }}
                      className={`${inputCls} mt-0 max-w-xs`}
                      placeholder="Consultorio 1"
                    />
                    <button onClick={() => crearConsultorio(s.id)}
                      className="rounded-lg bg-teal-600 px-4 text-xs font-semibold text-white transition hover:bg-teal-700">
                      Agregar
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
          {sedes.length === 0 && (
            <p className="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-400">
              Aún no hay sedes. Crea la primera a la izquierda.
            </p>
          )}
        </section>
      </div>
    </AppShell>
  );
}
