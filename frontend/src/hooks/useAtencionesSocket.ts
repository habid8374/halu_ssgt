"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl, getSesion } from "@/lib/api";

/**
 * Suscripción al tablero de flujo en tiempo real (Django Channels).
 * Reconexión automática con backoff simple. Nunca polling (CLAUDE.md §2).
 */
export interface EventoAtencion {
  type: "atencion" | "llamado" | "conectado";
  atencion_id?: number;
  estado_anterior?: string | null;
  estado_nuevo?: string;
  sede_id?: number;
  consultorio_id?: number | null;
  consultorio_nombre?: string | null;
  trabajador_nombre?: string;
  timestamp?: string;
}

export function useAtencionesSocket(
  sedeId: number,
  onEvento: (e: EventoAtencion) => void,
) {
  const [conectado, setConectado] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onEventoRef = useRef(onEvento);
  onEventoRef.current = onEvento;

  const conectar = useCallback(() => {
    const sesion = getSesion();
    const token = sesion ? `?token=${sesion.access}` : "";
    const ws = new WebSocket(`${wsUrl()}/tablero/${sedeId}/${token}`);
    wsRef.current = ws;

    ws.onopen = () => setConectado(true);
    ws.onclose = () => {
      setConectado(false);
      // Reconexión: el socket puede caerse por reinicios del backend.
      setTimeout(() => {
        if (wsRef.current === ws) conectar();
      }, 3000);
    };
    ws.onmessage = (msg) => {
      onEventoRef.current(JSON.parse(msg.data) as EventoAtencion);
    };
  }, [sedeId]);

  useEffect(() => {
    conectar();
    return () => {
      const ws = wsRef.current;
      wsRef.current = null; // evita la reconexión tras desmontar
      ws?.close();
    };
  }, [conectar]);

  return { conectado };
}
