"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import DiagnosticosSection from "@/components/medico/DiagnosticosSection";
import OrdenesSection from "@/components/medico/OrdenesSection";
import RecetasSection from "@/components/medico/RecetasSection";
import PruebasSection from "@/components/medico/PruebasSection";
import type { EncabezadoImpresion, Membrete } from "@/lib/imprimir";
import { cargarMembrete } from "@/lib/membrete";
import { imprimirHistoriaCompleta } from "@/lib/historiaPdf";
import { imprimirConcepto } from "@/lib/conceptoPdf";
import { apiFetch, TIPO_EXAMEN_LABEL, type Atencion } from "@/lib/api";

interface Historia {
  id: number;
  atencion: number;
  motivo_consulta: string;
  antecedentes: string;
  antecedentes_laborales: string;
  revision_sistemas: string;
  examen_fisico: string;
  diagnosticos: string;
  analisis: string;
  plan_manejo: string;
  recomendaciones: string;
  peso_kg: string;
  talla_cm: string;
  presion_arterial: string;
  frecuencia_cardiaca: string;
  frecuencia_respiratoria: string;
  temperatura: string;
  saturacion_o2: string;
}

const VITALES: Array<[keyof Historia, string, string]> = [
  ["peso_kg", "Peso (kg)", "70"],
  ["talla_cm", "Talla (cm)", "170"],
  ["presion_arterial", "T/A", "120/80"],
  ["frecuencia_cardiaca", "FC", "72"],
  ["frecuencia_respiratoria", "FR", "16"],
  ["temperatura", "Temp (°C)", "36.5"],
  ["saturacion_o2", "SatO₂ (%)", "98"],
];

interface Concepto {
  id: number;
  atencion: number;
  historia: number;
  aptitud: string;
  restricciones: string;
  recomendaciones_laborales: string;
  firmado: boolean;
  fecha_emision: string | null;
}

const CAMPOS_HISTORIA: Array<[keyof Historia, string]> = [
  ["motivo_consulta", "Motivo de consulta"],
  ["antecedentes", "Antecedentes personales / familiares"],
  ["antecedentes_laborales", "Antecedentes laborales (ocupacionales)"],
  ["revision_sistemas", "Revisión por sistemas"],
  ["examen_fisico", "Examen físico"],
  ["diagnosticos", "Diagnósticos (texto libre)"],
  ["analisis", "Análisis"],
  ["plan_manejo", "Plan de manejo"],
  ["recomendaciones", "Recomendaciones"],
];

const APTITUDES = [
  ["apto", "Apto"],
  ["apto_restricciones", "Apto con restricciones"],
  ["no_apto", "No apto"],
  ["aplazado", "Aplazado"],
] as const;

const areaCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none";
const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

/**
 * Atención en consultorio (rol médico). Historia clínica RESERVADA (solo el
 * médico asignado la ve; toda lectura queda auditada en el backend) y
 * concepto de aptitud (lo único que verá la empresa, tras firmarse con
 * licencia SST vigente).
 */
