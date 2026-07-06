"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch, ESTADO_LABEL, TIPO_EXAMEN_LABEL, type Atencion, type Estado, type Yo } from "@/lib/api";
import { imprimirHistoriaCompleta } from "@/lib/historiaPdf";

const norm = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

const inputCls =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-[11px] font-medium uppercase tracking-wide text-gray-500";

/**
 * Historias clínicas del médico: todas sus atenciones (activas y finalizadas),
 * con búsqueda. El backend limita el queryset a sus pacientes asignados (§4).
 * Abrir lleva a la atención completa (historia, diagnósticos, órdenes, recetas).
 */
export default function HistoriasPage() {
  const [atenciones, setAtenciones] = useState<Atencion[]>([]);
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [soloFinalizadas, setSoloFinalizadas] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [medicoNombre, setMedicoNombre] = useState("");

  useEffect(() => {
    apiFetch<Atencion[]>("/atenciones/")
      .then(setAtenciones)
      .catch((e) => setError((e as Error).message));
    const raw = typeof window !== "undefined" ? localStorage.getItem("halu_yo") : null;
    if (raw) setMedicoNombre((JSON.parse(raw) as Yo).nombre_completo ?? "");
  }, []);

  function limpiar() {
    setQ(""); setTipo(""); setDesde(""); setHasta(""); setSoloFinalizadas(false);
  }

  const lista = useMemo(() => {
    const t = norm(q.trim());
    return atenciones
      .filter((a) => (soloFinalizadas ? a.estado === "finalizado" : true))
      .filter((a) => !tipo || a.tipo_examen === tipo)
      .filter((a) => {
        const f = a.created_at.slice(0, 10); // YYYY-MM-DD
        if (desde && f < desde) return false;
        if (hasta && f > hasta) return false;
        return true;
      })
      .filter((a) =>
        !t ||
        norm(a.trabajador_nombre).includes(t) ||
        norm(a.empresa_nombre ?? "").includes(t) ||
        (a.trabajador_documento ?? "").includes(q.trim()),
      )
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
  }, [atenciones, q, tipo, desde, hasta, soloFinalizadas]);

  return (
    <AppShell titulo="Historias clínicas — Mis pacientes">
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className={`${labelCls} sm:col-span-2`}>Buscar (paciente, documento o empresa)
            <input value={q} onChange={(e) => setQ(e.target.value)} className={`${inputCls} mt-1`}
              placeholder="Nombre, N.º de documento o empresa…" />
          </label>
          <label className={labelCls}>Tipo de examen
            <select value={tipo} onChange={(e) => setTipo(e.target.value)} className={`${inputCls} mt-1`}>
              <option value="">Todos</option>
              {Object.entries(TIPO_EXAMEN_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={labelCls}>Estado
            <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={soloFinalizadas} onChange={(e) => setSoloFinalizadas(e.target.checked)} />
              Solo finalizadas
            </div>
          </label>
          <label className={labelCls}>Desde
            <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className={`${inputCls} mt-1`} />
          </label>
          <label className={labelCls}>Hasta
            <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className={`${inputCls} mt-1`} />
          </label>
          <div className="flex items-end gap-3">
            <button onClick={limpiar} className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-semibold text-gray-600 transition hover:bg-gray-200">
              Limpiar
            </button>
            <span className="text-xs text-gray-400">{lista.length} atenciones</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-4 py-2 font-medium">Paciente</th>
              <th className="px-4 py-2 font-medium">Documento</th>
              <th className="px-4 py-2 font-medium">Empresa</th>
              <th className="px-4 py-2 font-medium">Examen</th>
              <th className="px-4 py-2 font-medium">Estado</th>
              <th className="px-4 py-2 font-medium">Fecha</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {lista.map((a) => (
              <tr key={a.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-semibold text-gray-900">{a.trabajador_nombre}</td>
                <td className="px-4 py-2 font-mono text-xs text-gray-500">{a.trabajador_documento}</td>
                <td className="px-4 py-2 text-gray-600">{a.empresa_nombre}</td>
                <td className="px-4 py-2 text-gray-600">{TIPO_EXAMEN_LABEL[a.tipo_examen] ?? a.tipo_examen}</td>
                <td className="px-4 py-2">
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                    {ESTADO_LABEL[a.estado as Estado] ?? a.estado}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-500">{new Date(a.created_at).toLocaleDateString("es-CO")}</td>
                <td className="px-4 py-2">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => imprimirHistoriaCompleta(a, medicoNombre).catch((e) => setError((e as Error).message))}
                      className="rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-100">
                      🖨 PDF
                    </button>
                    <Link href={`/consultorio/atencion/${a.id}`}
                      className="rounded-lg bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700 transition hover:bg-violet-100">
                      Abrir
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
            {lista.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-sm text-gray-400">
                {atenciones.length === 0 ? "Aún no tiene atenciones asignadas." : "Sin resultados para la búsqueda."}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
