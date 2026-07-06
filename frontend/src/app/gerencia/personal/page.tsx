"use client";

import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Sede { id: number; nombre: string }
interface Empresa { id: number; nombre: string }
interface Usuario {
  id: number;
  email: string;
  nombre_completo: string;
  rol: string;
  rol_display: string;
  sede: number | null;
  sede_nombre: string | null;
  empresa: number | null;
  empresa_nombre: string | null;
  is_active: boolean;
  registro_profesional: string;
  especialidad: string;
  tiene_licencia_vigente: boolean;
}

const ROLES = [
  ["medico", "Médico ocupacional"],
  ["psicologo_sst", "Psicólogo SST"],
  ["recepcion", "Recepción / Admisión"],
  ["coordinador", "Coordinador / Gerencia"],
  ["empresa_cliente", "Empresa cliente (portal)"],
] as const;
const CLINICOS = new Set(["medico", "psicologo_sst"]);
const CON_SEDE = new Set(["medico", "psicologo_sst", "recepcion"]);

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

const VACIO = {
  rol: "medico", nombre_completo: "", email: "", password: "",
  sede: "", empresa: "",
  registro_profesional: "", especialidad: "",
  licencia_numero: "", licencia_entidad: "", licencia_expedicion: "", licencia_vencimiento: "",
};

/**
 * Administración de personal de la IPS (rol coordinador). Alta de médicos y
 * especialistas, psicólogos SST, recepción, coordinadores y usuarios del
 * portal de empresa — con su ficha profesional y licencia SST. Todo in-app.
 */