export default function AtencionPage({ params }: { params: { id: string } }) {
  const atencionId = Number(params.id);

  const [atencion, setAtencion] = useState<Atencion | null>(null);
  const [historia, setHistoria] = useState<Partial<Historia>>({});
  const [concepto, setConcepto] = useState<Partial<Concepto>>({ aptitud: "apto" });
  const [msg, setMsg] = useState<{ tipo: "ok" | "error"; texto: string } | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [medicoNombre, setMedicoNombre] = useState("");
  const [membrete, setMembrete] = useState<Membrete | undefined>(undefined);

  useEffect(() => {
    const raw = typeof window !== "undefined" ? localStorage.getItem("halu_yo") : null;
    if (raw) setMedicoNombre((JSON.parse(raw) as { nombre_completo?: string }).nombre_completo ?? "");
    void cargarMembrete().then(setMembrete);
  }, []);

  const encabezado: EncabezadoImpresion = {
    ips: typeof window !== "undefined" ? window.location.hostname : "IPS",
    paciente: atencion?.trabajador_nombre ?? "",
    documento: atencion?.trabajador_documento,
    empresa: atencion?.empresa_nombre ?? undefined,
    profesional: medicoNombre,
    membrete,
  };

  const cargar = useCallback(async () => {
    setAtencion(await apiFetch<Atencion>(`/atenciones/${atencionId}/`));
    const hs = await apiFetch<Historia[]>(`/historias/?atencion=${atencionId}`);
    if (hs.length) setHistoria(hs[0]);
    const cs = await apiFetch<Concepto[]>(`/conceptos/?atencion=${atencionId}`);
    if (cs.length) setConcepto(cs[0]);
  }, [atencionId]);

  useEffect(() => {
    cargar().catch((e) => setMsg({ tipo: "error", texto: (e as Error).message }));
  }, [cargar]);

  function setH(campo: keyof Historia, valor: string) {
    setHistoria((h) => ({ ...h, [campo]: valor }));
  }

  async function guardarHistoria() {
    setGuardando(true);
    setMsg(null);
    try {
      if (historia.id) {
        const { id, atencion: _a, ...campos } = historia;
        const h = await apiFetch<Historia>(`/historias/${id}/`, {
          method: "PATCH",
          body: JSON.stringify(campos),
        });
        setHistoria(h);
      } else {
        const h = await apiFetch<Historia>("/historias/", {
          method: "POST",
          body: JSON.stringify({ ...historia, atencion: atencionId }),
        });
        setHistoria(h);
      }
      setMsg({ tipo: "ok", texto: "Historia clínica guardada." });
    } catch (e) {
      setMsg({ tipo: "error", texto: (e as Error).message });
    }
    setGuardando(false);
  }

  async function guardarConcepto() {
    if (!historia.id) {
      setMsg({ tipo: "error", texto: "Guarda primero la historia clínica." });
      return;
    }
    setGuardando(true);
    setMsg(null);
    try {
      if (concepto.id) {
        const c = await apiFetch<Concepto>(`/conceptos/${concepto.id}/`, {
          method: "PATCH",
          body: JSON.stringify({
            aptitud: concepto.aptitud,
            restricciones: concepto.restricciones ?? "",
            recomendaciones_laborales: concepto.recomendaciones_laborales ?? "",
          }),
        });
        setConcepto(c);
      } else {
        const c = await apiFetch<Concepto>("/conceptos/", {
          method: "POST",
          body: JSON.stringify({
            atencion: atencionId,
            historia: historia.id,
            aptitud: concepto.aptitud,
            restricciones: concepto.restricciones ?? "",
            recomendaciones_laborales: concepto.recomendaciones_laborales ?? "",
          }),
        });
        setConcepto(c);
      }
      setMsg({ tipo: "ok", texto: "Concepto guardado (borrador, sin firmar)." });
    } catch (e) {
      setMsg({ tipo: "error", texto: (e as Error).message });
    }
    setGuardando(false);
  }

  async function firmar() {
    if (!concepto.id) return;
    setGuardando(true);
    setMsg(null);
    try {
      const c = await apiFetch<Concepto>(`/conceptos/${concepto.id}/firmar/`, { method: "POST" });
      setConcepto(c);
      setMsg({ tipo: "ok", texto: "Concepto FIRMADO: ya es visible para la empresa en su portal." });
    } catch (e) {
      setMsg({ tipo: "error", texto: (e as Error).message });
    }
    setGuardando(false);
  }

  return (
    <AppShell titulo={`Atención #${params.id}`}>
      <div className="mb-4">
        <Link href="/consultorio/mi-cola" className="text-sm text-teal-600 hover:underline">
          ← Volver a mi cola
        </Link>
        <button
          onClick={async () => {
            const rda = await apiFetch(`/atenciones/${atencionId}/rda/`);
            const blob = new Blob([JSON.stringify(rda, null, 2)], { type: "application/fhir+json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `rda_atencion_${atencionId}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="ml-4 rounded-lg bg-gray-200 px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-300"
          title="Resumen Digital de Atención — FHIR (Res. 866/2021)"
        >
          ⬇ RDA (FHIR)
        </button>
        <button
          onClick={async () => {
            if (!atencion) return;
            try {
              await imprimirHistoriaCompleta(atencion, medicoNombre);
            } catch (e) {
              setMsg({ tipo: "error", texto: (e as Error).message });
            }
          }}
          className="ml-2 rounded-lg bg-teal-600 px-3 py-1 text-xs font-semibold text-white hover:bg-teal-700"
          title="Imprimir o guardar como PDF la historia clínica completa"
        >
          🖨 Imprimir historia (PDF)
        </button>
      </div>

      {atencion && (
        <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white px-5 py-4">
          <div>
            <p className="text-lg font-bold text-gray-900">{atencion.trabajador_nombre}</p>
            <p className="text-sm text-gray-500">{atencion.empresa_nombre}</p>
          </div>
          <span className="rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
            {TIPO_EXAMEN_LABEL[atencion.tipo_examen] ?? atencion.tipo_examen}
          </span>
          <span className="rounded bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700">
            {atencion.estado}
          </span>
        </div>
      )}

      {msg && (
        <p className={`mb-4 rounded-lg px-3 py-2 text-sm ${msg.tipo === "ok" ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"}`}>
          {msg.texto}
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        {/* --------------------- Historia clínica (reservada) -------------------- */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wide text-teal-600">
              Historia clínica ocupacional
            </h2>
            <span className="rounded bg-red-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-red-600">
              Reservada — solo médico
            </span>
          </div>
          {/* Signos vitales / antropometría */}
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Signos vitales</p>
          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {VITALES.map(([campo, etiqueta, ph]) => (
              <label key={campo} className="block text-[11px] font-medium uppercase tracking-wide text-gray-500">
                {etiqueta}
                <input
                  className={areaCls}
                  placeholder={ph}
                  value={(historia[campo] as string) ?? ""}
                  onChange={(e) => setH(campo, e.target.value)}
                />
              </label>
            ))}
          </div>
          <div className="space-y-3">
            {CAMPOS_HISTORIA.map(([campo, etiqueta]) => (
              <label key={campo} className={labelCls}>
                {etiqueta}
                <textarea
                  rows={2}
                  className={areaCls}
                  value={(historia[campo] as string) ?? ""}
                  onChange={(e) => setH(campo, e.target.value)}
                />
              </label>
            ))}
          </div>
          <button onClick={guardarHistoria} disabled={guardando}
            className="mt-4 rounded-lg bg-teal-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:opacity-50">
            Guardar historia
          </button>
        </section>

        {/* ------------------- Concepto (visible al empleador) ------------------- */}
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wide text-teal-600">
              Concepto médico ocupacional
            </h2>
            {concepto.firmado ? (
              <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-600">
                ✓ Firmado {concepto.fecha_emision}
              </span>
            ) : (
              <span className="rounded bg-gray-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-gray-600">
                Borrador
              </span>
            )}
          </div>
          <p className="mb-3 text-xs text-gray-500">
            Este es el único documento que la empresa verá en su portal (Res. 1843/2025).
            No incluye contenido de la historia clínica.
          </p>
          {concepto.id && atencion && (
            <button
              onClick={() => imprimirConcepto({
                trabajador_nombre: atencion.trabajador_nombre,
                trabajador_documento: atencion.trabajador_documento,
                empresa_nombre: atencion.empresa_nombre,
                tipo_examen: atencion.tipo_examen,
                aptitud: concepto.aptitud ?? "apto",
                restricciones: concepto.restricciones,
                recomendaciones_laborales: concepto.recomendaciones_laborales,
                firmado: concepto.firmado,
                fecha_emision: concepto.fecha_emision,
                profesional_nombre: medicoNombre,
              })}
              className="mb-4 rounded-lg bg-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 transition hover:bg-gray-300"
            >
              🖨 Imprimir concepto (PDF)
            </button>
          )}

          {!concepto.firmado && (
            <button
              onClick={async () => {
                try {
                  const s = await apiFetch<{ aptitud: string; restricciones: string; recomendaciones_laborales: string }>(
                    `/atenciones/${atencionId}/sugerir_concepto/`,
                  );
                  setConcepto((c) => ({
                    ...c,
                    aptitud: s.aptitud,
                    restricciones: s.restricciones || c.restricciones,
                    recomendaciones_laborales: s.recomendaciones_laborales || c.recomendaciones_laborales,
                  }));
                  setMsg({ tipo: "ok", texto: "Concepto sugerido a partir de diagnósticos y pruebas. Revísalo antes de firmar." });
                } catch (e) {
                  setMsg({ tipo: "error", texto: (e as Error).message });
                }
              }}
              className="mb-3 rounded-lg bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700 transition hover:bg-violet-100"
            >
              ✨ Sugerir aptitud (según hallazgos)
            </button>
          )}

          <label className={labelCls}>
            Concepto de aptitud
            <select
              className={areaCls}
              value={concepto.aptitud ?? "apto"}
              disabled={concepto.firmado}
              onChange={(e) => setConcepto((c) => ({ ...c, aptitud: e.target.value }))}
            >
              {APTITUDES.map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>
          <label className={`${labelCls} mt-3`}>
            Restricciones
            <textarea rows={3} className={areaCls} disabled={concepto.firmado}
              value={concepto.restricciones ?? ""}
              onChange={(e) => setConcepto((c) => ({ ...c, restricciones: e.target.value }))} />
          </label>
          <label className={`${labelCls} mt-3`}>
            Recomendaciones laborales
            <textarea rows={3} className={areaCls} disabled={concepto.firmado}
              value={concepto.recomendaciones_laborales ?? ""}
              onChange={(e) => setConcepto((c) => ({ ...c, recomendaciones_laborales: e.target.value }))} />
          </label>

          {!concepto.firmado && (
            <div className="mt-4 flex gap-3">
              <button onClick={guardarConcepto} disabled={guardando}
                className="rounded-lg bg-gray-200 px-5 py-2 text-sm font-semibold text-gray-900 transition hover:bg-gray-300 disabled:opacity-50">
                Guardar borrador
              </button>
              <button onClick={firmar} disabled={guardando || !concepto.id}
                title={!concepto.id ? "Guarda el borrador primero" : "Requiere licencia SST vigente"}
                className="rounded-lg bg-emerald-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-400 disabled:opacity-50">
                ✍️ Firmar concepto
              </button>
            </div>
          )}
        </section>
      </div>

      {/* --------- Módulo del médico: circuito, diagnósticos, órdenes y recetas --------- */}
      <div className="mt-6 space-y-6">
        <PruebasSection atencionId={atencionId} />
        <DiagnosticosSection atencionId={atencionId} historiaId={historia.id} />
        <div className="grid gap-6 xl:grid-cols-2">
          <OrdenesSection atencionId={atencionId} encabezado={encabezado} />
          <RecetasSection atencionId={atencionId} encabezado={encabezado} />
        </div>
      </div>
    </AppShell>
  );
}
