"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch, TIPO_EXAMEN_LABEL, type Yo } from "@/lib/api";

interface Cita {
  id: number;
  trabajador_nombre: string;
  empresa_nombre: string;
  tipo_examen: string;
  fecha_hora: string;
  estado: string;
  profesional_nombre: string | null;
  nota: string;
}
interface Trabajador {
  id: number;
  nombres: string;
  apellidos: string;
}
interface Medico {
  id: number;
  nombre_completo: string;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Agenda (rol recepción): programa citas y las "admite" cuando el trabajador
 * llega — eso crea la Atención y la manda al tablero. El trabajador debe
 * existir (si es nuevo, se registra primero en Admisión).
 */
export default function AgendaPage() {
  const router = useRouter();
  const [sede, setSede] = useState<number | null>(null);
  const [citas, setCitas] = useState<Cita[]>([]);
  const [medicos, setMedicos] = useState<Medico[]>([]);

  const [numDoc, setNumDoc] = useState("");
  const [trabajador, setTrabajador] = useState<Trabajador | null>(null);
  const [buscado, setBuscado] = useState(false);
  const [tipoExamen, setTipoExamen] = useState("periodico");
  const [fechaHora, setFechaHora] = useState("");
  const [medicoId, setMedicoId] = useState("");
  const [nota, setNota] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; texto: string } | null>(null);

  const cargar = useCallback(async () => {
    setCitas(await apiFetch<Cita[]>("/citas/?pendientes=1"));
  }, []);

  useEffect(() => {
    const raw = localStorage.getItem("halu_yo");
    if (!raw) return;
    setSede((JSON.parse(raw) as Yo).sede ?? 1);
    void cargar();
    void apiFetch<Medico[]>("/medicos/").then((ms) => {
      setMedicos(ms);
      if (ms.length === 1) setMedicoId(String(ms[0].id));
    });
  }, [cargar]);

  async function buscar() {
    setBuscado(false);
    setTrabajador(null);
    if (!numDoc.trim()) return;
    const res = await apiFetch<Trabajador[]>(`/trabajadores/?documento=${numDoc.trim()}`);
    setBuscado(true);
    if (res.length) setTrabajador(res[0]);
  }

  async function programar(e: React.FormEvent) {
    e.preventDefault();
    if (!trabajador) return;
    setMsg(null);
    try {
      await apiFetch("/citas/", {
        method: "POST",
        body: JSON.stringify({
          trabajador: trabajador.id,
          sede,
          tipo_examen: tipoExamen,
          fecha_hora: new Date(fechaHora).toISOString(),
          profesional_asignado: medicoId ? Number(medicoId) : null,
          nota,
        }),
      });
      setMsg({ ok: true, texto: "Cita programada." });
      setNumDoc("");
      setTrabajador(null);
      setBuscado(false);
      setFechaHora("");
      setNota("");
      void cargar();
    } catch (err) {
      setMsg({ ok: false, texto: (err as Error).message });
    }
  }

  async function admitir(cita: Cita) {
    try {
      await apiFetch(`/citas/${cita.id}/admitir/`, { method: "POST" });
      router.push("/recepcion"); // la atención ya está en el tablero
    } catch (err) {
      setMsg({ ok: false, texto: (err as Error).message });
    }
  }

  async function cancelar(cita: Cita) {
    await apiFetch(`/citas/${cita.id}/cancelar/`, { method: "POST" });
    void cargar();
  }

  return (
    <AppShell titulo="Agenda — Citas programadas">
      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        {/* ----------------------------- Programar ----------------------------- */}
        <form onSubmit={programar} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Programar cita</h2>

          <label className={labelCls}>
            Documento del trabajador
            <div className="flex gap-2">
              <input value={numDoc} onChange={(e) => setNumDoc(e.target.value)} className={inputCls} placeholder="1010101010" />
              <button type="button" onClick={buscar}
                className="mt-1 rounded-lg bg-gray-200 px-4 text-sm font-semibold text-gray-900 transition hover:bg-gray-300">
                Buscar
              </button>
            </div>
          </label>
          {buscado && (
            <p className={`mt-2 rounded-lg px-3 py-2 text-xs ${trabajador ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-700"}`}>
              {trabajador
                ? `${trabajador.nombres} ${trabajador.apellidos}`
                : "No existe. Regístralo primero en Admisión."}
            </p>
          )}

          <label className={`${labelCls} mt-3`}>
            Tipo de examen
            <select value={tipoExamen} onChange={(e) => setTipoExamen(e.target.value)} className={inputCls}>
              {Object.entries(TIPO_EXAMEN_LABEL).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Fecha y hora
            <input type="datetime-local" value={fechaHora} onChange={(e) => setFechaHora(e.target.value)} className={inputCls} required />
          </label>
          <label className={`${labelCls} mt-3`}>
            Médico
            <select value={medicoId} onChange={(e) => setMedicoId(e.target.value)} className={inputCls} required>
              <option value="">Seleccionar…</option>
              {medicos.map((m) => (
                <option key={m.id} value={m.id}>{m.nombre_completo}</option>
              ))}
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Nota
            <input value={nota} onChange={(e) => setNota(e.target.value)} className={inputCls} placeholder="Opcional" />
          </label>

          {msg && (
            <p className={`mt-3 rounded-lg px-3 py-2 text-xs ${msg.ok ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"}`}>
              {msg.texto}
            </p>
          )}

          <button type="submit" disabled={!trabajador}
            className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-40">
            Programar
          </button>
        </form>

        {/* ------------------------- Citas pendientes -------------------------- */}
        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">
            Pendientes ({citas.length})
          </h2>
          {citas.length === 0 ? (
            <p className="text-sm text-gray-500">No hay citas pendientes.</p>
          ) : (
            <div className="space-y-2">
              {citas.map((c) => (
                <article key={c.id}
                  className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white px-4 py-3">
                  <div className="w-36">
                    <p className="text-sm font-bold text-gray-900">
                      {new Date(c.fecha_hora).toLocaleDateString("es-CO", { day: "2-digit", month: "short" })}
                    </p>
                    <p className="text-xs text-teal-600">
                      {new Date(c.fecha_hora).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-gray-900">{c.trabajador_nombre}</p>
                    <p className="truncate text-xs text-gray-500">
                      {c.empresa_nombre} · {TIPO_EXAMEN_LABEL[c.tipo_examen] ?? c.tipo_examen}
                      {c.profesional_nombre ? ` · ${c.profesional_nombre}` : ""}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => admitir(c)}
                      className="rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-100">
                      Llegó — Admitir
                    </button>
                    <button onClick={() => cancelar(c)}
                      className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-600 transition hover:bg-red-100">
                      Cancelar
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
