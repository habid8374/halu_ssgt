import Link from "next/link";

const rutas = [
  { href: "/recepcion", label: "Recepción — Tablero de flujo" },
  { href: "/consultorio/1", label: "Consultorio (médico)" },
  { href: "/gerencia", label: "Gerencia — Reportes" },
  { href: "/portal-empresa", label: "Portal empresa cliente" },
  { href: "/pantalla/1", label: "Pantalla pública (sede)" },
];

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-bold">Halu Salud Ocupacional</h1>
      <p className="mt-2 text-sm text-gray-500">
        Fase 1 — núcleo operativo. Rutas segregadas por rol (App Router).
      </p>
      <ul className="mt-6 space-y-2">
        {rutas.map((r) => (
          <li key={r.href}>
            <Link className="text-blue-600 underline" href={r.href}>
              {r.label}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
