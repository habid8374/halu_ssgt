"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import Tablero from "@/components/Tablero";
import { type Yo } from "@/lib/api";

/**
 * Tablero de flujo para recepción: todas las atenciones de SU sede,
 * con acciones de transición (registrar llegada, llamar, etc.).
 */
export default function RecepcionPage() {
  const [sede, setSede] = useState<number | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("halu_yo");
    if (raw) {
      const yo = JSON.parse(raw) as Yo;
      setSede(yo.sede ?? 1);
    }
  }, []);

  return (
    <AppShell titulo="Recepción — Tablero de flujo">
      {sede !== null ? (
        <Tablero sedeId={sede} />
      ) : (
        <p className="text-sm text-gray-500">Cargando…</p>
      )}
    </AppShell>
  );
}
