"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import Combobox, { type ItemCatalogo } from "@/components/Combobox";
import SelectUbicacion from "@/components/SelectUbicacion";
import { apiFetch, TIPO_EXAMEN_LABEL, type Yo } from "@/lib/api";

interface Empresa { id: number; nombre: string }
interface Medico { id: number; nombre_completo: string }
interface Consultorio { id: number; nombre: string }
interface Trabajador {
  id: number; empresa: number;
  tipo_documento: string; numero_documento: string;
  primer_nombre: string; segundo_nombre: string;
  primer_apellido: string; segundo_apellido: string;
  fecha_nacimiento: string | null; sexo: string;
  departamento_residencia: string; municipio_residencia: string;
  municipio_dane: string; zona_territorial: string; direccion: string;
  telefono: string; email: string;
  pertenencia_etnica: string; tipo_afiliacion: string;
  entidad_responsable_pago: string; cargo: string; ocupacion_ciuo: string;
}

const TIPOS_DOC = [
  ["CC", "Cédula de ciudadanía"], ["CE", "Cédula de extranjería"],
  ["TI", "Tarjeta de identidad"], ["RC", "Registro civil"],
  ["PA", "Pasaporte"], ["PE", "Permiso especial (PEP)"],
  ["PT", "Permiso protección temporal (PPT)"], ["CN", "Certificado nacido vivo"],
  ["SC", "Salvoconducto"], ["DE", "Documento extranjero"], ["CD", "Carné diplomático"],
  ["AS", "Adulto sin identificación"], ["MS", "Menor sin identificación"],
] as const;
const SEXOS = [["M", "Masculino"], ["F", "Femenino"], ["I", "Indeterminado"]] as const;
const ZONAS = [["U", "Urbana"], ["R", "Rural"]] as const;
const ETNIAS = [
  ["", "No informa"], ["1", "Indígena"], ["2", "ROM (gitano)"], ["3", "Raizal"],
  ["4", "Palenquero"], ["5", "Afrocolombiano(a)"], ["6", "Ninguna"],
] as const;
const AFILIACIONES = [
  ["", "No informa"], ["contributivo", "Contributivo"], ["subsidiado", "Subsidiado"],
  ["especial", "Régimen especial"], ["particular", "Particular"],
] as const;
const PRUEBAS = [
  ["medicina", "Evaluación médica"], ["visiometria", "Visiometría"],
  ["audiometria", "Audiometría"], ["espirometria", "Espirometría"],
  ["laboratorio", "Laboratorio"], ["psicologia", "Psicología"], ["otro", "Otro paraclínico"],
] as const;

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none disabled:bg-gray-100";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

const VACIO = {
  tipo_documento: "CC", numero_documento: "",
  primer_nombre: "", segundo_nombre: "", primer_apellido: "", segundo_apellido: "",
  fecha_nacimiento: "", sexo: "",
  departamento_residencia: "", municipio_residencia: "", municipio_dane: "",
  zona_territorial: "", direccion: "", telefono: "", email: "",
  pertenencia_etnica: "", tipo_afiliacion: "", entidad_responsable_pago: "",
  empresa: "", cargo: "", ocupacion_ciuo: "",
};

/**
 * Admisión (rol recepción). Registra al trabajador con los datos del conjunto
 * mínimo interoperable (Res. 866/2021) y RIPS (Res. 948/2026), y crea la
 * atención. Los campos con * son obligatorios.
 */
