/**
 * Consultorio del médico ocupacional.
 * Rol `medico`: ve la historia clínica SOLO de sus pacientes asignados y
 * emite el concepto de aptitud. La carga de datos y el editor de historia
 * clínica se implementan tras aprobar los modelos.
 */
export default function ConsultorioPage({
  params,
}: {
  params: { id: string };
}) {
  return (
    <main className="p-6">
      <h1 className="text-xl font-bold">Consultorio — Atención #{params.id}</h1>
      <p className="mt-2 text-sm text-gray-500">
        Historia clínica ocupacional (reservada) y concepto de aptitud.
      </p>
    </main>
  );
}
