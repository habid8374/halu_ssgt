"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch, apiUpload } from "@/lib/api";

interface Prueba {
  id: number;
  tipo_prueba: string;
  tipo_prueba_label: string;
  detalle: string;
  estado: string;
  resultado: Record<string, unknown>;
  resumen: string;
  archivo_url: string | null;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-[11px] font-medium uppercase tracking-wide text-gray-500";
const FRECS = [500, 1000, 2000, 3000, 4000, 6000, 8000];

const ESTADO_UI: Record<string, string> = {
  pendiente: "bg-gray-100 text-gray-500",
  en_proceso: "bg-amber-50 text-amber-700",
  realizada: "bg-emerald-50 text-emerald-700",
  no_aplica: "bg-gray-100 text-gray-400",
};

// --- Interpretaciones automáticas ---
function ptaOido(vals: Record<string, string>): number | null {
  const nums = [500, 1000, 2000].map((f) => Number(vals?.[String(f)])).filter((n) => !Number.isNaN(n));
  if (nums.length < 3) return null;
  return Math.round(nums.reduce((a, b) => a + b, 0) / nums.length);
}
function gradoAudicion(pta: number | null): string {
  if (pta === null) return "";
  if (pta <= 25) return "Normal";
  if (pta <= 40) return "Hipoacusia leve";
  if (pta <= 55) return "Hipoacusia moderada";
  if (pta <= 70) return "Hipoacusia moderada a severa";
  if (pta <= 90) return "Hipoacusia severa";
  return "Hipoacusia profunda";
}
function notch4k(vals: Record<string, string>): boolean {
  const v3 = Number(vals?.["3000"]), v4 = Number(vals?.["4000"]), v6 = Number(vals?.["6000"]);
  return !Number.isNaN(v4) && !Number.isNaN(v6) && v4 >= v6 + 15 && (Number.isNaN(v3) || v4 >= v3 + 15);
}
function interpretarEspiro(r: Record<string, string>): string {
  const fev1 = Number(r?.fev1_pct), rel = Number(r?.fev1_fvc);
  if (Number.isNaN(rel) && Number.isNaN(fev1)) return "";
  if (!Number.isNaN(rel) && rel < 70) return Number(r?.fvc_pct) < 80 ? "Patrón mixto" : "Patrón obstructivo";
  if (!Number.isNaN(Number(r?.fvc_pct)) && Number(r?.fvc_pct) < 80) return "Patrón restrictivo (sugerido)";
  return "Espirometría dentro de límites normales";
}

/**
 * Circuito de pruebas de la atención (triaje multi-estación). Cada estación se
 * digita con su formulario especializado y/o se adjunta el soporte del equipo,
 * y se marca como realizada. El concepto se habilita al cerrar el circuito.
 */
export default function PruebasSection({ atencionId }: { atencionId: number }) {
  const [pruebas, setPruebas] = useState<Prueba[]>([]);
  const [abierta, setAbierta] = useState<number | null>(null);

  const cargar = useCallback(async () => {
    setPruebas(await apiFetch<Prueba[]>(`/pruebas/?atencion=${atencionId}`));
  }, [atencionId]);
  useEffect(() => { void cargar(); }, [cargar]);

  const total = pruebas.length;
  const hechas = pruebas.filter((p) => p.estado === "realizada" || p.estado === "no_aplica").length;

  async function guardar(p: Prueba, resultado: Record<string, unknown>, resumen: string, estado?: string) {
    await apiFetch(`/pruebas/${p.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ resultado, resumen, ...(estado ? { estado } : {}) }),
    });
    void cargar();
  }
  async function marcar(p: Prueba, estado: string) {
    await apiFetch(`/pruebas/${p.id}/`, { method: "PATCH", body: JSON.stringify({ estado }) });
    void cargar();
  }
  async function adjuntar(p: Prueba, file: File) {
    const form = new FormData();
    form.append("archivo", file);
    await apiUpload(`/pruebas/${p.id}/`, form);
    void cargar();
  }

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-teal-600">
          Circuito de pruebas (paraclínicos)
        </h2>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${hechas === total && total ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
          {hechas}/{total} realizadas
        </span>
      </div>

      <div className="space-y-2">
        {pruebas.map((p) => (
          <article key={p.id} className="rounded-lg border border-gray-200">
            <button onClick={() => setAbierta(abierta === p.id ? null : p.id)}
              className="flex w-full items-center gap-3 px-3 py-2.5 text-left">
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${ESTADO_UI[p.estado]}`}>
                {p.estado.replace("_", " ")}
              </span>
              <span className="flex-1 text-sm font-semibold text-gray-800">{p.tipo_prueba_label}</span>
              {p.resumen && <span className="hidden truncate text-xs text-gray-500 sm:block">{p.resumen}</span>}
              {p.archivo_url && <span title="Con adjunto">📎</span>}
              <span className="text-gray-400">{abierta === p.id ? "▲" : "▼"}</span>
            </button>

            {abierta === p.id && (
              <div className="border-t border-gray-100 bg-gray-50 p-4">
                <FormularioPrueba prueba={p} onGuardar={guardar} />

                <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-gray-200 pt-3">
                  <label className="text-xs font-semibold text-gray-600">
                    📎 Adjuntar soporte
                    <input type="file" className="ml-2 text-xs"
                      onChange={(e) => { const file = e.target.files?.[0]; if (file) void adjuntar(p, file); }} />
                  </label>
                  {p.archivo_url && <a href={p.archivo_url} target="_blank" className="text-xs font-semibold text-teal-600 hover:underline">Ver adjunto</a>}
                  <div className="ml-auto flex gap-2">
                    {p.estado !== "realizada" && (
                      <button onClick={() => marcar(p, "realizada")} className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-400">
                        Marcar realizada
                      </button>
                    )}
                    {p.estado !== "no_aplica" && (
                      <button onClick={() => marcar(p, "no_aplica")} className="rounded-lg bg-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-300">
                        No aplica
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </article>
        ))}
        {total === 0 && <p className="text-sm text-gray-400">Sin pruebas en el circuito.</p>}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
function FormularioPrueba({
  prueba, onGuardar,
}: {
  prueba: Prueba;
  onGuardar: (p: Prueba, r: Record<string, unknown>, resumen: string, estado?: string) => void;
}) {
  const [r, setR] = useState<Record<string, unknown>>(prueba.resultado ?? {});
  const [resumen, setResumen] = useState(prueba.resumen ?? "");
  const set = (k: string, v: unknown) => setR((p) => ({ ...p, [k]: v }));

  if (prueba.tipo_prueba === "audiometria") {
    const od = (r.od as Record<string, string>) ?? {};
    const oi = (r.oi as Record<string, string>) ?? {};
    const setOido = (oido: "od" | "oi", f: number, v: string) =>
      setR((p) => ({ ...p, [oido]: { ...(p[oido] as object), [f]: v } }));
    const ptaOD = ptaOido(od), ptaOI = ptaOido(oi);
    const sugerido = `OD: ${gradoAudicion(ptaOD)} (PTA ${ptaOD ?? "—"}). OI: ${gradoAudicion(ptaOI)} (PTA ${ptaOI ?? "—"}).${notch4k(od) || notch4k(oi) ? " Muesca en 4kHz (trauma acústico a descartar)." : ""}`;
    return (
      <div>
        <p className="mb-2 text-xs text-gray-500">Umbrales por vía aérea (dB HL)</p>
        <div className="overflow-x-auto">
          <table className="text-xs">
            <thead><tr><th className="px-1"></th>{FRECS.map((f) => <th key={f} className="px-1 text-gray-500">{f}</th>)}</tr></thead>
            <tbody>
              {(["od", "oi"] as const).map((oido) => (
                <tr key={oido}>
                  <td className="pr-2 font-semibold text-gray-700">{oido.toUpperCase()}</td>
                  {FRECS.map((f) => (
                    <td key={f} className="px-0.5">
                      <input value={(oido === "od" ? od : oi)[String(f)] ?? ""} onChange={(e) => setOido(oido, f, e.target.value)}
                        className="w-11 rounded border border-gray-300 px-1 py-1 text-center" inputMode="numeric" />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 rounded bg-white px-2 py-1 text-xs text-gray-600">Sugerido: {sugerido}</p>
        <ResumenGuardar r={{ ...r, sugerido }} resumen={resumen || sugerido} setResumen={setResumen} onGuardar={(res) => onGuardar(prueba, r, res, "realizada")} />
      </div>
    );
  }

  if (prueba.tipo_prueba === "visiometria") {
    const campos: Array<[string, string]> = [
      ["av_od_sc", "AV OD s/c"], ["av_oi_sc", "AV OI s/c"],
      ["av_od_cc", "AV OD c/c"], ["av_oi_cc", "AV OI c/c"],
    ];
    return (
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {campos.map(([k, l]) => (
          <label key={k} className={labelCls}>{l}
            <input value={(r[k] as string) ?? ""} onChange={(e) => set(k, e.target.value)} className={inputCls} placeholder="20/20" />
          </label>
        ))}
        <label className={`${labelCls} col-span-2 sm:col-span-4`}>Visión de color / profundidad
          <input value={(r.color as string) ?? ""} onChange={(e) => set("color", e.target.value)} className={inputCls} placeholder="Normal (Ishihara)…" />
        </label>
        <div className="col-span-2 sm:col-span-4">
          <ResumenGuardar r={r} resumen={resumen} setResumen={setResumen} onGuardar={(res) => onGuardar(prueba, r, res, "realizada")} />
        </div>
      </div>
    );
  }

  if (prueba.tipo_prueba === "espirometria") {
    const patron = interpretarEspiro(r as Record<string, string>);
    const campos: Array<[string, string]> = [
      ["fvc_pct", "FVC (% pred)"], ["fev1_pct", "FEV1 (% pred)"], ["fev1_fvc", "FEV1/FVC (%)"],
    ];
    return (
      <div className="grid grid-cols-3 gap-2">
        {campos.map(([k, l]) => (
          <label key={k} className={labelCls}>{l}
            <input value={(r[k] as string) ?? ""} onChange={(e) => set(k, e.target.value)} className={inputCls} inputMode="decimal" />
          </label>
        ))}
        <p className="col-span-3 rounded bg-white px-2 py-1 text-xs text-gray-600">Sugerido: {patron || "—"}</p>
        <div className="col-span-3">
          <ResumenGuardar r={{ ...r, patron }} resumen={resumen || patron} setResumen={setResumen} onGuardar={(res) => onGuardar(prueba, { ...r, patron }, res, "realizada")} />
        </div>
      </div>
    );
  }

  // laboratorio / otro: texto libre
  return (
    <div>
      <label className={labelCls}>Resultado / hallazgos
        <textarea rows={3} value={(r.texto as string) ?? ""} onChange={(e) => set("texto", e.target.value)} className={inputCls} />
      </label>
      <ResumenGuardar r={r} resumen={resumen} setResumen={setResumen} onGuardar={(res) => onGuardar(prueba, r, res, "realizada")} />
    </div>
  );
}

function ResumenGuardar({
  resumen, setResumen, onGuardar,
}: {
  r: Record<string, unknown>; resumen: string; setResumen: (v: string) => void; onGuardar: (resumen: string) => void;
}) {
  return (
    <div className="mt-3">
      <label className={labelCls}>Interpretación / resumen (va al concepto)
        <input value={resumen} onChange={(e) => setResumen(e.target.value)} className={inputCls} />
      </label>
      <button onClick={() => onGuardar(resumen)} className="mt-2 rounded-lg bg-teal-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-teal-700">
        Guardar resultado
      </button>
    </div>
  );
}
