"use client";

import { useCallback, useEffect, useState } from "react";
import { imprimirDocumento, esc, type EncabezadoImpresion } from "@/lib/imprimir";
import { apiFetch } from "@/lib/api";

interface Medicamento {
  medicamento: string;
  concentracion: string;
  forma_farmaceutica: string;
  dosis: string;
  via: string;
  frecuencia: string;
  duracion: string;
  cantidad: string;
  indicaciones: string;
}
interface Receta {
  id: number;
  diagnostico_cie10: string;
  observaciones: string;
  created_at: string;
  medicamentos: Medicamento[];
}

const MED_VACIO: Medicamento = {
  medicamento: "", concentracion: "", forma_farmaceutica: "", dosis: "",
  via: "", frecuencia: "", duracion: "", cantidad: "", indicaciones: "",
};

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/** Fórmula médica: encabezado + medicamentos. Se imprime y entrega al paciente. */
export default function RecetasSection({
  atencionId,
  encabezado,
}: {
  atencionId: number;
  encabezado: EncabezadoImpresion;
}) {
  const [lista, setLista] = useState<Receta[]>([]);
  const [items, setItems] = useState<Medicamento[]>([]);
  const [med, setMed] = useState<Medicamento>({ ...MED_VACIO });
  const [obs, setObs] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const setM = (k: keyof Medicamento, v: string) => setMed((p) => ({ ...p, [k]: v }));

  const cargar = useCallback(async () => {
    setLista(await apiFetch<Receta[]>(`/recetas/?atencion=${atencionId}`));
  }, [atencionId]);

  useEffect(() => { void cargar(); }, [cargar]);

  function agregarItem() {
    if (!med.medicamento.trim()) return;
    setItems((p) => [...p, med]);
    setMed({ ...MED_VACIO });
  }

  async function guardarReceta() {
    if (items.length === 0) { setMsg("Agrega al menos un medicamento."); return; }
    setMsg(null);
    await apiFetch("/recetas/", {
      method: "POST",
      body: JSON.stringify({ atencion: atencionId, observaciones: obs, medicamentos: items }),
    });
    setItems([]); setObs("");
    void cargar();
  }

  async function eliminar(id: number) {
    await apiFetch(`/recetas/${id}/`, { method: "DELETE" });
    void cargar();
  }

  function imprimir(r: Receta) {
    const filas = r.medicamentos.map((m, i) => `
      <tr>
        <td>${i + 1}</td>
        <td><b>${esc(m.medicamento)}</b> ${esc(m.concentracion)} ${esc(m.forma_farmaceutica)}</td>
        <td>${esc(m.dosis)} ${esc(m.via)} ${esc(m.frecuencia)}<br>${esc(m.duracion)} — ${esc(m.cantidad)}${m.indicaciones ? `<br><span style="color:#666">${esc(m.indicaciones)}</span>` : ""}</td>
      </tr>`).join("");
    imprimirDocumento("Fórmula médica", encabezado,
      `<h2>Medicamentos</h2>
       <table><thead><tr><th>#</th><th>Medicamento</th><th>Posología</th></tr></thead><tbody>${filas}</tbody></table>
       ${r.observaciones ? `<h2>Observaciones</h2><div class="item">${esc(r.observaciones)}</div>` : ""}`);
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
        Recetas / fórmula médica
      </h2>

      {lista.length > 0 && (
        <ul className="mb-4 space-y-2">
          {lista.map((r) => (
            <li key={r.id} className="flex items-start gap-3 rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-gray-800">Receta #{r.id}</p>
                <p className="text-xs text-gray-500">
                  {r.medicamentos.map((m) => m.medicamento).join(", ")}
                </p>
              </div>
              <button onClick={() => imprimir(r)} className="text-xs text-teal-600 hover:underline">Imprimir</button>
              <button onClick={() => eliminar(r.id)} className="text-xs text-red-500 hover:underline">Quitar</button>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-lg border border-dashed border-gray-300 p-4">
        {/* Medicamentos en composición */}
        {items.length > 0 && (
          <ul className="mb-3 space-y-1">
            {items.map((m, i) => (
              <li key={i} className="flex items-center gap-2 rounded bg-teal-50 px-3 py-1.5 text-sm text-teal-800">
                <span className="flex-1">
                  {m.medicamento} {m.concentracion} — {m.dosis} {m.frecuencia} {m.duracion}
                </span>
                <button onClick={() => setItems((p) => p.filter((_, j) => j !== i))} className="text-xs text-red-500 hover:underline">
                  Quitar
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Agregar medicamento</p>
        <div className="grid gap-3 md:grid-cols-3">
          <label className={`${labelCls} md:col-span-2`}>Medicamento *
            <input value={med.medicamento} onChange={(e) => setM("medicamento", e.target.value)} className={inputCls} placeholder="Acetaminofén" />
          </label>
          <label className={labelCls}>Concentración
            <input value={med.concentracion} onChange={(e) => setM("concentracion", e.target.value)} className={inputCls} placeholder="500 mg" />
          </label>
          <label className={labelCls}>Forma
            <input value={med.forma_farmaceutica} onChange={(e) => setM("forma_farmaceutica", e.target.value)} className={inputCls} placeholder="Tableta" />
          </label>
          <label className={labelCls}>Dosis
            <input value={med.dosis} onChange={(e) => setM("dosis", e.target.value)} className={inputCls} placeholder="1 tableta" />
          </label>
          <label className={labelCls}>Vía
            <input value={med.via} onChange={(e) => setM("via", e.target.value)} className={inputCls} placeholder="Oral" />
          </label>
          <label className={labelCls}>Frecuencia
            <input value={med.frecuencia} onChange={(e) => setM("frecuencia", e.target.value)} className={inputCls} placeholder="Cada 8 horas" />
          </label>
          <label className={labelCls}>Duración
            <input value={med.duracion} onChange={(e) => setM("duracion", e.target.value)} className={inputCls} placeholder="7 días" />
          </label>
          <label className={labelCls}>Cantidad
            <input value={med.cantidad} onChange={(e) => setM("cantidad", e.target.value)} className={inputCls} placeholder="21 tabletas" />
          </label>
          <label className={`${labelCls} md:col-span-3`}>Indicaciones
            <input value={med.indicaciones} onChange={(e) => setM("indicaciones", e.target.value)} className={inputCls} />
          </label>
        </div>
        <button onClick={agregarItem}
          className="mt-3 rounded-lg bg-gray-200 px-4 py-2 text-sm font-semibold text-gray-800 transition hover:bg-gray-300">
          + Añadir a la receta
        </button>

        <label className={`${labelCls} mt-4`}>Observaciones de la receta
          <input value={obs} onChange={(e) => setObs(e.target.value)} className={inputCls} />
        </label>
        {msg && <p className="mt-2 text-xs text-amber-600">{msg}</p>}
        <button onClick={guardarReceta} disabled={items.length === 0}
          className="mt-3 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
          Guardar receta ({items.length})
        </button>
      </div>
    </section>
  );
}
