import { apiFetch, TIPO_EXAMEN_LABEL, type Atencion } from "@/lib/api";
import { imprimirDocumento, esc, type EncabezadoImpresion } from "@/lib/imprimir";

/**
 * Compone e imprime la HISTORIA CLÍNICA COMPLETA de una atención (historia +
 * signos vitales + diagnósticos + órdenes + recetas + concepto). El navegador
 * permite "Guardar como PDF" desde el diálogo de impresión — sin dependencias.
 */

const APTITUD: Record<string, string> = {
  apto: "Apto",
  apto_restricciones: "Apto con restricciones",
  no_apto: "No apto",
  aplazado: "Aplazado",
};
const TIPO_ORDEN: Record<string, string> = {
  laboratorio: "Laboratorio", imagen: "Imagen diagnóstica", paraclinico: "Paraclínico",
  procedimiento: "Procedimiento", interconsulta: "Interconsulta/remisión",
  incapacidad: "Incapacidad", otro: "Otra orden",
};

function bloque(titulo: string, texto: string): string {
  if (!texto || !texto.trim()) return "";
  return `<h2>${titulo}</h2><div class="item">${esc(texto).replace(/\n/g, "<br>")}</div>`;
}

export async function imprimirHistoriaCompleta(atencion: Atencion, medicoNombre: string) {
  const id = atencion.id;
  const [historias, diagnosticos, ordenes, recetas, conceptos] = await Promise.all([
    apiFetch<Record<string, string>[]>(`/historias/?atencion=${id}`),
    apiFetch<Record<string, string>[]>(`/diagnosticos/?atencion=${id}`),
    apiFetch<Record<string, string | number>[]>(`/ordenes/?atencion=${id}`),
    apiFetch<Array<{ medicamentos: Record<string, string>[]; observaciones: string }>>(`/recetas/?atencion=${id}`),
    apiFetch<Record<string, string>[]>(`/conceptos/?atencion=${id}`),
  ]);

  const h = historias[0];
  const enc: EncabezadoImpresion = {
    ips: typeof window !== "undefined" ? window.location.hostname : "IPS",
    paciente: atencion.trabajador_nombre,
    documento: atencion.trabajador_documento,
    empresa: atencion.empresa_nombre,
    profesional: medicoNombre,
  };

  let cuerpo = `<h2>Atención</h2><div class="item">
    Tipo de examen: <b>${esc(TIPO_EXAMEN_LABEL[atencion.tipo_examen] ?? atencion.tipo_examen)}</b> ·
    Estado: ${esc(atencion.estado)} ·
    Fecha: ${new Date(atencion.created_at).toLocaleDateString("es-CO")}
  </div>`;

  if (h) {
    // Signos vitales
    const vitales: Array<[string, string]> = [
      ["Peso", h.peso_kg], ["Talla", h.talla_cm], ["T/A", h.presion_arterial],
      ["FC", h.frecuencia_cardiaca], ["FR", h.frecuencia_respiratoria],
      ["Temp", h.temperatura], ["SatO₂", h.saturacion_o2],
    ];
    const v = vitales.filter(([, val]) => val && String(val).trim());
    if (v.length) {
      cuerpo += `<h2>Signos vitales</h2><table><tbody><tr>${
        v.map(([k, val]) => `<td><b>${k}</b><br>${esc(String(val))}</td>`).join("")
      }</tr></tbody></table>`;
    }
    cuerpo += bloque("Motivo de consulta", h.motivo_consulta);
    cuerpo += bloque("Antecedentes personales/familiares", h.antecedentes);
    cuerpo += bloque("Antecedentes laborales", h.antecedentes_laborales);
    cuerpo += bloque("Revisión por sistemas", h.revision_sistemas);
    cuerpo += bloque("Examen físico", h.examen_fisico);
  }

  if (diagnosticos.length) {
    cuerpo += `<h2>Diagnósticos (CIE-10 / CIE-11)</h2><table>
      <thead><tr><th>CIE-10</th><th>Descripción</th><th>CIE-11</th><th>Relación</th></tr></thead><tbody>${
      diagnosticos.map((d) => `<tr>
        <td>${esc(String(d.cie10_codigo))}</td><td>${esc(String(d.cie10_desc))}</td>
        <td>${esc(String(d.cie11_codigo ?? ""))}</td>
        <td>${d.relacion === "principal" ? "Principal" : "Relacionado"}</td></tr>`).join("")
    }</tbody></table>`;
  }

  if (h) {
    cuerpo += bloque("Análisis", h.analisis);
    cuerpo += bloque("Plan de manejo", h.plan_manejo);
    cuerpo += bloque("Recomendaciones", h.recomendaciones);
  }

  if (ordenes.length) {
    cuerpo += `<h2>Órdenes médicas</h2>${
      ordenes.map((o) => `<div class="item"><b>${esc(TIPO_ORDEN[String(o.tipo)] ?? String(o.tipo))}</b>: ${esc(String(o.descripcion))} (x${o.cantidad})${
        o.codigo_cups ? ` · CUPS ${esc(String(o.codigo_cups))}` : ""}${
        o.indicaciones ? `<br>${esc(String(o.indicaciones))}` : ""}</div>`).join("")
    }`;
  }

  const recetasConMeds = recetas.filter((r) => r.medicamentos.length);
  if (recetasConMeds.length) {
    cuerpo += `<h2>Fórmula médica</h2>`;
    for (const r of recetasConMeds) {
      cuerpo += `<table><thead><tr><th>Medicamento</th><th>Posología</th></tr></thead><tbody>${
        r.medicamentos.map((m) => `<tr>
          <td><b>${esc(m.medicamento)}</b> ${esc(m.concentracion ?? "")} ${esc(m.forma_farmaceutica ?? "")}</td>
          <td>${esc(m.dosis ?? "")} ${esc(m.via ?? "")} ${esc(m.frecuencia ?? "")} ${esc(m.duracion ?? "")} ${esc(m.cantidad ?? "")}</td></tr>`).join("")
      }</tbody></table>${r.observaciones ? `<div class="item">${esc(r.observaciones)}</div>` : ""}`;
    }
  }

  const c = conceptos[0];
  if (c) {
    cuerpo += `<h2>Concepto de aptitud</h2><div class="item">
      Concepto: <b>${esc(APTITUD[String(c.aptitud)] ?? String(c.aptitud))}</b>
      ${c.firmado ? `· FIRMADO ${esc(String(c.fecha_emision ?? ""))}` : "· (borrador)"}
      ${c.restricciones ? `<br><b>Restricciones:</b> ${esc(String(c.restricciones))}` : ""}
      ${c.recomendaciones_laborales ? `<br><b>Recomendaciones laborales:</b> ${esc(String(c.recomendaciones_laborales))}` : ""}
    </div>`;
  }

  imprimirDocumento("Historia clínica ocupacional", enc, cuerpo);
}
