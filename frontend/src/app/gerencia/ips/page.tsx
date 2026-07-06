"use client";

import { useEffect, useRef, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";
import { invalidarMembrete } from "@/lib/membrete";
import type { Membrete } from "@/lib/imprimir";

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

const VACIO: Membrete = {
  razon_social: "", nit: "", codigo_habilitacion: "",
  direccion: "", ciudad: "", telefono: "", email: "", logo_data_uri: "",
};

/**
 * Configuración de la IPS (rol coordinador): datos de membrete que aparecen en
 * la historia clínica, el certificado de aptitud, órdenes y recetas —incluido
 * el código de habilitación (REPS) y el logo.
 */
export default function ConfiguracionIPSPage() {
  const [f, setF] = useState<Membrete>({ ...VACIO });
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const set = (k: keyof Membrete, v: string) => setF((p) => ({ ...p, [k]: v }));

  useEffect(() => {
    apiFetch<Membrete>("/configuracion/").then((d) => setF({ ...VACIO, ...d })).catch(() => {});
  }, []);

  function elegirLogo(file: File) {
    if (file.size > 500_000) {
      setError("El logo pesa más de 500 KB. Use una imagen más liviana (PNG/JPG).");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => set("logo_data_uri", String(reader.result));
    reader.readAsDataURL(file);
    setError(null);
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    setMsg(null); setError(null); setGuardando(true);
    try {
      await apiFetch("/configuracion/", { method: "PATCH", body: JSON.stringify(f) });
      invalidarMembrete();
      setMsg("Configuración guardada. Ya aparece en el membrete de los documentos.");
    } catch (e) {
      setError((e as Error).message.replace(/^API \d+:\s*/, "").slice(0, 200));
    } finally {
      setGuardando(false);
    }
  }

  return (
    <AppShell titulo="Configuración de la IPS (membrete)">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <form onSubmit={guardar} className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Datos de la institución</h2>
          <label className={labelCls}>Razón social *
            <input value={f.razon_social} onChange={(e) => set("razon_social", e.target.value)} className={inputCls} required />
          </label>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>NIT
              <input value={f.nit} onChange={(e) => set("nit", e.target.value)} className={inputCls} placeholder="900123456-7" />
            </label>
            <label className={labelCls}>Código de habilitación (REPS)
              <input value={f.codigo_habilitacion} onChange={(e) => set("codigo_habilitacion", e.target.value)} className={inputCls} />
            </label>
          </div>
          <label className={`${labelCls} mt-3`}>Dirección
            <input value={f.direccion} onChange={(e) => set("direccion", e.target.value)} className={inputCls} />
          </label>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>Ciudad
              <input value={f.ciudad} onChange={(e) => set("ciudad", e.target.value)} className={inputCls} />
            </label>
            <label className={labelCls}>Teléfono
              <input value={f.telefono} onChange={(e) => set("telefono", e.target.value)} className={inputCls} />
            </label>
          </div>
          <label className={`${labelCls} mt-3`}>Correo
            <input type="email" value={f.email} onChange={(e) => set("email", e.target.value)} className={inputCls} />
          </label>
          <button type="submit" disabled={guardando}
            className="mt-5 rounded-lg bg-teal-600 px-6 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
            {guardando ? "Guardando…" : "Guardar membrete"}
          </button>
        </section>

        <section className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Logo</h2>
          <div className="mb-4 flex h-28 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50">
            {f.logo_data_uri
              /* eslint-disable-next-line @next/next/no-img-element */
              ? <img src={f.logo_data_uri} alt="Logo" className="max-h-24 w-auto object-contain" />
              : <span className="text-xs text-gray-400">Sin logo</span>}
          </div>
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp"
            onChange={(e) => { const file = e.target.files?.[0]; if (file) elegirLogo(file); }}
            className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-teal-50 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-teal-700 hover:file:bg-teal-100" />
          {f.logo_data_uri && (
            <button type="button" onClick={() => set("logo_data_uri", "")}
              className="mt-3 text-xs font-semibold text-red-500 hover:underline">
              Quitar logo
            </button>
          )}
          <p className="mt-3 text-[11px] text-gray-400">PNG o JPG, preferiblemente con fondo transparente. Máx. 500 KB.</p>
        </section>
      </form>
    </AppShell>
  );
}
