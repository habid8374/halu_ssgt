"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Alerta {
  id: number;
  tipo: string;
  mensaje: string;
  vence: string;
  vencida: boolean;
  resuelta: boolean;
}

const TIPO_UI: Record<string, string> = {
  furat: "FURAT · 2 días hábiles",
  furel: "FUREL · 2 días hábiles",
  adaptacion: "Adaptación · 20 días hábiles",
  investigacion: "Investigación",
};

/** Bandeja de alertas de plazos normativos (generadas por Celery beat). */
export default function AlertasPage() {
  const [alertas, setAlertas] = useState<Alerta[] | null>(null);

  const cargar = useCallback(async () => {
    setAlertas(await apiFetch<Alerta[]>("/alertas/?abiertas=1"));
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function resolver(a: Alerta) {
    await apiFetch(`/alertas/${a.id}/resolver/`, { method: "POST" });
    void cargar();
  }

  return (
    <AppShell titulo="Alertas de plazos normativos">
      <p className="mb-4 text-xs text-gray-500">
        FURAT/FUREL: reporte a la ARL en máximo 2 días hábiles. Adaptación de
        condiciones: 20 días hábiles desde la recomendación (Res. 1843/2025).
        Las alertas se generan automáticamente cada hora.
      </p>
      {alertas === null ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : alertas.length === 0 ? (
        <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          ✓ Sin alertas abiertas: todos los plazos al día.
        </p>
      ) : (
        <div className="space-y-2">
          {alertas.map((a) => (
            <article key={a.id}
              className={`flex flex-wrap items-center gap-4 rounded-xl border px-4 py-3 ${
                a.vencida ? "border-red-300 bg-red-50" : "border-amber-300 bg-amber-50"
              }`}>
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${
                a.vencida ? "bg-red-600 text-white" : "bg-amber-500 text-white"
              }`}>
                {a.vencida ? "Vencida" : "Por vencer"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{a.mensaje}</p>
                <p className="text-xs text-gray-500">{TIPO_UI[a.tipo] ?? a.tipo} · vence {a.vence}</p>
              </div>
              <button onClick={() => resolver(a)}
                className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 shadow-sm ring-1 ring-gray-300 transition hover:bg-gray-50">
                Marcar resuelta
              </button>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  );
}
