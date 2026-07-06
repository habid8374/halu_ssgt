"use client";

import { useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch, apiUpload } from "@/lib/api";

interface Cums { id: number; codigo: string; nombre: string; forma_farmaceutica: string; via: string; atc: string }

const inputCls =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";

/**
 * Vademécum CUMS (rol coordinador). Alimenta el buscador de medicamentos de las
 * recetas. Se siembra deduplicado y se actualiza importando el CUMS oficial
 * (INVIMA/MinSalud) desde la app, sin comandos.
 */
export default function MedicamentosPage() {
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState<Cums[]>([]);
  const [subiendo, setSubiendo] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function buscar(texto: string) {
    setResultados(await apiFetch<Cums[]>(`/cums/?q=${encodeURIComponent(texto)}`));
  }
  useEffect(() => {
    const t = setTimeout(() => void buscar(q), 250);
    return () => clearTimeout(t);
  }, [q]);

  async function importar() {
    const file = fileRef.current?.files?.[0];
    if (!file) { setError("Selecciona el archivo CSV del CUMS."); return; }
    setError(null); setMsg(null); setSubiendo(true);
    try {
      const form = new FormData();
      form.append("archivo", file);
      const r = await apiUpload<{ creados: number; actualizados: number; total: number }>("/cums/importar/", form);
      setMsg(`Importación lista: ${r.creados} nuevos, ${r.actualizados} actualizados. Total en vademécum: ${r.total}.`);
      if (fileRef.current) fileRef.current.value = "";
      void buscar(q);
    } catch (e) {
      setError((e as Error).message.replace(/^API \d+:\s*/, "").slice(0, 200));
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <AppShell titulo="Vademécum (CUMS)">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        <section className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-600">Importar CUMS oficial</h2>
          <p className="mb-4 text-xs text-gray-500">
            CSV con: <b>código (CUM)</b>, <b>genérico</b>, forma farmacéutica, vía
            y ATC. Se actualiza por código, sin duplicar. Completa el vademécum
            inicial ya cargado.
          </p>
          <input ref={fileRef} type="file" accept=".csv,text/csv"
            className="mb-3 block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-teal-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-teal-700 hover:file:bg-teal-100" />
          <button onClick={importar} disabled={subiendo}
            className="w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
            {subiendo ? "Importando…" : "Importar vademécum"}
          </button>
        </section>

        <section>
          <input value={q} onChange={(e) => setQ(e.target.value)} className={`${inputCls} mb-3`}
            placeholder="Buscar medicamento por genérico, CUM o ATC…" />
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                <tr><th className="px-4 py-2 font-medium">CUM</th><th className="px-4 py-2 font-medium">Genérico</th><th className="px-4 py-2 font-medium">Forma</th><th className="px-4 py-2 font-medium">Vía</th><th className="px-4 py-2 font-medium">ATC</th></tr>
              </thead>
              <tbody>
                {resultados.map((c) => (
                  <tr key={c.id} className="border-t border-gray-100">
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">{c.codigo}</td>
                    <td className="px-4 py-2 text-gray-800">{c.nombre}</td>
                    <td className="px-4 py-2 text-gray-500">{c.forma_farmaceutica}</td>
                    <td className="px-4 py-2 text-gray-500">{c.via}</td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-400">{c.atc}</td>
                  </tr>
                ))}
                {resultados.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                    Sin resultados. {q ? "Prueba otro término." : "Escribe para buscar en el vademécum."}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-gray-400">Se muestran hasta 50 resultados.</p>
        </section>
      </div>
    </AppShell>
  );
}
