"use client";

import { useState } from "react";
import AppShell from "@/components/AppShell";
import Tablero from "@/components/Tablero";

/**
 * Vista de coordinación/gerencia: tablero de TODAS las sedes (matriz §4),
 * en solo lectura. Los reportes agregados llegan en una fase posterior.
 */
export default function GerenciaPage() {
  const [sede, setSede] = useState(1);

  return (
    <AppShell titulo="Gerencia — Tablero de sedes">
      <div className="mb-4 flex items-center gap-2">
        <label className="text-xs text-gray-500">Sede:</label>
        <select
          value={sede}
          onChange={(e) => setSede(Number(e.target.value))}
          className="rounded-lg border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900"
        >
          <option value={1}>Sede Principal</option>
        </select>
        <span className="text-xs text-gray-500">· Vista de solo lectura</span>
      </div>
      <Tablero sedeId={sede} soloLectura />
    </AppShell>
  );
}
