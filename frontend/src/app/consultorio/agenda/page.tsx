"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch, TIPO_EXAMEN_LABEL } from "@/lib/api";

interface Cita {
  id: number;
  trabajador_nombre: string;
  empresa_nombre: string;
  tipo_examen: string;
  fecha_hora: string;
  estado: string;
}

const ESTADO_COLOR: Record<string, string> = {
  programada: "bg-amber-50 text-amber-700",
  confirmada: "bg-blue-50 text-blue-700",
  cumplida: "bg-emerald-50 text-emerald-700",
  cancelada: "bg-gray-100 text-gray-500",
};

/**
 * Agenda del médico (solo lectura): sus próximas citas. La programación la
 * gestiona recepción; aquí el profesional consulta lo que tiene asignado.
 */
export default function AgendaMedicoPage() {
  const [citas, setCitas] = useState<Cita[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Cita[]>("/citas/")
      .then((cs) => setCitas([...cs].sort((a, b) => (a.fecha_hora < b.fecha_hora ? -1 : 1))))
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <AppShell titulo="Mi agenda">
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="space-y-2">
        {citas.map((c) => {
          const f = new Date(c.fecha_hora);
          return (
            <article key={c.id} className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white px-4 py-3">
              <div className="w-32 shrink-0">
                <p className="text-sm font-bold text-gray-900">
                  {f.toLocaleDateString("es-CO", { day: "2-digit", month: "short" })}
                </p>
                <p className="text-xs text-gray-500">{f.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-gray-900">{c.trabajador_nombre}</p>
                <p className="text-xs text-gray-500">{c.empresa_nombre} · {TIPO_EXAMEN_LABEL[c.tipo_examen] ?? c.tipo_examen}</p>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ESTADO_COLOR[c.estado] ?? "bg-gray-100 text-gray-600"}`}>
                {c.estado}
              </span>
            </article>
          );
        })}
        {citas.length === 0 && (
          <p className="rounded-xl border border-dashed border-gray-300 px-4 py-10 text-center text-sm text-gray-400">
            No tiene citas asignadas.
          </p>
        )}
      </div>
    </AppShell>
  );
}
