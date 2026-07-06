"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import TarjetaPrueba, { type Prueba } from "@/components/pruebas/TarjetaPrueba";

/**
 * Circuito de pruebas de la atención (vista del médico). Muestra el estado de
 * cada estación; el médico también puede digitar/adjuntar resultados.
 */
export default function PruebasSection({ atencionId }: { atencionId: number }) {
  const [pruebas, setPruebas] = useState<Prueba[]>([]);

  const cargar = useCallback(async () => {
    setPruebas(await apiFetch<Prueba[]>(`/pruebas/?atencion=${atencionId}`));
  }, [atencionId]);
  useEffect(() => { void cargar(); }, [cargar]);

  const total = pruebas.length;
  const hechas = pruebas.filter((p) => p.estado === "realizada" || p.estado === "no_aplica").length;

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-teal-600">
          Circuito de pruebas (paraclínicos)
        </h2>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${hechas === total && total ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          {hechas}/{total} realizadas
        </span>
      </div>
      <div className="space-y-2">
        {pruebas.map((p) => <TarjetaPrueba key={p.id} prueba={p} onCambio={cargar} />)}
        {total === 0 && <p className="text-sm text-gray-400">Sin pruebas en el circuito.</p>}
      </div>
    </section>
  );
}
