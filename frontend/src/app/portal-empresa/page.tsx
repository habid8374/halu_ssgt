"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import { imprimirConcepto, imprimirConceptosLote } from "@/lib/conceptoPdf";

interface Concepto {
  id: number;
  trabajador_nombre: string;
  trabajador_documento?: string;
  empresa_nombre?: string;
  tipo_examen?: string;
  aptitud: string;
  restricciones: string;
  recomendaciones_laborales: string;
  firmado?: boolean;
  fecha_emision: string | null;
  vigencia_hasta?: string | null;
  profesional_nombre: string;
}

const APTITUD_UI: Record<string, { label: string; clase: string }> = {
  apto: { label: "Apto", clase: "bg-emerald-50 text-emerald-600" },
  apto_restricciones: { label: "Apto con restricciones", clase: "bg-amber-500/15 text-amber-700" },
  no_apto: { label: "No apto", clase: "bg-red-500/15 text-red-600" },
  aplazado: { label: "Aplazado", clase: "bg-gray-100 text-gray-500" },
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
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <p className="flex-1 text-xs text-gray-500">
          Por normativa (Res. 1843/2025), este portal solo muestra el concepto de aptitud
          ocupacional. La historia clínica es reservada y no es accesible para el empleador.
        </p>
        <Link href="/portal-empresa/epidemiologia"
          className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-700 transition hover:bg-gray-200">
          📊 Condiciones de salud
        </Link>
        {conceptos && conceptos.length > 0 && (
          <button onClick={() => imprimirConceptosLote(conceptos)}
            className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-teal-700">
            ⬇ Descargar todos (PDF)
          </button>
        )}
      </div>
      {conceptos === null ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : conceptos.length === 0 ? (
        <p className="text-sm text-gray-500">Aún no hay conceptos firmados disponibles.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-white text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3">Trabajador</th>
                <th className="px-4 py-3">Concepto</th>
                <th className="px-4 py-3">Restricciones</th>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Profesional</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {conceptos.map((c) => {
                const ap = APTITUD_UI[c.aptitud] ?? APTITUD_UI.aplazado;
                return (
                  <tr key={c.id} className="bg-gray-100">
                    <td className="px-4 py-3 font-medium text-gray-900">{c.trabajador_nombre}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ap.clase}`}>
                        {ap.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{c.restricciones || "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{c.fecha_emision ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{c.profesional_nombre}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => imprimirConcepto(c)}
                        className="rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-100">
                        🖨 PDF
                      </button>
                    </td>
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
