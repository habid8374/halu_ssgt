"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import TarjetaPrueba, { type Prueba } from "@/components/pruebas/TarjetaPrueba";

const ESTACIONES = [
  ["", "Todas"], ["visiometria", "Visiometría"], ["audiometria", "Audiometría"],
  ["espirometria", "Espirometría"], ["laboratorio", "Laboratorio"], ["otro", "Otro paraclínico"],
] as const;

/**
 * Cola por estación (rol técnico de apoyo diagnóstico). Muestra las pruebas
 * pendientes de su sede; el técnico las resuelve (digita/adjunta) y marca hechas.
 */
export default function EstacionesPage() {
  const [pruebas, setPruebas] = useState<Prueba[]>([]);
  const [tipo, setTipo] = useState("");
  const [verHechas, setVerHechas] = useState(false);

  const cargar = useCallback(async () => {
    setPruebas(await apiFetch<Prueba[]>("/pruebas/"));
  }, []);
  useEffect(() => { void cargar(); }, [cargar]);

  const lista = useMemo(() => pruebas
    .filter((p) => !tipo || p.tipo_prueba === tipo)
    .filter((p) => verHechas || p.estado === "pendiente" || p.estado === "en_proceso"),
    [pruebas, tipo, verHechas]);

  const pendientesPorTipo = useMemo(() => {
    const c: Record<string, number> = {};
    pruebas.forEach((p) => { if (p.estado === "pendiente" || p.estado === "en_proceso") c[p.tipo_prueba] = (c[p.tipo_prueba] ?? 0) + 1; });
    return c;
  }, [pruebas]);

  return (
    <AppShell titulo="Estaciones — mi cola de pruebas">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {ESTACIONES.map(([v, l]) => (
          <button key={v} onClick={() => setTipo(v)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              tipo === v ? "bg-teal-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
            {l}{v && pendientesPorTipo[v] ? ` (${pendientesPorTipo[v]})` : ""}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={verHechas} onChange={(e) => setVerHechas(e.target.checked)} />
          Ver también realizadas
        </label>
      </div>

      <div className="space-y-2">
        {lista.map((p) => (
          <TarjetaPrueba key={p.id} prueba={p} onCambio={cargar} mostrarPaciente />
        ))}
        {lista.length === 0 && (
          <p className="rounded-xl border border-dashed border-gray-300 px-4 py-10 text-center text-sm text-gray-400">
            No hay pruebas pendientes en tu cola. 🎉
          </p>
        )}
      </div>
    </AppShell>
  );
}
