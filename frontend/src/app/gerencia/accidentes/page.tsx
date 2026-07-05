"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Reporte {
  estado: string;
  fecha_limite: string;
  radicado_arl: string;
}
interface Accidente {
  id: number;
  tipo_evento: string;
  trabajador_nombre: string;
  empresa_nombre: string;
  fecha_evento: string;
  gravedad: string;
  descripcion: string;
  reporte: Reporte | null;
}
interface Trabajador {
  id: number;
  nombres: string;
  apellidos: string;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/** Registro y seguimiento de accidentes de trabajo / enfermedad laboral. */
export default function AccidentesPage() {
  const [items, setItems] = useState<Accidente[]>([]);
  const [numDoc, setNumDoc] = useState("");
  const [trabajador, setTrabajador] = useState<Trabajador | null>(null);
  const [tipoEvento, setTipoEvento] = useState("accidente");
  const [fecha, setFecha] = useState("");
  const [gravedad, setGravedad] = useState("leve");
  const [descripcion, setDescripcion] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setItems(await apiFetch<Accidente[]>("/accidentes/"));
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function buscar() {
    setTrabajador(null);
    const res = await apiFetch<Trabajador[]>(`/trabajadores/?documento=${numDoc.trim()}`).catch(() => []);
    if (res.length) setTrabajador(res[0]);
    else setMsg("Trabajador no encontrado (regístralo en Admisión).");
  }

  async function registrar(e: React.FormEvent) {
    e.preventDefault();
    if (!trabajador) return;
    setMsg(null);
    try {
      await apiFetch("/accidentes/", {
        method: "POST",
        body: JSON.stringify({
          tipo_evento: tipoEvento, trabajador: trabajador.id,
          fecha_evento: fecha, gravedad, descripcion,
        }),
      });
      setNumDoc(""); setTrabajador(null); setFecha(""); setDescripcion("");
      void cargar();
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  async function marcarEnviado(a: Accidente) {
    const radicado = window.prompt("Número de radicado de la ARL:") ?? "";
    await apiFetch(`/accidentes/${a.id}/marcar_enviado/`, {
      method: "POST",
      body: JSON.stringify({ radicado }),
    });
    void cargar();
  }

  return (
    <AppShell titulo="Accidentes de trabajo y enfermedad laboral">
      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <form onSubmit={registrar} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Registrar evento</h2>
          <label className={labelCls}>
            Documento del trabajador
            <div className="flex gap-2">
              <input value={numDoc} onChange={(e) => setNumDoc(e.target.value)} className={inputCls} />
              <button type="button" onClick={buscar}
                className="mt-1 rounded-lg bg-gray-200 px-4 text-sm font-semibold text-gray-900 hover:bg-gray-300">
                Buscar
              </button>
            </div>
          </label>
          {trabajador && (
            <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-600">
              {trabajador.nombres} {trabajador.apellidos}
            </p>
          )}
          <label className={`${labelCls} mt-3`}>
            Tipo de evento
            <select value={tipoEvento} onChange={(e) => setTipoEvento(e.target.value)} className={inputCls}>
              <option value="accidente">Accidente de trabajo (FURAT)</option>
              <option value="enfermedad">Enfermedad laboral (FUREL)</option>
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Fecha del evento
            <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className={inputCls} required />
          </label>
          <label className={`${labelCls} mt-3`}>
            Gravedad
            <select value={gravedad} onChange={(e) => setGravedad(e.target.value)} className={inputCls}>
              <option value="leve">Leve</option>
              <option value="grave">Grave</option>
              <option value="mortal">Mortal</option>
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Descripción
            <textarea rows={3} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} className={inputCls} required />
          </label>
          {msg && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{msg}</p>}
          <button type="submit" disabled={!trabajador}
            className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-40">
            Registrar (crea el reporte ARL con plazo de 2 días hábiles)
          </button>
        </form>

        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">
            Eventos registrados ({items.length})
          </h2>
          <div className="space-y-2">
            {items.map((a) => (
              <article key={a.id} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase text-white ${
                    a.tipo_evento === "accidente" ? "bg-red-500" : "bg-orange-500"
                  }`}>
                    {a.tipo_evento === "accidente" ? "FURAT" : "FUREL"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900">{a.trabajador_nombre}</p>
                    <p className="text-xs text-gray-500">
                      {a.empresa_nombre} · {a.fecha_evento} · gravedad {a.gravedad}
                    </p>
                  </div>
                  {a.reporte && (
                    a.reporte.estado === "enviado" ? (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-600">
                        ✓ Enviado a ARL {a.reporte.radicado_arl && `· ${a.reporte.radicado_arl}`}
                      </span>
                    ) : (
                      <>
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                          Pendiente · límite {a.reporte.fecha_limite}
                        </span>
                        <button onClick={() => marcarEnviado(a)}
                          className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700">
                          Marcar enviado
                        </button>
                      </>
                    )
                  )}
                </div>
                <p className="mt-2 text-xs text-gray-600">{a.descripcion}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
