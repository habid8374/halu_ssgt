"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import Tablero from "@/components/Tablero";
import { type Yo } from "@/lib/api";

/**
 * Cola del médico ocupacional. El backend limita el queryset a las
 * atenciones asignadas a este profesional (matriz §4) — aquí solo se
 * renderiza lo que la API permite ver.
 */
export default function ConsultorioPage() {
  const [sede, setSede] = useState<number | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem("halu_yo");
    if (raw) {
      const yo = JSON.parse(raw) as Yo;
      setSede(yo.sede ?? 1);
    }
  }, []);

  return (
    <AppShell titulo="Consultorio — Mi cola de atención">
      {sede !== null ? (
        <Tablero sedeId={sede} hrefAtencion={(id) => `/consultorio/atencion/${id}`} />
      ) : (
        <p className="text-sm text-slate-400">Cargando…</p>
      )}
    </AppShell>
  );
}
