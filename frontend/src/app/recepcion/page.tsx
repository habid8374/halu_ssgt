"use client";

import { useAtencionesSocket } from "@/hooks/useAtencionesSocket";

/**
 * Tablero de flujo (kanban por colores) para recepción.
 * Rol `recepcion`: ve todas las atenciones de su sede; NO ve historia clínica.
 * Las tarjetas se renderizarán como columnas por estado con Framer Motion (paso 5).
 */
export default function RecepcionPage() {
  const { conectado } = useAtencionesSocket(1);
  return (
    <main className="p-6">
      <h1 className="text-xl font-bold">Recepción — Tablero de flujo</h1>
      <p className="mt-1 text-sm text-gray-500">
        WebSocket: {conectado ? "conectado" : "desconectado"}
      </p>
      <p className="mt-4 text-sm">
        Columnas del tablero (registrado → espera → llamado → atención →
        paraclínicos → finalizado) se implementan en el paso 5.
      </p>
    </main>
  );
}
