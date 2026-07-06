/**
 * Impresión de documentos clínicos (órdenes, recetas). Abre una ventana con
 * un formato limpio y lanza el diálogo de impresión del navegador — sin
 * dependencias externas y sin exigir comandos al usuario.
 */
export interface Membrete {
  razon_social: string;
  nit: string;
  codigo_habilitacion: string;
  direccion: string;
  ciudad: string;
  telefono: string;
  email: string;
  logo_data_uri: string;
}

export interface EncabezadoImpresion {
  ips: string;
  paciente: string;
  documento?: string;
  empresa?: string;
  profesional?: string;
  fecha?: string;
  membrete?: Membrete;
}

function membreteHtml(enc: EncabezadoImpresion): string {
  const m = enc.membrete;
  if (!m || !m.razon_social) {
    return `<h1>${esc(enc.ips)}</h1>`;
  }
  const linea2 = [m.nit ? `NIT ${esc(m.nit)}` : "", m.codigo_habilitacion ? `Habilitación ${esc(m.codigo_habilitacion)}` : ""]
    .filter(Boolean).join(" · ");
  const linea3 = [m.direccion, m.ciudad, m.telefono, m.email].filter(Boolean).map(esc).join(" · ");
  const logo = m.logo_data_uri
    ? `<img src="${m.logo_data_uri}" alt="" style="height:56px;width:auto;object-fit:contain" />`
    : "";
  return `<div style="display:flex;align-items:center;gap:14px;border-bottom:2px solid #0f766e;padding-bottom:10px">
    ${logo}
    <div>
      <h1 style="margin:0">${esc(m.razon_social)}</h1>
      ${linea2 ? `<div class="ips">${linea2}</div>` : ""}
      ${linea3 ? `<div class="ips">${linea3}</div>` : ""}
    </div>
  </div>`;
}

export function imprimirDocumento(
  titulo: string,
  enc: EncabezadoImpresion,
  cuerpoHtml: string,
) {
  const fecha = enc.fecha ?? new Date().toLocaleDateString("es-CO");
  const win = window.open("", "_blank", "width=820,height=1000");
  if (!win) return;
  win.document.write(`<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>${titulo}</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, Arial, sans-serif; color: #111; margin: 32px; }
  h1 { font-size: 18px; margin: 0 0 2px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em; color: #0f766e; margin: 22px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  .ips { font-size: 12px; color: #555; }
  .datos { margin-top: 14px; font-size: 13px; display: grid; grid-template-columns: 1fr 1fr; gap: 2px 20px; }
  .datos b { color: #444; }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; margin-top: 6px; }
  th, td { text-align: left; border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }
  th { background: #f3f4f6; }
  .item { margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px dashed #ddd; font-size: 13px; }
  .firma { margin-top: 60px; font-size: 13px; }
  .firma div { border-top: 1px solid #333; width: 260px; padding-top: 4px; }
  @media print { body { margin: 12mm; } }
</style></head><body>
${membreteHtml(enc)}
<div class="ips" style="margin-top:6px">${titulo}</div>
<div class="datos">
  <span><b>Paciente:</b> ${enc.paciente}</span>
  ${enc.documento ? `<span><b>Documento:</b> ${enc.documento}</span>` : ""}
  ${enc.empresa ? `<span><b>Empresa:</b> ${enc.empresa}</span>` : ""}
  <span><b>Fecha:</b> ${fecha}</span>
</div>
${cuerpoHtml}
<div class="firma"><div>${enc.profesional ?? ""}<br><span style="font-size:11px;color:#666">Firma del profesional</span></div></div>
</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 350);
}

export function esc(s: string): string {
  return (s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string),
  );
}
