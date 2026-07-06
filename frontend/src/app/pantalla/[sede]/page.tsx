"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useState } from "react";
import { useAtencionesSocket, type EventoAtencion } from "@/hooks/useAtencionesSocket";
import { campanilla, anunciar, activarAudio } from "@/lib/aviso";

interface Llamado {
  atencion_id: number;
  trabajador_nombre: string;
  consultorio_nombre: string | null;
  timestamp: string;
}

/**
 * Pantalla pública de sala de espera (TV de la sede). Conexión anónima:
 * el backend solo le envía eventos de LLAMADO (nombre + consultorio),
 * ningún otro dato (separación por diseño).
 */
export default function PantallaPage({ params }: { params: { sede: string } }) {
  const [llamados, setLlamados] = useState<Llamado[]>([]);
  const [audio, setAudio] = useState(false);

  const onEvento = useCallback((e: EventoAtencion) => {
    if (e.type === "llamado" && e.trabajador_nombre) {
      setLlamados((prev) =>
        [
          {
            atencion_id: e.atencion_id!,
            trabajador_nombre: e.trabajador_nombre!,
            consultorio_nombre: e.consultorio_nombre ?? null,
            timestamp: e.timestamp ?? new Date().toISOString(),
          },
          ...prev.filter((l) => l.atencion_id !== e.atencion_id),
        ].slice(0, 6),
      );
      // Campanilla + anuncio por voz (si el operador activó el sonido).
      campanilla();
      const destino = e.consultorio_nombre ? `. Pase a ${e.consultorio_nombre}` : "";
      anunciar(`${e.trabajador_nombre}${destino}`);
    }
  }, []);

  const { conectado } = useAtencionesSocket(Number(params.sede), onEvento);
  const actual = llamados[0];

  return (
    <main className="flex min-h-screen flex-col bg-slate-950 p-8 text-white">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="Halu" className="h-11 w-auto" />
          <p className="text-lg font-bold">Halu Salud Ocupacional</p>
        </div>
        <div className="flex items-center gap-4">
          {!audio && (
            <button
              onClick={() => { activarAudio(); setAudio(true); campanilla(); anunciar("Sonido activado"); }}
              className="rounded-lg bg-teal-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-400"
            >
              🔊 Activar sonido
            </button>
          )}
          <span className={`flex items-center gap-2 text-sm ${conectado ? "text-emerald-400" : "text-red-400"}`}>
            <span className={`h-2.5 w-2.5 rounded-full ${conectado ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
            {conectado ? "En vivo" : "Reconectando…"}
          </span>
        </div>
      </header>

      <section className="flex flex-1 flex-col items-center justify-center">
        <AnimatePresence mode="wait">
          {actual ? (
            <motion.div
              key={actual.atencion_id}
              initial={{ opacity: 0, y: 40, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -40 }}
              className="text-center"
            >
              <p className="text-2xl uppercase tracking-[0.3em] text-teal-400">Turno llamado</p>
              <p className="mt-6 text-7xl font-black">{actual.trabajador_nombre}</p>
              {actual.consultorio_nombre && (
                <p className="mt-6 text-4xl font-semibold text-slate-300">
                  → {actual.consultorio_nombre}
                </p>
              )}
            </motion.div>
          ) : (
            <motion.p key="vacio" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-3xl text-slate-600">
              Esperando llamados…
            </motion.p>
          )}
        </AnimatePresence>
      </section>

      {llamados.length > 1 && (
        <footer className="border-t border-slate-800 pt-4">
          <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">Llamados recientes</p>
          <div className="flex gap-6">
            {llamados.slice(1).map((l) => (
              <p key={l.atencion_id} className="text-sm text-slate-400">
                {l.trabajador_nombre}
                {l.consultorio_nombre ? ` · ${l.consultorio_nombre}` : ""}
              </p>
            ))}
          </div>
        </footer>
      )}
    </main>
  );
}
