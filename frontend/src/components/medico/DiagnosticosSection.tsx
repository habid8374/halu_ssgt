"use client";

import { useCallback, useEffect, useState } from "react";
import Combobox, { type ItemCatalogo } from "@/components/Combobox";
import { cargarCie10, cargarCie11 } from "@/lib/catalogos";
import { apiFetch } from "@/lib/api";

interface Diagnostico {
  id: number;
  cie10_codigo: string;
  cie10_desc: string;
  cie11_codigo: string;
  cie11_desc: string;
  relacion: string;
  tipo: string;
  observacion: string;
}

const RELACIONES = [["principal", "Principal"], ["relacionado", "Relacionado"]] as const;
const TIPOS = [
  ["01", "Impresión diagnóstica"],
  ["02", "Confirmado nuevo"],
  ["03", "Confirmado repetido"],
] as const;
const TIPO_LABEL: Record<string, string> = Object.fromEntries(TIPOS);

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Diagnósticos codificados de la historia (CIE-10 obligatorio; CIE-11 opcional
 * en transición). El médico los elige de catálogo, no los escribe.
 */
export default function DiagnosticosSection({
  atencionId,
  historiaId,
}: {
  atencionId: number;
  historiaId?: number;
}) {
  const [lista, setLista] = useState<Diagnostico[]>([]);
  const [cie10, setCie10] = useState<ItemCatalogo[]>([]);
  const [cie11, setCie11] = useState<ItemCatalogo[]>([]);
  const [sel10, setSel10] = useState<ItemCatalogo | null>(null);
  const [sel11, setSel11] = useState<ItemCatalogo | null>(null);
  const [relacion, setRelacion] = useState("principal");
  const [tipo, setTipo] = useState("01");
  const [obs, setObs] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setLista(await apiFetch<Diagnostico[]>(`/diagnosticos/?atencion=${atencionId}`));
  }, [atencionId]);

  useEffect(() => {
    void cargar();
    void cargarCie10().then(setCie10);
    void cargarCie11().then(setCie11);
  }, [cargar]);

  async function agregar() {
    if (!historiaId) { setMsg("Guarda primero la historia clínica."); return; }
    if (!sel10) { setMsg("Selecciona un diagnóstico CIE-10."); return; }
    setMsg(null);
    await apiFetch("/diagnosticos/", {
      method: "POST",
      body: JSON.stringify({
        historia: historiaId,
        cie10_codigo: sel10.codigo, cie10_desc: sel10.nombre,
        cie11_codigo: sel11?.codigo ?? "", cie11_desc: sel11?.nombre ?? "",
        relacion, tipo, observacion: obs,
      }),
    });
    setSel10(null); setSel11(null); setObs(""); setRelacion("principal"); setTipo("01");
    void cargar();
  }

  async function eliminar(id: number) {
    await apiFetch(`/diagnosticos/${id}/`, { method: "DELETE" });
    void cargar();
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-teal-600">
          Diagnósticos (CIE-10 / CIE-11)
        </h2>
        <span className="rounded bg-red-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-red-600">
          Reservado — solo médico
        </span>
      </div>

      {lista.length > 0 && (
        <ul className="mb-4 space-y-2">
          {lista.map((d) => (
            <li key={d.id} className="flex items-start gap-3 rounded-lg bg-gray-50 px-3 py-2 text-sm">
              <span className="mt-0.5 rounded bg-teal-100 px-1.5 py-0.5 font-mono text-xs font-semibold text-teal-800">
                {d.cie10_codigo}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-gray-800">{d.cie10_desc}</p>
                <p className="text-xs text-gray-500">
                  {d.relacion === "principal" ? "Principal" : "Relacionado"} · {TIPO_LABEL[d.tipo] ?? d.tipo}
                  {d.cie11_codigo ? ` · CIE-11 ${d.cie11_codigo}` : ""}
                </p>
              </div>
              <button onClick={() => eliminar(d.id)} className="text-xs text-red-500 hover:underline">
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-lg border border-dashed border-gray-300 p-4">
        <div className="grid gap-3 md:grid-cols-2">
          <label className={labelCls}>Diagnóstico CIE-10 *
            <div className="mt-1">
              <Combobox items={cie10} value={sel10?.codigo ?? ""} placeholder="Buscar por código o nombre…"
                onSelect={setSel10} />
            </div>
          </label>
          <label className={labelCls}>Equivalente CIE-11 (opcional)
            <div className="mt-1">
              <Combobox items={cie11} value={sel11?.codigo ?? ""} placeholder="Transición Res. 1442/2024…"
                onSelect={setSel11} />
            </div>
          </label>
          <label className={labelCls}>Relación
            <select value={relacion} onChange={(e) => setRelacion(e.target.value)} className={inputCls}>
              {RELACIONES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={labelCls}>Tipo
            <select value={tipo} onChange={(e) => setTipo(e.target.value)} className={inputCls}>
              {TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={`${labelCls} md:col-span-2`}>Observación
            <input value={obs} onChange={(e) => setObs(e.target.value)} className={inputCls} />
          </label>
        </div>
        {msg && <p className="mt-2 text-xs text-amber-600">{msg}</p>}
        <button onClick={agregar}
          className="mt-3 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700">
          + Agregar diagnóstico
        </button>
      </div>
    </section>
  );
}
