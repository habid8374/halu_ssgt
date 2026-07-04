"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Concepto {
  id: number;
  trabajador_nombre: string;
  aptitud: string;
  restricciones: string;
  recomendaciones_laborales: string;
  fecha_emision: string | null;
  profesional_nombre: string;
}

const APTITUD_UI: Record<string, { label: string; clase: string }> = {
  apto: { label: "Apto", clase: "bg-emerald-500/15 text-emerald-400" },
  apto_restricciones: { label: "Apto con restricciones", clase: "bg-amber-500/15 text-amber-400" },
  no_apto: { label: "No apto", clase: "bg-red-500/15 text-red-400" },
  aplazado: { label: "Aplazado", clase: "bg-slate-500/15 text-slate-400" },
};

/**
 * Portal de la empresa cliente. SOLO conceptos de aptitud firmados de SUS
 * trabajadores — la historia clínica es inaccesible por diseño en el
 * backend (Res. 1843/2025; CLAUDE.md regla 1).
 */
export default function PortalEmpresaPage() {
  const [conceptos, setConceptos] = useState<Concepto[] | null>(null);

  useEffect(() => {
    apiFetch<Concepto[]>("/conceptos/").then(setConceptos).catch(() => setConceptos([]));
  }, []);

  return (
    <AppShell titulo="Portal empresa — Conceptos de aptitud">
      <p className="mb-4 text-xs text-slate-500">
        Por normativa (Res. 1843/2025), este portal solo muestra el concepto de aptitud
        ocupacional. La historia clínica es reservada y no es accesible para el empleador.
      </p>
      {conceptos === null ? (
        <p className="text-sm text-slate-400">Cargando…</p>
      ) : conceptos.length === 0 ? (
        <p className="text-sm text-slate-400">Aún no hay conceptos firmados disponibles.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-4 py-3">Trabajador</th>
                <th className="px-4 py-3">Concepto</th>
                <th className="px-4 py-3">Restricciones</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Profesional</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {conceptos.map((c) => {
                const ap = APTITUD_UI[c.aptitud] ?? APTITUD_UI.aplazado;
                return (
                  <tr key={c.id} className="bg-slate-950">
                    <td className="px-4 py-3 font-medium text-white">{c.trabajador_nombre}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ap.clase}`}>
                        {ap.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{c.restricciones || "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{c.fecha_emision ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-400">{c.profesional_nombre}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
