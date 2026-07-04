"use client";

import { useAtencionesSocket } from "@/hooks/useAtencionesSocket";

/**
 * Pantalla pública de sala de espera (por sede). Muestra llamados de pacientes
 * en tiempo real. Vista pública: sin datos clínicos, solo turno/estado.
 */
export default function PantallaPage({
  params,
}: {
  params: { sede: string };
}) {
  const { conectado } = useAtencionesSocket(Number(params.sede));
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <h1 className="text-3xl font-bold">Sede {params.sede}</h1>
      <p className="mt-2 text-sm opacity-60">
        {conectado ? "En vivo" : "Reconectando…"}
      </p>
    </main>
  );
}
