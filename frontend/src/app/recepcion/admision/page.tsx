"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch, TIPO_EXAMEN_LABEL, type Yo } from "@/lib/api";

interface Empresa {
  id: number;
  nombre: string;
}
interface Medico {
  id: number;
  nombre_completo: string;
}
interface Consultorio {
  id: number;
  nombre: string;
}
interface Trabajador {
  id: number;
  empresa: number;
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellidos: string;
  cargo: string;
}

const TIPOS_DOC = [
  ["CC", "Cédula de ciudadanía"],
  ["CE", "Cédula de extranjería"],
  ["TI", "Tarjeta de identidad"],
  ["PA", "Pasaporte"],
  ["PEP", "PEP"],
  ["PPT", "PPT"],
] as const;

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Admisión (rol recepción): busca o registra al trabajador y crea la
 * atención en estado "registrado" — la tarjeta aparece de inmediato en el
 * tablero (evento en tiempo real al pasarla a espera).
 */
export default function AdmisionPage() {
  const router = useRouter();
  const [sede, setSede] = useState<number | null>(null);

  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [consultorios, setConsultorios] = useState<Consultorio[]>([]);

  // Paso 1: trabajador
  const [tipoDoc, setTipoDoc] = useState("CC");
  const [numDoc, setNumDoc] = useState("");
  const [trabajador, setTrabajador] = useState<Trabajador | null>(null);
  const [buscado, setBuscado] = useState(false);
  const [nombres, setNombres] = useState("");
  const [apellidos, setApellidos] = useState("");
  const [empresaId, setEmpresaId] = useState("");
  const [cargo, setCargo] = useState("");

  // Paso 2: atención
  const [tipoExamen, setTipoExamen] = useState("pre_ingreso");
  const [medicoId, setMedicoId] = useState("");
  const [consultorioId, setConsultorioId] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

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
  }, []);

  async function buscar() {
    setError(null);
    setBuscado(false);
    setTrabajador(null);
    if (!numDoc.trim()) return;
    const res = await apiFetch<Trabajador[]>(`/trabajadores/?documento=${numDoc.trim()}`);
    setBuscado(true);
    if (res.length > 0) {
      const t = res[0];
      setTrabajador(t);
      setNombres(t.nombres);
      setApellidos(t.apellidos);
      setEmpresaId(String(t.empresa));
      setCargo(t.cargo);
    } else {
      setNombres("");
      setApellidos("");
      setCargo("");
    }
  }

  async function admitir(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setGuardando(true);
    try {
      let t = trabajador;
      if (!t) {
        t = await apiFetch<Trabajador>("/trabajadores/", {
          method: "POST",
          body: JSON.stringify({
            tipo_documento: tipoDoc,
            numero_documento: numDoc.trim(),
            nombres,
            apellidos,
            empresa: Number(empresaId),
            cargo,
          }),
        });
      }
      await apiFetch("/atenciones/", {
        method: "POST",
        body: JSON.stringify({
          trabajador: t.id,
          sede,
          tipo_examen: tipoExamen,
          profesional_asignado: medicoId ? Number(medicoId) : null,
          consultorio: consultorioId ? Number(consultorioId) : null,
        }),
      });
      router.push("/recepcion");
    } catch (err) {
      setError((err as Error).message);
      setGuardando(false);
    }
  }

  return (
    <AppShell titulo="Admisión — Registrar atención">
      <form onSubmit={admitir} className="max-w-2xl space-y-6">
        {/* ------------------------- Paso 1: trabajador ------------------------ */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
            1 · Trabajador
          </h2>
          <div className="flex gap-3">
            <label className={`${labelCls} w-40`}>
              Tipo doc.
              <select value={tipoDoc} onChange={(e) => setTipoDoc(e.target.value)} className={inputCls}>
                {TIPOS_DOC.map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </label>
            <label className={`${labelCls} flex-1`}>
              Número de documento
              <input value={numDoc} onChange={(e) => setNumDoc(e.target.value)} className={inputCls} placeholder="1010101010" required />
            </label>
            <button type="button" onClick={buscar}
              className="mt-5 h-9 rounded-lg bg-gray-200 px-4 text-sm font-semibold text-gray-900 transition hover:bg-gray-300">
              Buscar
            </button>
          </div>

          {buscado && (
            <p className={`mt-3 rounded-lg px-3 py-2 text-sm ${trabajador ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-700"}`}>
              {trabajador
                ? `Trabajador encontrado: ${trabajador.nombres} ${trabajador.apellidos}`
                : "No existe: diligencia los datos para registrarlo."}
            </p>
          )}

          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className={labelCls}>
              Nombres
              <input value={nombres} onChange={(e) => setNombres(e.target.value)} className={inputCls} required disabled={!!trabajador} />
            </label>
            <label className={labelCls}>
              Apellidos
              <input value={apellidos} onChange={(e) => setApellidos(e.target.value)} className={inputCls} required disabled={!!trabajador} />
            </label>
            <label className={labelCls}>
              Empresa (convenio)
              <select value={empresaId} onChange={(e) => setEmpresaId(e.target.value)} className={inputCls} required disabled={!!trabajador}>
                <option value="">Seleccionar…</option>
                {empresas.map((em) => (
                  <option key={em.id} value={em.id}>{em.nombre}</option>
                ))}
              </select>
            </label>
            <label className={labelCls}>
              Cargo
              <input value={cargo} onChange={(e) => setCargo(e.target.value)} className={inputCls} disabled={!!trabajador} />
            </label>
          </div>
        </section>

        {/* -------------------------- Paso 2: atención ------------------------- */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-teal-600">
            2 · Atención
          </h2>
          <div className="grid grid-cols-3 gap-3">
            <label className={labelCls}>
              Tipo de examen
              <select value={tipoExamen} onChange={(e) => setTipoExamen(e.target.value)} className={inputCls}>
                {Object.entries(TIPO_EXAMEN_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </label>
            <label className={labelCls}>
              Médico asignado
              <select value={medicoId} onChange={(e) => setMedicoId(e.target.value)} className={inputCls} required>
                <option value="">Seleccionar…</option>
                {medicos.map((m) => (
                  <option key={m.id} value={m.id}>{m.nombre_completo}</option>
                ))}
              </select>
            </label>
            <label className={labelCls}>
              Consultorio
              <select value={consultorioId} onChange={(e) => setConsultorioId(e.target.value)} className={inputCls}>
                <option value="">Sin asignar</option>
                {consultorios.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </label>
          </div>
        </section>

        {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={guardando}
          className="rounded-lg bg-teal-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
          {guardando ? "Registrando…" : "Registrar atención"}
        </button>
      </form>
    </AppShell>
  );
}
