/**
 * Impresión de documentos clínicos (órdenes, recetas). Abre una ventana con
 * un formato limpio y lanza el diálogo de impresión del navegador — sin
 * dependencias externas y sin exigir comandos al usuario.
 */
export interface EncabezadoImpresion {
  ips: string;
  paciente: string;
  documento?: string;
  empresa?: string;
  profesional?: string;
  fecha?: string;
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
<h1>${enc.ips}</h1>
<div class="ips">${titulo}</div>
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
