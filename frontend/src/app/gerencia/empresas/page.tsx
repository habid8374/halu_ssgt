"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import SelectUbicacion from "@/components/SelectUbicacion";
import { apiFetch, TIPO_EXAMEN_LABEL } from "@/lib/api";

interface Empresa {
  id: number;
  nombre: string;
  nit: string;
  direccion: string;
  telefono: string;
  email: string;
  activo: boolean;
}
interface Tarifa {
  id: number;
  empresa: number;
  tipo_examen: string;
  valor: string;
}

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Gestión de empresas cliente (convenios) — rol coordinador. Cada IPS crea
 * y administra sus propios convenios y tarifas desde la app, sin admin.
 */
export default function EmpresasPage() {
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [tarifas, setTarifas] = useState<Tarifa[]>([]);
  const [seleccionada, setSeleccionada] = useState<Empresa | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);

  // Formulario de nueva empresa
  const VACIA = {
    nombre: "", nit: "", digito_verificacion: "",
    actividad_economica_ciiu: "", actividad_economica_desc: "",
    clase_riesgo: "", arl_nombre: "",
    departamento: "", municipio: "", municipio_dane: "",
    direccion: "", telefono: "", email: "",
    representante_legal: "", responsable_sst: "", contacto_sst: "",
  };
  const [nueva, setNueva] = useState<Record<string, string>>({ ...VACIA });
  const setN = (k: string, v: string) => setNueva((p) => ({ ...p, [k]: v }));

  const cargar = useCallback(async () => {
    setEmpresas(await apiFetch<Empresa[]>("/empresas/"));
    setTarifas(await apiFetch<Tarifa[]>("/tarifas/"));
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  function abrirTarifario(e: Empresa) {
    setSeleccionada(e);
    const propias = tarifas.filter((t) => t.empresa === e.id);
    const v: Record<string, string> = {};
    Object.keys(TIPO_EXAMEN_LABEL).forEach((tipo) => {
      v[tipo] = propias.find((t) => t.tipo_examen === tipo)?.valor ?? "";
    });
    setValores(v);
  }

  async function crearEmpresa(ev: React.FormEvent) {
    ev.preventDefault();
    setMsg(null);
    try {
      await apiFetch("/empresas/", { method: "POST", body: JSON.stringify(nueva) });
      setNueva({ ...VACIA });
      setMsg("Empresa creada. Ya está disponible en Admisión.");
      void cargar();
    } catch (e) {
      setMsg((e as Error).message.toLowerCase().includes("nit") ? "Ya existe una empresa con ese NIT." : (e as Error).message);
    }
  }

  async function alternarActivo(e: Empresa) {
    await apiFetch(`/empresas/${e.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ activo: !e.activo }),
    });
    void cargar();
  }

  async function guardarTarifas() {
    if (!seleccionada) return;
    setMsg(null);
    const propias = tarifas.filter((t) => t.empresa === seleccionada.id);
    for (const [tipo, valor] of Object.entries(valores)) {
      if (valor === "") continue;
      const existente = propias.find((t) => t.tipo_examen === tipo);
      if (existente) {
        await apiFetch(`/tarifas/${existente.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ valor }),
        });
      } else {
        await apiFetch("/tarifas/", {
          method: "POST",
          body: JSON.stringify({ empresa: seleccionada.id, tipo_examen: tipo, valor }),
        });
      }
    }
    setMsg(`Tarifario de ${seleccionada.nombre} guardado.`);
    setSeleccionada(null);
    void cargar();
  }

  return (
    <AppShell titulo="Empresas cliente (convenios)">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        {/* --------------------------- Nueva empresa --------------------------- */}
        <form onSubmit={crearEmpresa} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
            Nueva empresa (empleador)
          </h2>
          <label className={labelCls}>Razón social *
            <input value={nueva.nombre} onChange={(e) => setN("nombre", e.target.value)} className={inputCls} required />
          </label>
          <div className="mt-3 grid grid-cols-[1fr_80px] gap-3">
            <label className={labelCls}>NIT *
              <input value={nueva.nit} onChange={(e) => setN("nit", e.target.value)} className={inputCls} placeholder="900123456" required />
            </label>
            <label className={labelCls}>DV
              <input value={nueva.digito_verificacion} onChange={(e) => setN("digito_verificacion", e.target.value)} className={inputCls} maxLength={1} placeholder="7" />
            </label>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>Código CIIU
              <input value={nueva.actividad_economica_ciiu} onChange={(e) => setN("actividad_economica_ciiu", e.target.value)} className={inputCls} placeholder="4290" />
            </label>
            <label className={labelCls}>Clase de riesgo
              <select value={nueva.clase_riesgo} onChange={(e) => setN("clase_riesgo", e.target.value)} className={inputCls}>
                <option value="">—</option>
                {["I", "II", "III", "IV", "V"].map((c) => <option key={c} value={c}>Clase {c}</option>)}
              </select>
            </label>
          </div>
          <label className={`${labelCls} mt-3`}>Actividad económica (descripción)
            <input value={nueva.actividad_economica_desc} onChange={(e) => setN("actividad_economica_desc", e.target.value)} className={inputCls} />
          </label>
          <label className={`${labelCls} mt-3`}>ARL
            <input value={nueva.arl_nombre} onChange={(e) => setN("arl_nombre", e.target.value)} className={inputCls} placeholder="Positiva, Sura…" />
          </label>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <SelectUbicacion
              departamento={nueva.departamento}
              municipioDane={nueva.municipio_dane}
              onChange={(v) => setNueva((p) => ({
                ...p,
                departamento: v.departamento,
                municipio: v.municipio,
                municipio_dane: v.municipio_dane,
              }))}
            />
          </div>
          <label className={`${labelCls} mt-3`}>Dirección
            <input value={nueva.direccion} onChange={(e) => setN("direccion", e.target.value)} className={inputCls} />
          </label>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>Teléfono
              <input value={nueva.telefono} onChange={(e) => setN("telefono", e.target.value)} className={inputCls} />
            </label>
            <label className={labelCls}>Correo
              <input type="email" value={nueva.email} onChange={(e) => setN("email", e.target.value)} className={inputCls} />
            </label>
          </div>
          <label className={`${labelCls} mt-3`}>Representante legal
            <input value={nueva.representante_legal} onChange={(e) => setN("representante_legal", e.target.value)} className={inputCls} />
          </label>
          <label className={`${labelCls} mt-3`}>Responsable SST
            <input value={nueva.responsable_sst} onChange={(e) => setN("responsable_sst", e.target.value)} className={inputCls} />
          </label>
          <button type="submit"
            className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700">
            Crear empresa
          </button>
          <p className="mt-3 text-[11px] text-gray-400">
            El acceso al portal de la empresa (usuario y contraseña) se crea en
            Usuarios con el rol «Empresa cliente».
          </p>
        </form>

        {/* ----------------------------- Listado ------------------------------ */}
        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">
            Convenios ({empresas.length})
          </h2>
          <div className="space-y-2">
            {empresas.map((e) => (
              <article key={e.id} className="rounded-xl border border-gray-200 bg-white px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900">{e.nombre}</p>
                    <p className="text-xs text-gray-500">
                      NIT {e.nit}{e.telefono ? ` · ${e.telefono}` : ""}{e.email ? ` · ${e.email}` : ""}
                    </p>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                    e.activo ? "bg-emerald-50 text-emerald-600" : "bg-gray-100 text-gray-500"
                  }`}>
                    {e.activo ? "Activa" : "Inactiva"}
                  </span>
                  <button onClick={() => abrirTarifario(e)}
                    className="rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-semibold text-teal-700 transition hover:bg-teal-100">
                    💲 Tarifario
                  </button>
                  <button onClick={() => alternarActivo(e)}
                    className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 transition hover:bg-gray-200">
                    {e.activo ? "Desactivar" : "Activar"}
                  </button>
                </div>

                {/* Tarifario desplegable */}
                {seleccionada?.id === e.id && (
                  <div className="mt-4 rounded-lg bg-gray-50 p-4">
                    <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Tarifas por tipo de examen (COP)
                    </p>
                    <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
                      {Object.entries(TIPO_EXAMEN_LABEL).map(([tipo, etiqueta]) => (
                        <label key={tipo} className={labelCls}>
                          {etiqueta}
                          <input
                            type="number"
                            min="0"
                            value={valores[tipo] ?? ""}
                            onChange={(ev) => setValores((v) => ({ ...v, [tipo]: ev.target.value }))}
                            className={inputCls}
                            placeholder="0"
                          />
                        </label>
                      ))}
                    </div>
                    <div className="mt-4 flex gap-2">
                      <button onClick={guardarTarifas}
                        className="rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-700">
                        Guardar tarifario
                      </button>
                      <button onClick={() => setSeleccionada(null)}
                        className="rounded-lg bg-gray-200 px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-300">
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