export default function PersonalPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [sedes, setSedes] = useState<Sede[]>([]);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [f, setF] = useState<Record<string, string>>({ ...VACIO });
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));
  const esClinico = CLINICOS.has(f.rol);
  const requiereSede = CON_SEDE.has(f.rol);
  const requiereEmpresa = f.rol === "empresa_cliente";

  const cargar = useCallback(async () => {
    setUsuarios(await apiFetch<Usuario[]>("/usuarios/"));
    setSedes(await apiFetch<Sede[]>("/sedes/"));
    setEmpresas(await apiFetch<Empresa[]>("/empresas/"));
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  async function crear(ev: React.FormEvent) {
    ev.preventDefault();
    setMsg(null); setError(null); setGuardando(true);
    const payload: Record<string, unknown> = {
      rol: f.rol, nombre_completo: f.nombre_completo, email: f.email, password: f.password,
      sede: requiereSede ? Number(f.sede) : null,
      empresa: requiereEmpresa ? Number(f.empresa) : null,
    };
    if (esClinico) {
      payload.registro_profesional = f.registro_profesional;
      payload.especialidad = f.especialidad;
      if (f.licencia_numero) {
        payload.licencia_numero = f.licencia_numero;
        payload.licencia_entidad = f.licencia_entidad;
        payload.licencia_expedicion = f.licencia_expedicion || null;
        payload.licencia_vencimiento = f.licencia_vencimiento || null;
      }
    }
    try {
      await apiFetch("/usuarios/", { method: "POST", body: JSON.stringify(payload) });
      setF({ ...VACIO });
      setMsg("Personal creado. Ya puede iniciar sesión con su correo y contraseña.");
      void cargar();
    } catch (e) {
      setError(limpiarError((e as Error).message));
    } finally {
      setGuardando(false);
    }
  }

  async function alternarActivo(u: Usuario) {
    await apiFetch(`/usuarios/${u.id}/`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    void cargar();
  }

  async function restablecerClave(u: Usuario) {
    const nueva = window.prompt(`Nueva contraseña para ${u.nombre_completo} (mín. 8):`);
    if (!nueva) return;
    try {
      await apiFetch(`/usuarios/${u.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ password: nueva }),
      });
      setMsg(`Contraseña de ${u.nombre_completo} actualizada.`);
    } catch (e) {
      setError(limpiarError((e as Error).message));
    }
  }

  return (
    <AppShell titulo="Personal de la IPS">
      {msg && <p className="mb-4 rounded-lg bg-teal-50 px-3 py-2 text-sm text-teal-700">{msg}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="grid gap-6 xl:grid-cols-[440px_1fr]">
        {/* ------------------------- Alta de personal ------------------------- */}
        <form onSubmit={crear} className="h-fit rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
            Nuevo integrante
          </h2>

          <label className={labelCls}>Rol *
            <select value={f.rol} onChange={(e) => set("rol", e.target.value)} className={inputCls}>
              {ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>

          <label className={`${labelCls} mt-3`}>Nombre completo *
            <input value={f.nombre_completo} onChange={(e) => set("nombre_completo", e.target.value)} className={inputCls} required />
          </label>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className={labelCls}>Correo (usuario) *
              <input type="email" value={f.email} onChange={(e) => set("email", e.target.value)} className={inputCls} placeholder="dra.perez@ips.co" required />
            </label>
            <label className={labelCls}>Contraseña *
              <input type="password" value={f.password} onChange={(e) => set("password", e.target.value)} className={inputCls} minLength={8} placeholder="mín. 8 caracteres" required />
            </label>
          </div>

          {requiereSede && (
            <label className={`${labelCls} mt-3`}>Sede *
              <select value={f.sede} onChange={(e) => set("sede", e.target.value)} className={inputCls} required>
                <option value="">Seleccionar…</option>
                {sedes.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}
              </select>
            </label>
          )}

          {requiereEmpresa && (
            <label className={`${labelCls} mt-3`}>Empresa asociada *
              <select value={f.empresa} onChange={(e) => set("empresa", e.target.value)} className={inputCls} required>
                <option value="">Seleccionar…</option>
                {empresas.map((em) => <option key={em.id} value={em.id}>{em.nombre}</option>)}
              </select>
            </label>
          )}

          {esClinico && (
            <div className="mt-4 rounded-lg bg-gray-50 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Ficha profesional {f.rol === "medico" ? "(médico)" : "(psicólogo)"}
              </p>
              <div className="grid grid-cols-2 gap-3">
                <label className={labelCls}>Registro / T.P.
                  <input value={f.registro_profesional} onChange={(e) => set("registro_profesional", e.target.value)} className={inputCls} placeholder="RM 12345" />
                </label>
                <label className={labelCls}>Especialidad
                  <input value={f.especialidad} onChange={(e) => set("especialidad", e.target.value)} className={inputCls} placeholder="Medicina del trabajo" />
                </label>
              </div>
              <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Licencia SST (para firmar conceptos)
              </p>
              <div className="grid grid-cols-2 gap-3">
                <label className={labelCls}>Número
                  <input value={f.licencia_numero} onChange={(e) => set("licencia_numero", e.target.value)} className={inputCls} placeholder="Lic. SST N°" />
                </label>
                <label className={labelCls}>Entidad que expide
                  <input value={f.licencia_entidad} onChange={(e) => set("licencia_entidad", e.target.value)} className={inputCls} placeholder="Secretaría de Salud…" />
                </label>
                <label className={labelCls}>Expedición
                  <input type="date" value={f.licencia_expedicion} onChange={(e) => set("licencia_expedicion", e.target.value)} className={inputCls} />
                </label>
                <label className={labelCls}>Vencimiento
                  <input type="date" value={f.licencia_vencimiento} onChange={(e) => set("licencia_vencimiento", e.target.value)} className={inputCls} />
                </label>
              </div>
              <p className="mt-2 text-[11px] text-gray-400">
                La licencia se registra como validada. Sin licencia vigente el
                profesional no podrá firmar conceptos de aptitud.
              </p>
            </div>
          )}

          <button type="submit" disabled={guardando}
            className="mt-4 w-full rounded-lg bg-teal-600 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
            {guardando ? "Creando…" : "Crear integrante"}
          </button>
        </form>

        {/* ---------------------------- Directorio ---------------------------- */}
        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-gray-500">
            Equipo ({usuarios.length})
          </h2>
          <div className="space-y-2">
            {usuarios.map((u) => (
              <article key={u.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900">
                    {u.nombre_completo}
                    {u.especialidad ? <span className="font-normal text-gray-500"> · {u.especialidad}</span> : null}
                  </p>
                  <p className="text-xs text-gray-500">
                    {u.email} · {u.rol_display}
                    {u.sede_nombre ? ` · ${u.sede_nombre}` : ""}
                    {u.empresa_nombre ? ` · ${u.empresa_nombre}` : ""}
                  </p>
                </div>
                {CLINICOS.has(u.rol) && (
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                    u.tiene_licencia_vigente ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-700"
                  }`}>
                    {u.tiene_licencia_vigente ? "Licencia vigente" : "Sin licencia vigente"}
                  </span>
                )}
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                  u.is_active ? "bg-emerald-50 text-emerald-600" : "bg-gray-100 text-gray-500"
                }`}>
                  {u.is_active ? "Activo" : "Inactivo"}
                </span>
                <button onClick={() => restablecerClave(u)}
                  className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 transition hover:bg-gray-200">
                  🔑 Contraseña
                </button>
                <button onClick={() => alternarActivo(u)}
                  className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 transition hover:bg-gray-200">
                  {u.is_active ? "Desactivar" : "Activar"}
                </button>
              </article>
            ))}
            {usuarios.length === 0 && (
              <p className="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-400">
                Aún no hay personal registrado. Crea el primer integrante a la izquierda.
              </p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function limpiarError(m: string): string {
  const s = m.replace(/^API \d+:\s*/, "");
  try {
    const j = JSON.parse(s);
    const primero = Object.values(j)[0];
    return Array.isArray(primero) ? String(primero[0]) : String(primero);
  } catch {
    return s.length > 200 ? "No se pudo guardar. Revisa los datos." : s;
  }
}
