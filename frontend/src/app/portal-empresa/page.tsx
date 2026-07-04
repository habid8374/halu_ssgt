/**
 * Portal de la empresa cliente (externo).
 * Rol `empresa_cliente`: consulta ÚNICAMENTE conceptos de aptitud de SUS
 * trabajadores. NUNCA historia clínica (Res. 1843/2025 — CLAUDE.md regla 1).
 * Esta restricción se aplica en el backend (permisos DRF por objeto), no solo aquí.
 */
export default function PortalEmpresaPage() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-bold">Portal empresa cliente</h1>
      <p className="mt-2 text-sm text-gray-500">
        Conceptos de aptitud de sus trabajadores. Sin acceso a historia clínica.
      </p>
    </main>
  );
}
