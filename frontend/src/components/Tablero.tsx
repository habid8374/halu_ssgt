"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  ESTADOS,
  ESTADO_LABEL,
  SIGUIENTES,
  TIPO_EXAMEN_LABEL,
  type Atencion,
  type Estado,
} from "@/lib/api";
import { useAtencionesSocket, type EventoAtencion } from "@/hooks/useAtencionesSocket";

// Colores del semáforo por estado (tarjeta y columna).
const COLOR: Record<Estado, { borde: string; fondo: string; punto: string }> = {
  registrado: { borde: "border-gray-300", fondo: "bg-gray-100", punto: "bg-slate-400" },
  espera: { borde: "border-amber-500/40", fondo: "bg-amber-50", punto: "bg-amber-400" },
  llamado: { borde: "border-blue-500/40", fondo: "bg-blue-500/10", punto: "bg-blue-400" },
  atencion: { borde: "border-violet-500/40", fondo: "bg-violet-500/10", punto: "bg-violet-400" },
  paraclinicos: { borde: "border-cyan-500/40", fondo: "bg-cyan-500/10", punto: "bg-cyan-400" },
  finalizado: { borde: "border-emerald-500/40", fondo: "bg-emerald-50", punto: "bg-emerald-400" },
};

const ACCION_LABEL: Record<Estado, string> = {
  registrado: "Registrar",
  espera: "A espera",
  llamado: "Llamar",
  atencion: "Iniciar atención",
  paraclinicos: "A paraclínicos",
  finalizado: "Finalizar",
};

function MinutosEn({ desde }: { desde: string }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);
  const min = Math.max(0, Math.round((Date.now() - new Date(desde).getTime()) / 60_000));
  const alerta = min >= 30 ? "text-red-600" : min >= 15 ? "text-amber-700" : "text-gray-500";
  return <span className={`text-[11px] tabular-nums ${alerta}`}>{min} min</span>;
}

export default function Tablero({
  sedeId,
  soloLectura = false,
  hrefAtencion,
}: {
  sedeId: number;
  soloLectura?: boolean;
  /** Si se define, cada tarjeta muestra "Abrir" hacia esa ruta (vista médico). */
  hrefAtencion?: (id: number) => string;
}) {
  const [atenciones, setAtenciones] = useState<Atencion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const data = await apiFetch<Atencion[]>(`/atenciones/?sede=${sedeId}`);
      setAtenciones(data);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [sedeId]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // Cambios de estado llegan por WebSocket: recargamos la atención afectada
  // desde la API (fuente de verdad) sin polling.
  const onEvento = useCallback(
    (e: EventoAtencion) => {
      if (e.type === "atencion") void cargar();
    },
    [cargar],
  );
  const { conectado } = useAtencionesSocket(sedeId, onEvento);

  async function transicionar(a: Atencion, estado: Estado) {
    // Optimista: la confirmación llega por el WS.
    setAtenciones((prev) => prev.map((x) => (x.id === a.id ? { ...x, estado } : x)));
    try {
      await apiFetch(`/atenciones/${a.id}/transicion/`, {
        method: "POST",
        body: JSON.stringify({ estado }),
      });
    } catch {
      void cargar(); // revertir con el estado real
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-2 text-xs">
        <span className={`h-2 w-2 rounded-full ${conectado ? "bg-emerald-400" : "bg-red-400"}`} />
        <span className="text-gray-500">
          {conectado ? "Tiempo real conectado" : "Reconectando…"}
        </span>
        {error && <span className="text-red-600">· {error}</span>}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {ESTADOS.map((estado) => {
          const items = atenciones.filter((a) => a.estado === estado);
          const c = COLOR[estado];
          return (
            <section key={estado} className={`rounded-xl border ${c.borde} ${c.fondo} p-2`}>
              <header className="mb-2 flex items-center justify-between px-1">
                <div className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${c.punto}`} />
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-700">
                    {ESTADO_LABEL[estado]}
                  </h2>
                </div>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-bold text-gray-600">
                  {items.length}
                </span>
              </header>

              <div className="flex min-h-[60px] flex-col gap-2">
                <AnimatePresence mode="popLayout">
                  {items.map((a) => (
                    <motion.article
                      key={a.id}
                      layout
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                      className="rounded-lg border border-gray-200 bg-white p-2.5 shadow-sm"
                    >
                      <p className="truncate text-sm font-semibold text-gray-900">{a.trabajador_nombre}</p>
                      <p className="truncate text-[11px] text-gray-500">{a.empresa_nombre}</p>
                      <div className="mt-1.5 flex items-center justify-between">
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">
                          {TIPO_EXAMEN_LABEL[a.tipo_examen] ?? a.tipo_examen}
                        </span>
                        <MinutosEn desde={a.estado_actualizado_at} />
                      </div>
                      {(hrefAtencion || (!soloLectura && SIGUIENTES[a.estado].length > 0)) && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {hrefAtencion && (
                            <a
                              href={hrefAtencion(a.id)}
                              className="rounded-md bg-violet-50 px-2 py-1 text-[11px] font-semibold text-violet-700 transition hover:bg-violet-100"
                            >
                              Abrir atención
                            </a>
                          )}
                          {!soloLectura &&
                            SIGUIENTES[a.estado].map((sig) => (
                              <button
                                key={sig}
                                onClick={() => transicionar(a, sig)}
                                className="rounded-md bg-teal-50 px-2 py-1 text-[11px] font-semibold text-teal-700 transition hover:bg-teal-100"
                              >
                                {ACCION_LABEL[sig]}
                              </button>
                            ))}
                        </div>
                      )}
                    </motion.article>
                  ))}
                </AnimatePresence>
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
