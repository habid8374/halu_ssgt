/**
 * Reportes gerenciales (Server Component — carga pesada del lado servidor).
 * Rol `coordinador`: tablero de todas las sedes y reportes agregados; NO ve
 * historia clínica (salvo excepción legal auditada).
 */
export default function GerenciaPage() {
  return (
    <main className="p-6">
      <h1 className="text-xl font-bold">Gerencia — Reportes agregados</h1>
      <p className="mt-2 text-sm text-gray-500">
        Indicadores de tiempos de atención y cumplimiento SG-SST (fase posterior).
      </p>
    </main>
  );
}
