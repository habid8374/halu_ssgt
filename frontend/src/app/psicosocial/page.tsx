"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Instrumento {
  id: number;
  trabajador_nombre: string;
  tipo: string;
  fecha_aplicacion: string;
  nivel_riesgo: string;
}
interface Consolidado {
  total: number;
  detalle: { tipo: string; nivel_riesgo: string; cantidad: number }[];
  nota?: string;
}
interface Trabajador {
  id: number;
  nombres: string;
  apellidos: string;
}

const TIPOS = [
  ["intralaboral", "Cuestionario intralaboral"],
  ["extralaboral", "Cuestionario extralaboral"],
  ["estres", "Cuestionario de estrés"],
  ["ficha", "Ficha sociodemográfica"],
] as const;

const NIVELES = [
  ["sin_riesgo", "Sin riesgo"],
  ["bajo", "Bajo"],
  ["medio", "Medio"],
  ["alto", "Alto"],
  ["muy_alto", "Muy alto"],
] as const;

const NIVEL_COLOR: Record<string, string> = {
  sin_riesgo: "bg-emerald-50 text-emerald-600",
  bajo: "bg-teal-50 text-teal-700",
  medio: "bg-amber-50 text-amber-700",
  alto: "bg-orange-100 text-orange-700",
  muy_alto: "bg-red-50 text-red-600",
};

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Batería de riesgo psicosocial (Res. 2404/2019). Los instrumentos listados
 * son SOLO los aplicados por este psicólogo (custodia separada). El
 * consolidado es agregado y anónimo.
 */
export default function PsicosocialPage() {
  const [instrumentos, setInstrumentos] = useState<Instrumento[]>([]);
  const [consolidado, setConsolidado] = useState<Consolidado | null>(null);

  const [numDoc, setNumDoc] = useState("");
  const [trabajador, setTrabajador] = useState<Trabajador | null>(null);
  const [tipo, setTipo] = useState("intralaboral");
  const [nivel, setNivel] = useState("medio");
  const [contenido, setContenido] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setInstrumentos(await apiFetch<Instrumento[]>("/psicosocial/instrumentos/"));
    setConsolidado(await apiFetch<Consolidado>("/psicosocial/consolidado/"));
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function buscar() {
    setTrabajador(null);
    setMsg(null);
    // El psicólogo no gestiona trabajadores; consulta por documento vía API
    // de solo lectura no disponible para su rol -> se busca en instrumentos
    // previos o se pide apoyo de recepción. Para simplificar fase 2: buscar
    // por documento usando el endpoint de recepción NO está permitido, así
    // que se solicita el ID interno si ya se conoce.
    const id = Number(numDoc);
    if (Number.isInteger(id) && id > 0) {
      setTrabajador({ id, nombres: `Trabajador #${id}`, apellidos: "" });
    } else {
      setMsg("Ingresa el ID interno del trabajador (visible en la lista de instrumentos o suministrado por recepción).");
    }
  }

  async function aplicar(e: React.FormEvent) {
    e.preventDefault();
    if (!trabajador) return;
    setMsg(null);
    try {
      await apiFetch("/psicosocial/instrumentos/", {
        method: "POST",
        body: JSON.stringify({
          trabajador: trabajador.id, tipo, nivel_riesgo: nivel, contenido,
        }),
      });
      setNumDoc(""); setTrabajador(null); setContenido("");
      void cargar();
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  return (
    <AppShell titulo="Batería de riesgo psicosocial">
      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <form onSubmit={aplicar} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Aplicar instrumento</h2>
          <label className={labelCls}>
            ID del trabajador
            <div className="flex gap-2">
              <input value={numDoc} onChange={(e) => setNumDoc(e.target.value)} className={inputCls} placeholder="ej. 3" />
              <button type="button" onClick={buscar}
                className="mt-1 rounded-lg bg-gray-200 px-4 text-sm font-semibold text-gray-900 hover:bg-gray-300">
                Usar
              </button>
            </div>
          </label>
          {trabajador && (
            <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-600">
              {trabajador.nombres} {trabajador.apellidos}
            </p>
          )}
          <label className={`${labelCls} mt-3`}>
            Instrumento
            <select value={tipo} onChange={(e) => setTipo(e.target.value)} className={inputCls}>
              {TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Nivel de riesgo resultante
            <select value={nivel} onChange={(e) => setNivel(e.target.value)} className={inputCls}>
              {NIVELES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Observaciones (reservadas, cifradas)
            <textarea rows={3} value={contenido} onChange={(e) => setContenido(e.target.value)} className={inputCls} />
          </label>
          {msg && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">{msg}</p>}
          <button type="submit" disabled={!trabajador}
            className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-40">
            Guardar instrumento
          </button>
        </form>

        <div className="space-y-6">
          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">
              Mis instrumentos aplicados ({instrumentos.length})
            </h2>
            <div className="space-y-2">
              {instrumentos.map((i) => (
                <article key={i.id} className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900">{i.trabajador_nombre}</p>
                    <p className="text-xs text-gray-500">
                      {TIPOS.find(([v]) => v === i.tipo)?.[1] ?? i.tipo} · {i.fecha_aplicacion}
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${NIVEL_COLOR[i.nivel_riesgo] ?? ""}`}>
                    {NIVELES.find(([v]) => v === i.nivel_riesgo)?.[1] ?? i.nivel_riesgo}
                  </span>
                </article>
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">
              Informe consolidado (agregado y anónimo)
            </h2>
            {consolidado && (
              consolidado.detalle.length === 0 ? (
                <p className="text-sm text-gray-500">{consolidado.nota ?? "Sin datos suficientes."}</p>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                  <table className="w-full text-left text-sm">
                    <thead className="text-xs uppercase tracking-wide text-gray-500">
                      <tr>
                        <th className="px-4 py-2.5">Instrumento</th>
                        <th className="px-4 py-2.5">Nivel</th>
                        <th className="px-4 py-2.5">Cantidad</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {consolidado.detalle.map((d, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2.5 text-gray-900">
                            {TIPOS.find(([v]) => v === d.tipo)?.[1] ?? d.tipo}
                          </td>
                          <td className="px-4 py-2.5">
                            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${NIVEL_COLOR[d.nivel_riesgo] ?? ""}`}>
                              {NIVELES.find(([v]) => v === d.nivel_riesgo)?.[1] ?? d.nivel_riesgo}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-gray-600">{d.cantidad}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </section>
        </div>
      </div>
    </AppShell>
  );
}
