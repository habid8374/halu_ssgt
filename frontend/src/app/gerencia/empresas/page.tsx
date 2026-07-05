"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
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
  const [nombre, setNombre] = useState("");
  const [nit, setNit] = useState("");
  const [telefono, setTelefono] = useState("");
  const [email, setEmail] = useState("");

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
      await apiFetch("/empresas/", {
        method: "POST",
        body: JSON.stringify({ nombre, nit, telefono, email }),
      });
      setNombre(""); setNit(""); setTelefono(""); setEmail("");
      setMsg("Empresa creada. Ya está disponible en Admisión.");
      void cargar();
    } catch (e) {
      setMsg((e as Error).message.includes("nit") ? "Ya existe una empresa con ese NIT." : (e as Error).message);
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

      <div className="grid gap-6 xl:grid-cols-[380px_1fr]">
        {/* --------------------------- Nueva empresa --------------------------- */}
        <form onSubmit={crearEmpresa} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
            Nueva empresa
          </h2>
          <label className={labelCls}>
            Razón social
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} className={inputCls} required />
          </label>
          <label className={`${labelCls} mt-3`}>
            NIT
            <input value={nit} onChange={(e) => setNit(e.target.value)} className={inputCls} placeholder="900123456-7" required />
          </label>
          <label className={`${labelCls} mt-3`}>
            Teléfono
            <input value={telefono} onChange={(e) => setTelefono(e.target.value)} className={inputCls} />
          </label>
          <label className={`${labelCls} mt-3`}>
            Correo
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} />
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
