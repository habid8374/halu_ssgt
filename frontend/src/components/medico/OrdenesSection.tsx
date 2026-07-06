"use client";

import { useCallback, useEffect, useState } from "react";
import Combobox, { type ItemCatalogo } from "@/components/Combobox";
import AsyncCombobox from "@/components/AsyncCombobox";
import { cargarCie10 } from "@/lib/catalogos";
import { imprimirDocumento, esc, type EncabezadoImpresion } from "@/lib/imprimir";
import { apiFetch } from "@/lib/api";

interface Orden {
  id: number;
  tipo: string;
  descripcion: string;
  codigo_cups: string;
  cantidad: number;
  diagnostico_cie10: string;
  indicaciones: string;
  estado: string;
}

const TIPOS = [
  ["laboratorio", "Laboratorio clínico"],
  ["imagen", "Imagen diagnóstica"],
  ["paraclinico", "Otro paraclínico"],
  ["procedimiento", "Procedimiento"],
  ["interconsulta", "Interconsulta / remisión"],
  ["incapacidad", "Incapacidad médica"],
  ["otro", "Otra orden"],
] as const;
const TIPO_LABEL: Record<string, string> = Object.fromEntries(TIPOS);

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

const VACIO = { tipo: "laboratorio", descripcion: "", codigo_cups: "", cantidad: "1", indicaciones: "" };

/**
 * Órdenes médicas del médico tratante: paraclínicos, procedimientos,
 * remisiones e incapacidades. Se imprimen y entregan al trabajador.
 */
export default function OrdenesSection({
  atencionId,
  encabezado,
}: {
  atencionId: number;
  encabezado: EncabezadoImpresion;
}) {
  const [lista, setLista] = useState<Orden[]>([]);
  const [cie10, setCie10] = useState<ItemCatalogo[]>([]);
  const [dx, setDx] = useState<ItemCatalogo | null>(null);
  const [cups, setCups] = useState<ItemCatalogo | null>(null);
  const [f, setF] = useState<Record<string, string>>({ ...VACIO });
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));

  const buscarCups = (q: string) =>
    apiFetch<ItemCatalogo[]>(`/cups/?q=${encodeURIComponent(q)}`);

  const cargar = useCallback(async () => {
    setLista(await apiFetch<Orden[]>(`/ordenes/?atencion=${atencionId}`));
  }, [atencionId]);

  useEffect(() => {
    void cargar();
    void cargarCie10().then(setCie10);
  }, [cargar]);

  async function agregar() {
    if (!f.descripcion.trim()) return;
    await apiFetch("/ordenes/", {
      method: "POST",
      body: JSON.stringify({
        atencion: atencionId, tipo: f.tipo, descripcion: f.descripcion,
        codigo_cups: cups?.codigo ?? f.codigo_cups, cantidad: Number(f.cantidad) || 1,
        diagnostico_cie10: dx?.codigo ?? "", indicaciones: f.indicaciones,
      }),
    });
    setF({ ...VACIO }); setDx(null); setCups(null);
    void cargar();
  }

  async function eliminar(id: number) {
    await apiFetch(`/ordenes/${id}/`, { method: "DELETE" });
    void cargar();
  }

  function imprimir(o?: Orden) {
    const ordenes = o ? [o] : lista;
    if (ordenes.length === 0) return;
    const filas = ordenes.map((x) => `
      <div class="item">
        <b>${TIPO_LABEL[x.tipo] ?? x.tipo}</b> — ${esc(x.descripcion)} (x${x.cantidad})
        ${x.codigo_cups ? `<br><span style="color:#666">CUPS: ${esc(x.codigo_cups)}</span>` : ""}
        ${x.diagnostico_cie10 ? `<br><span style="color:#666">Dx: ${esc(x.diagnostico_cie10)}</span>` : ""}
        ${x.indicaciones ? `<br>${esc(x.indicaciones)}` : ""}
      </div>`).join("");
    imprimirDocumento("Orden médica", encabezado, `<h2>Órdenes</h2>${filas}`);
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-teal-600">
          Órdenes y paraclínicos
        </h2>
        {lista.length > 0 && (
          <button onClick={() => imprimir()} className="rounded-lg bg-gray-200 px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-300">
            🖨 Imprimir todas
          </button>
        )}
      </div>

      {lista.length > 0 && (
        <ul className="mb-4 space-y-2">
          {lista.map((o) => (
            <li key={o.id} className="flex items-start gap-3 rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <span className="mt-0.5 rounded bg-violet-100 px-1.5 py-0.5 text-xs font-semibold text-violet-700">
                {TIPO_LABEL[o.tipo] ?? o.tipo}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-gray-800">{o.descripcion} <span className="text-gray-400">x{o.cantidad}</span></p>
                {(o.codigo_cups || o.diagnostico_cie10 || o.indicaciones) && (
                  <p className="text-xs text-gray-500">
                    {o.codigo_cups ? `CUPS ${o.codigo_cups} · ` : ""}
                    {o.diagnostico_cie10 ? `Dx ${o.diagnostico_cie10} · ` : ""}
                    {o.indicaciones}
                  </p>
                )}
              </div>
              <button onClick={() => imprimir(o)} className="text-xs text-teal-600 hover:underline">Imprimir</button>
              <button onClick={() => eliminar(o.id)} className="text-xs text-red-500 hover:underline">Quitar</button>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-lg border border-dashed border-gray-300 p-4">
        <div className="grid gap-3 md:grid-cols-2">
          <label className={labelCls}>Tipo de orden
            <select value={f.tipo} onChange={(e) => set("tipo", e.target.value)} className={inputCls}>
              {TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={labelCls}>Cantidad
            <input type="number" min="1" value={f.cantidad} onChange={(e) => set("cantidad", e.target.value)} className={inputCls} />
          </label>
          <label className={`${labelCls} md:col-span-2`}>Procedimiento CUPS (buscar en catálogo)
            <div className="mt-1">
              <AsyncCombobox buscar={buscarCups} seligido={cups} placeholder="Buscar por código o nombre…"
                onSelect={(c) => {
                  setCups(c);
                  if (c && !f.descripcion.trim()) set("descripcion", c.nombre);
                }} />
            </div>
          </label>
          <label className={`${labelCls} md:col-span-2`}>Descripción (estudio / servicio) *
            <input value={f.descripcion} onChange={(e) => set("descripcion", e.target.value)} className={inputCls}
              placeholder="Hemograma, RX de tórax, audiometría…" />
          </label>
          <label className={labelCls}>Diagnóstico relacionado (CIE-10)
            <div className="mt-1">
              <Combobox items={cie10} value={dx?.codigo ?? ""} placeholder="Buscar diagnóstico…" onSelect={setDx} />
            </div>
          </label>
          <label className={`${labelCls} md:col-span-2`}>Indicaciones
            <input value={f.indicaciones} onChange={(e) => set("indicaciones", e.target.value)} className={inputCls} />
          </label>
        </div>
        <button onClick={agregar}
          className="mt-3 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700">
          + Agregar orden
        </button>
      </div>
    </section>
  );
}
