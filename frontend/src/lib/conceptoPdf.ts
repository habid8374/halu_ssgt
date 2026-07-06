import { TIPO_EXAMEN_LABEL } from "@/lib/api";
import { imprimirDocumento, esc, type EncabezadoImpresion } from "@/lib/imprimir";

/**
 * Certificado de aptitud médico ocupacional en formato oficial, para entregar
 * a la empresa (Res. 1843/2025: es el ÚNICO documento que ve el empleador; no
 * contiene información clínica reservada). Imprime / "Guardar como PDF".
 */

export interface ConceptoImprimible {
  trabajador_nombre: string;
  trabajador_documento?: string;
  empresa_nombre?: string;
  tipo_examen?: string;
  aptitud: string;
  restricciones?: string;
  recomendaciones_laborales?: string;
  firmado?: boolean;
  fecha_emision?: string | null;
  vigencia_hasta?: string | null;
  profesional_nombre?: string;
}

const APTITUD: Record<string, string> = {
  apto: "APTO",
  apto_restricciones: "APTO CON RESTRICCIONES / RECOMENDACIONES",
  no_apto: "NO APTO",
  aplazado: "APLAZADO",
};
const COLOR: Record<string, string> = {
  apto: "#059669", apto_restricciones: "#b45309", no_apto: "#dc2626", aplazado: "#6b7280",
};

export function imprimirConcepto(c: ConceptoImprimible) {
  const enc: EncabezadoImpresion = {
    ips: typeof window !== "undefined" ? window.location.hostname : "IPS",
    paciente: c.trabajador_nombre,
    documento: c.trabajador_documento,
    empresa: c.empresa_nombre,
    profesional: c.profesional_nombre,
    fecha: c.fecha_emision ?? new Date().toLocaleDateString("es-CO"),
  };
  const color = COLOR[c.aptitud] ?? "#111";

  let cuerpo = `<h2>Certificado de aptitud médico ocupacional</h2>`;
  if (c.tipo_examen) {
    cuerpo += `<div class="item">Tipo de evaluación: <b>${esc(TIPO_EXAMEN_LABEL[c.tipo_examen] ?? c.tipo_examen)}</b></div>`;
  }
  cuerpo += `<div style="margin:18px 0;padding:16px;border:2px solid ${color};border-radius:8px;text-align:center">
    <div style="font-size:12px;letter-spacing:.15em;color:#666">CONCEPTO DE APTITUD</div>
    <div style="font-size:22px;font-weight:800;color:${color};margin-top:4px">${esc(APTITUD[c.aptitud] ?? c.aptitud)}</div>
  </div>`;

  if (c.restricciones && c.restricciones.trim()) {
    cuerpo += `<h2>Restricciones</h2><div class="item">${esc(c.restricciones).replace(/\n/g, "<br>")}</div>`;
  }
  if (c.recomendaciones_laborales && c.recomendaciones_laborales.trim()) {
    cuerpo += `<h2>Recomendaciones laborales</h2><div class="item">${esc(c.recomendaciones_laborales).replace(/\n/g, "<br>")}</div>`;
  }
  if (c.vigencia_hasta) {
    cuerpo += `<div class="item">Vigencia hasta: <b>${esc(c.vigencia_hasta)}</b></div>`;
  }
  if (!c.firmado) {
    cuerpo += `<div class="item" style="color:#b45309">Documento en BORRADOR (sin firma).</div>`;
  }
  cuerpo += `<div class="item" style="font-size:11px;color:#666;margin-top:16px">
    De acuerdo con la Resolución 1843 de 2025, este certificado no contiene información
    clínica reservada. La historia clínica ocupacional es de custodia exclusiva del
    profesional de la salud.
  </div>`;

  imprimirDocumento("Certificado de aptitud médico ocupacional", enc, cuerpo);
}
