"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Empresa { id: number; nombre: string }
interface Factura {
  id: number; numero: string; empresa_nombre: string; estado: string;
  total: string; periodo_desde: string; periodo_hasta: string;
}
interface Accidente { id: number; trabajador_nombre: string; tipo_evento: string; fecha_evento: string }
interface FacturaARL {
  id: number; numero: string; trabajador_nombre: string; valor: string;
  estado: string; cuv: string;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

const ESTADO_FACTURA: Record<string, string> = {
  borrador: "bg-gray-100 text-gray-600",
  emitida: "bg-blue-50 text-blue-700",
  pagada: "bg-emerald-50 text-emerald-600",
  anulada: "bg-red-50 text-red-600",
  validada: "bg-emerald-50 text-emerald-600",
  radicada: "bg-blue-50 text-blue-700",
};

/**
 * Facturación (coordinador). DOS MOTORES SEPARADOS (CLAUDE.md regla 8):
 * facturas estándar a empresas (sin RIPS) y facturas ARL con RIPS/CUV,
 * exclusivas de accidentes de trabajo/enfermedad laboral.
 */
export default function FacturacionPage() {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [accidentes, setAccidentes] = useState<Accidente[]>([]);
  const [facturasARL, setFacturasARL] = useState<FacturaARL[]>([]);
  const [empresaId, setEmpresaId] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [accidenteId, setAccidenteId] = useState("");
  const [valorARL, setValorARL] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setFacturas(await apiFetch<Factura[]>("/facturas/"));
    setFacturasARL(await apiFetch<FacturaARL[]>("/facturas-arl/"));
    setAccidentes(await apiFetch<Accidente[]>("/accidentes/"));
  }, []);

  useEffect(() => {
    // Empresas: el coordinador no tiene el endpoint de recepción; se listan
    // desde las facturas/tarifas ya existentes o el admin. Para simplificar,
    // se piden vía tarifas.
    void apiFetch<{ empresa: number; empresa_nombre: string }[]>("/tarifas/").then((ts) => {
      const unicas = new Map<number, string>();
      ts.forEach((t) => unicas.set(t.empresa, t.empresa_nombre));
      setEmpresas([...unicas].map(([id, nombre]) => ({ id, nombre })));
    });
    void cargar();
  }, [cargar]);

  async function generar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await apiFetch("/facturas/generar/", {
        method: "POST",
        body: JSON.stringify({ empresa: Number(empresaId), desde, hasta }),
      });
      void cargar();
    } catch (err) { setMsg((err as Error).message); }
  }

  async function accion(id: number, ruta: string) {
    setMsg(null);
    try {
      await apiFetch(`/facturas/${id}/${ruta}/`, { method: "POST" });
      void cargar();
    } catch (err) { setMsg((err as Error).message); }
  }

  async function generarARL(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    try {
      await apiFetch("/facturas-arl/", {
        method: "POST",
        body: JSON.stringify({ accidente: Number(accidenteId), valor: valorARL }),
      });
      setAccidenteId(""); setValorARL("");
      void cargar();
    } catch (err) { setMsg((err as Error).message); }
  }

  async function validarMUV(id: number) {
    setMsg(null);
    try {
      await apiFetch(`/facturas-arl/${id}/validar_muv/`, { method: "POST" });
      void cargar();
    } catch (err) { setMsg((err as Error).message); }
  }

  const chip = (estado: string) => (
    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${ESTADO_FACTURA[estado] ?? ""}`}>
      {estado}
    </span>
  );

  return (
    <AppShell titulo="Facturación">
      {msg && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{msg}</p>}
      <div className="grid gap-8 xl:grid-cols-2">
        {/* ---------------- Motor estándar (empresas, sin RIPS) ---------------- */}
        <section>
          <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-teal-600">
            Facturas a empresas (sin RIPS)
          </h2>
          <p className="mb-4 text-xs text-gray-500">
            Exámenes ocupacionales pagados por la empresa: fuera del SGSSS, nunca generan RIPS.
          </p>
          <form onSubmit={generar} className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4">
            <label className={labelCls}>
              Empresa
              <select value={empresaId} onChange={(e) => setEmpresaId(e.target.value)} className={inputCls} required>
                <option value="">Seleccionar…</option>
                {empresas.map((e2) => <option key={e2.id} value={e2.id}>{e2.nombre}</option>)}
              </select>
            </label>
            <label className={labelCls}>
              Desde
              <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className={inputCls} required />
            </label>
            <label className={labelCls}>
              Hasta
              <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className={inputCls} required />
            </label>
            <button className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700">
              Generar borrador
            </button>
          </form>
          <div className="space-y-2">
            {facturas.map((f) => (
              <article key={f.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900">
                    {f.numero || `Borrador #${f.id}`} · {f.empresa_nombre}
                  </p>
                  <p className="text-xs text-gray-500">{f.periodo_desde} → {f.periodo_hasta}</p>
                </div>
                <p className="text-sm font-bold text-gray-900">
                  ${Number(f.total).toLocaleString("es-CO")}
                </p>
                {chip(f.estado)}
                {f.estado === "borrador" && (
                  <button onClick={() => accion(f.id, "emitir")}
                    className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700">
                    Emitir
                  </button>
                )}
                {f.estado === "emitida" && (
                  <button onClick={() => accion(f.id, "marcar_pagada")}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">
                    Marcar pagada
                  </button>
                )}
              </article>
            ))}
          </div>
        </section>

        {/* ------------------ Motor ARL (RIPS, solo accidentes) ----------------- */}
        <section>
          <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-red-600">
            Facturas ARL — RIPS (solo accidentes / enfermedad laboral)
          </h2>
          <p className="mb-4 text-xs text-gray-500">
            Único punto del sistema que genera RIPS (Res. 948/2026). Requiere un
            accidente registrado; el CUV se obtiene del MUV.
          </p>
          <form onSubmit={generarARL} className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4">
            <label className={`${labelCls} min-w-56 flex-1`}>
              Accidente / enfermedad
              <select value={accidenteId} onChange={(e) => setAccidenteId(e.target.value)} className={inputCls} required>
                <option value="">Seleccionar…</option>
                {accidentes.map((a) => (
                  <option key={a.id} value={a.id}>
                    #{a.id} · {a.trabajador_nombre} · {a.fecha_evento}
                  </option>
                ))}
              </select>
            </label>
            <label className={labelCls}>
              Valor
              <input type="number" value={valorARL} onChange={(e) => setValorARL(e.target.value)} className={inputCls} required />
            </label>
            <button className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700">
              Generar RIPS
            </button>
          </form>
          <div className="space-y-2">
            {facturasARL.map((f) => (
              <article key={f.id} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900">{f.numero} · {f.trabajador_nombre}</p>
                    <p className="text-xs text-gray-500">${Number(f.valor).toLocaleString("es-CO")}</p>
                  </div>
                  {chip(f.estado)}
                  {f.estado === "borrador" && (
                    <button onClick={() => validarMUV(f.id)}
                      className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-700">
                      Validar en MUV (CUV)
                    </button>
                  )}
                </div>
                {f.cuv && (
                  <p className="mt-2 break-all rounded bg-gray-50 px-2 py-1 font-mono text-[10px] text-gray-500">
                    CUV: {f.cuv}
                  </p>
                )}
              </article>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
