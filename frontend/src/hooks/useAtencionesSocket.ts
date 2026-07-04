"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";

/**
 * Suscripción al tablero de flujo en tiempo real (Channels).
 *
 * Se conecta al consumer de Django Channels por sede. El contrato del evento
 * (forma exacta del payload de cambio de estado) se cierra en el paso 5, junto
 * con el TableroConsumer. Este hook establece la estructura: conexión, reconexión
 * y acumulación de eventos — sin polling (CLAUDE.md §2).
 */
export interface EventoAtencion {
  atencion_id: number;
  estado_anterior: string | null;
  estado_nuevo: string;
  sede_id: number;
  consultorio_id: number | null;
  timestamp: string;
}

export function useAtencionesSocket(sedeId: number) {
  const [eventos, setEventos] = useState<EventoAtencion[]>([]);
  const [conectado, setConectado] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/tablero/${sedeId}/`);
    wsRef.current = ws;

    ws.onopen = () => setConectado(true);
    ws.onclose = () => setConectado(false);
    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data) as EventoAtencion;
      setEventos((prev) => [...prev, data]);
    };

    return () => ws.close();
  }, [sedeId]);

  return { eventos, conectado };
}
