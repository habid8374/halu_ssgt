"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

interface Epi {
  total_atenciones: number;
  aptitud: Record<string, number>;
  detalle_restringido?: boolean;
  diagnosticos: { codigo: string; descripcion: string; casos: number }[];
  hallazgos: { hallazgo: string; casos: number }[];
  pruebas: { tipo: string; realizadas: number }[];
}

const APTITUD_LABEL: Record<string, string> = {
  apto: "Apto", apto_restricciones: "Con restricciones", no_apto: "No apto", aplazado: "Aplazado",
};
const APTITUD_COLOR: Record<string, string> = {
  apto: "bg-emerald-500", apto_restricciones: "bg-amber-500", no_apto: "bg-red-500", aplazado: "bg-gray-400",
};
const PRUEBA_LABEL: Record<string, string> = {
  medicina: "Médica", visiometria: "Visiometría", audiometria: "Audiometría",
  espirometria: "Espirometría", laboratorio: "Laboratorio", psicologia: "Psicología", otro: "Otro",
};

const inputCls = "rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-teal-500 focus:outline-none";

/**
 * Diagnóstico de Condiciones de Salud (agregado). La empresa ve solo sus
 * agregados (con mínimo de anonimato); el coordinador puede elegir empresa.
 */
export default function EpidemiologiaPanel({ conEmpresa = false }: { conEmpresa?: boolean }) {
  const [empresas, setEmpresas] = useState<{ id: number; nombre: string }[]>([]);
  const [empresa, setEmpresa] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [epi, setEpi] = useState<Epi | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (conEmpresa) void apiFetch<{ id: number; nombre: string }[]>("/empresas/").then(setEmpresas);
  }, [conEmpresa]);

  const cargar = useCallback(async () => {
    setError(null);
    const p = new URLSearchParams();
    if (empresa) p.set("empresa", empresa);
    if (desde) p.set("desde", desde);
    if (hasta) p.set("hasta", hasta);
    try {
      setEpi(await apiFetch<Epi>(`/epidemiologia/?${p.toString()}`));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [empresa, desde, hasta]);

  useEffect(() => { void cargar(); }, [cargar]);

  const totalApt = epi ? Object.values(epi.aptitud).reduce((a, b) => a + b, 0) : 0;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        {conEmpresa && (
          <label className="text-[11px] font-medium uppercase tracking-wide text-gray-500">
            Empresa
            <select value={empresa} onChange={(e) => setEmpresa(e.target.value)} className={`${inputCls} mt-1 block`}>
              <option value="">Toda la IPS</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          </label>
        )}
        <label className="text-[11px] font-medium uppercase tracking-wide text-gray-500">Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className={`${inputCls} mt-1 block`} />
        </label>
        <label className="text-[11px] font-medium uppercase tracking-wide text-gray-500">Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className={`${inputCls} mt-1 block`} />
        </label>
      </div>

      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      {epi && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Aptitud */}
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-teal-600">Concepto de aptitud</h2>
            <p className="mb-3 text-xs text-gray-400">{epi.total_atenciones} atenciones en el periodo</p>
            {totalApt === 0 ? <p className="text-sm text-gray-400">Sin conceptos firmados.</p> : (
              <div className="space-y-2">
                {Object.entries(epi.aptitud).map(([k, n]) => (
                  <div key={k}>
                    <div className="mb-0.5 flex justify-between text-xs text-gray-600">
                      <span>{APTITUD_LABEL[k] ?? k}</span><span className="tabular-nums">{n}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                      <div className={`h-full ${APTITUD_COLOR[k] ?? "bg-gray-400"}`} style={{ width: `${Math.round((n / totalApt) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Pruebas realizadas */}
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-600">Pruebas realizadas</h2>
            <div className="flex flex-wrap gap-2">
              {epi.pruebas.map((p) => (
                <span key={p.tipo} className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-700">
                  {PRUEBA_LABEL[p.tipo] ?? p.tipo}: {p.realizadas}
                </span>
              ))}
              {epi.pruebas.length === 0 && <span className="text-sm text-gray-400">Sin pruebas.</span>}
            </div>
            {epi.hallazgos.length > 0 && (
              <>
                <h3 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-gray-500">Hallazgos frecuentes</h3>
                <div className="flex flex-wrap gap-2">
                  {epi.hallazgos.map((h) => (
                    <span key={h.hallazgo} className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                      {h.hallazgo}: {h.casos}
                    </span>
                  ))}
                </div>
              </>
            )}
          </section>

          {/* Diagnósticos */}
          <section className="rounded-xl border border-gray-200 bg-white p-5 md:col-span-2">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-600">Diagnósticos más frecuentes (CIE-10)</h2>
            {epi.detalle_restringido ? (
              <p className="text-sm text-gray-400">Muy pocos casos para mostrar detalle (se protege la confidencialidad).</p>
            ) : epi.diagnosticos.length === 0 ? (
              <p className="text-sm text-gray-400">Sin diagnósticos registrados.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-gray-500">
                  <tr><th className="py-1 font-medium">CIE-10</th><th className="py-1 font-medium">Descripción</th><th className="py-1 text-right font-medium">Casos</th></tr>
                </thead>
                <tbody>
                  {epi.diagnosticos.map((d) => (
                    <tr key={d.codigo} className="border-t border-gray-100">
                      <td className="py-1.5 font-mono text-xs text-gray-600">{d.codigo}</td>
                      <td className="py-1.5 text-gray-800">{d.descripcion}</td>
                      <td className="py-1.5 text-right font-semibold tabular-nums text-gray-700">{d.casos}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