export default function AdmisionPage() {
  const router = useRouter();
  const [sede, setSede] = useState<number | null>(null);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [consultorios, setConsultorios] = useState<Consultorio[]>([]);

  const [f, setF] = useState<Record<string, string>>({ ...VACIO });
  const [existente, setExistente] = useState<Trabajador | null>(null);
  const [buscado, setBuscado] = useState(false);
  const [ciuo, setCiuo] = useState<ItemCatalogo[]>([]);

  const [tipoExamen, setTipoExamen] = useState("pre_ingreso");
  const [medicoId, setMedicoId] = useState("");
  const [consultorioId, setConsultorioId] = useState("");
  const [bateria, setBateria] = useState<string[]>(["medicina"]);
  const [profesiogramaHallado, setProfesiogramaHallado] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));
  const toggleprueba = (t: string) =>
    setBateria((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]));
  const bloqueado = !!existente; // datos personales no editables si ya existe

  // Auto-carga de la batería según profesiograma (empresa + cargo).
  useEffect(() => {
    if (!f.empresa) return;
    const cargo = f.cargo.trim();
    const t = setTimeout(() => {
      void apiFetch<{ encontrado: boolean; pruebas: { tipo_prueba: string }[] }>(
        `/profesiogramas/resolver/?empresa=${f.empresa}&cargo=${encodeURIComponent(cargo)}`,
      ).then((r) => {
        setProfesiogramaHallado(r.encontrado);
        if (r.encontrado) {
          const tipos = Array.from(new Set(["medicina", ...r.pruebas.map((p) => p.tipo_prueba)]));
          setBateria(tipos);
        }
      }).catch(() => {});
    }, 300);
    return () => clearTimeout(t);
  }, [f.empresa, f.cargo]);

  useEffect(() => {
    const raw = localStorage.getItem("halu_yo");
    if (!raw) return;
    const yo = JSON.parse(raw) as Yo;
    setSede(yo.sede ?? 1);
    void apiFetch<Empresa[]>("/empresas/").then(setEmpresas);
    void apiFetch<Medico[]>("/medicos/").then((ms) => {
      setMedicos(ms);
      if (ms.length === 1) setMedicoId(String(ms[0].id));
    });
    void apiFetch<Consultorio[]>(`/consultorios/?sede=${yo.sede ?? 1}`).then(setConsultorios);
    void fetch("/ciuo.json")
      .then((r) => r.json())
      .then((d: { ocupaciones: ItemCatalogo[] }) => setCiuo(d.ocupaciones));
  }, []);

  async function buscar() {
    setError(null); setBuscado(false); setExistente(null);
    if (!f.numero_documento.trim()) return;
    const res = await apiFetch<Trabajador[]>(`/trabajadores/?documento=${f.numero_documento.trim()}`);
    setBuscado(true);
    if (res.length > 0) {
      const t = res[0];
      setExistente(t);
      setF({
        tipo_documento: t.tipo_documento, numero_documento: t.numero_documento,
        primer_nombre: t.primer_nombre, segundo_nombre: t.segundo_nombre,
        primer_apellido: t.primer_apellido, segundo_apellido: t.segundo_apellido,
        fecha_nacimiento: t.fecha_nacimiento ?? "", sexo: t.sexo,
        departamento_residencia: t.departamento_residencia, municipio_residencia: t.municipio_residencia,
        municipio_dane: t.municipio_dane, zona_territorial: t.zona_territorial,
        direccion: t.direccion, telefono: t.telefono, email: t.email,
        pertenencia_etnica: t.pertenencia_etnica, tipo_afiliacion: t.tipo_afiliacion,
        entidad_responsable_pago: t.entidad_responsable_pago,
        empresa: String(t.empresa), cargo: t.cargo, ocupacion_ciuo: t.ocupacion_ciuo,
      });
    }
  }

  async function admitir(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setGuardando(true);
    try {
      let id = existente?.id;
      if (!existente) {
        const { empresa, ...resto } = f;
        const t = await apiFetch<Trabajador>("/trabajadores/", {
          method: "POST",
          body: JSON.stringify({ ...resto, empresa: Number(empresa) }),
        });
        id = t.id;
      }
      await apiFetch("/atenciones/", {
        method: "POST",
        body: JSON.stringify({
          trabajador: id, sede, tipo_examen: tipoExamen,
          profesional_asignado: medicoId ? Number(medicoId) : null,
          consultorio: consultorioId ? Number(consultorioId) : null,
          pruebas: bateria,
        }),
      });
      router.push("/recepcion");
    } catch (err) {
      setError((err as Error).message);
      setGuardando(false);
    }
  }

  const Sel = ({ k, req, children, disabled }: { k: string; req?: boolean; children: React.ReactNode; disabled?: boolean }) => (
    <select value={f[k]} onChange={(e) => set(k, e.target.value)} className={inputCls} required={req} disabled={disabled ?? bloqueado}>
      {children}
    </select>
  );

  return (
    <AppShell titulo="Admisión — Registrar atención">
      <form onSubmit={admitir} className="space-y-6">
        {/* Buscar por documento */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-teal-600">Identificación</h2>
          <div className="flex flex-wrap items-end gap-3">
            <label className={`${labelCls} w-56`}>
              Tipo de documento *
              <Sel k="tipo_documento" req disabled={bloqueado}>
                {TIPOS_DOC.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </Sel>
            </label>
            <label className={`${labelCls} w-56`}>
              Número de documento *
              <input value={f.numero_documento} onChange={(e) => set("numero_documento", e.target.value)}
                className={inputCls} placeholder="1010101010" required disabled={bloqueado} />
            </label>
            <button type="button" onClick={buscar}
              className="h-[38px] rounded-lg bg-gray-200 px-4 text-sm font-semibold text-gray-900 hover:bg-gray-300">
              Buscar
            </button>
          </div>
          {buscado && (
            <p className={`mt-3 rounded-lg px-3 py-2 text-sm ${existente ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-700"}`}>
              {existente ? "Trabajador encontrado: sus datos ya están registrados (solo lectura)." : "No existe: diligencia los datos para registrarlo."}
            </p>
          )}
        </section>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Datos personales */}
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Datos personales</h2>
            <div className="grid grid-cols-2 gap-3">
              <label className={labelCls}>Primer nombre *
                <input value={f.primer_nombre} onChange={(e) => set("primer_nombre", e.target.value)} className={inputCls} required disabled={bloqueado} /></label>
              <label className={labelCls}>Segundo nombre
                <input value={f.segundo_nombre} onChange={(e) => set("segundo_nombre", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
              <label className={labelCls}>Primer apellido *
                <input value={f.primer_apellido} onChange={(e) => set("primer_apellido", e.target.value)} className={inputCls} required disabled={bloqueado} /></label>
              <label className={labelCls}>Segundo apellido
                <input value={f.segundo_apellido} onChange={(e) => set("segundo_apellido", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
              <label className={labelCls}>Fecha de nacimiento *
                <input type="date" value={f.fecha_nacimiento} onChange={(e) => set("fecha_nacimiento", e.target.value)} className={inputCls} required disabled={bloqueado} /></label>
              <label className={labelCls}>Sexo *
                <Sel k="sexo" req><option value="">Seleccionar…</option>{SEXOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Sel></label>
              <label className={labelCls}>Pertenencia étnica
                <Sel k="pertenencia_etnica">{ETNIAS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Sel></label>
              <label className={labelCls}>Tipo de afiliación
                <Sel k="tipo_afiliacion">{AFILIACIONES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Sel></label>
              <label className={`${labelCls} col-span-2`}>EPS / EAPB
                <input value={f.entidad_responsable_pago} onChange={(e) => set("entidad_responsable_pago", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
            </div>
          </section>

          {/* Residencia y contacto */}
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Residencia y contacto</h2>
            <div className="grid grid-cols-2 gap-3">
              <SelectUbicacion
                departamento={f.departamento_residencia}
                municipioDane={f.municipio_dane}
                disabled={bloqueado}
                onChange={(v) => setF((p) => ({
                  ...p,
                  departamento_residencia: v.departamento,
                  municipio_residencia: v.municipio,
                  municipio_dane: v.municipio_dane,
                }))}
              />
              <label className={labelCls}>Zona
                <Sel k="zona_territorial"><option value="">Seleccionar…</option>{ZONAS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Sel></label>
              <label className={`${labelCls} col-span-2`}>Dirección
                <input value={f.direccion} onChange={(e) => set("direccion", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
              <label className={labelCls}>Teléfono
                <input value={f.telefono} onChange={(e) => set("telefono", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
              <label className={labelCls}>Correo
                <input type="email" value={f.email} onChange={(e) => set("email", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
            </div>
          </section>

          {/* Datos laborales */}
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Datos laborales</h2>
            <div className="grid grid-cols-2 gap-3">
              <label className={`${labelCls} col-span-2`}>Empresa (convenio) *
                <Sel k="empresa" req><option value="">Seleccionar…</option>{empresas.map((em) => <option key={em.id} value={em.id}>{em.nombre}</option>)}</Sel></label>
              <label className={labelCls}>Cargo
                <input value={f.cargo} onChange={(e) => set("cargo", e.target.value)} className={inputCls} disabled={bloqueado} /></label>
              <label className={labelCls}>Ocupación (CIUO)
                <div className="mt-1">
                  <Combobox
                    items={ciuo}
                    value={f.ocupacion_ciuo}
                    disabled={bloqueado}
                    placeholder="Buscar ocupación…"
                    onSelect={(o) => set("ocupacion_ciuo", o?.codigo ?? "")}
                  />
                </div></label>
            </div>
          </section>

          {/* Atención */}
          <section className="h-fit rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">Atención</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              <label className={labelCls}>Tipo de examen *
                <select value={tipoExamen} onChange={(e) => setTipoExamen(e.target.value)} className={inputCls}>
                  {Object.entries(TIPO_EXAMEN_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select></label>
              <label className={labelCls}>Médico asignado *
                <select value={medicoId} onChange={(e) => setMedicoId(e.target.value)} className={inputCls} required>
                  <option value="">Seleccionar…</option>
                  {medicos.map((m) => <option key={m.id} value={m.id}>{m.nombre_completo}</option>)}
                </select></label>
              <label className={labelCls}>Consultorio
                <select value={consultorioId} onChange={(e) => setConsultorioId(e.target.value)} className={inputCls}>
                  <option value="">Sin asignar</option>
                  {consultorios.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                </select></label>
            </div>

            {/* Batería de pruebas (circuito). Se autocarga del profesiograma. */}
            <div className="mt-4">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                Circuito de pruebas
                {profesiogramaHallado
                  ? <span className="ml-2 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600">Profesiograma cargado</span>
                  : <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">Sin profesiograma — selección manual</span>}
              </p>
              <div className="flex flex-wrap gap-2">
                {PRUEBAS.map(([v, l]) => (
                  <button type="button" key={v} onClick={() => toggleprueba(v)}
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                      bateria.includes(v)
                        ? "bg-teal-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}>
                    {bateria.includes(v) ? "✓ " : ""}{l}
                  </button>
                ))}
              </div>
            </div>
          </section>
        </div>

        {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={guardando}
          className="rounded-lg bg-teal-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
          {guardando ? "Registrando…" : "Registrar atención"}
        </button>
      </form>
    </AppShell>
  );
}
