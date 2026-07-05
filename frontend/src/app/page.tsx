"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getSesion } from "@/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Sin sesión → login. Con sesión → cada quien entra por su ruta de rol.
    if (!getSesion()) router.replace("/login");
  }, [router]);

  const rutas = [
    { href: "/recepcion", label: "Recepción", desc: "Tablero de flujo en tiempo real", icono: "🗂️" },
    { href: "/consultorio/1", label: "Consultorio", desc: "Cola del médico ocupacional", icono: "🩺" },
    { href: "/gerencia", label: "Gerencia", desc: "Tablero multi-sede (solo lectura)", icono: "📊" },
    { href: "/portal-empresa", label: "Portal empresa", desc: "Conceptos de aptitud", icono: "🏢" },
    { href: "/pantalla/1", label: "Pantalla pública", desc: "TV de sala de espera", icono: "📺" },
  ];

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="mb-8 flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-2xl">🩺</span>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Halu Salud Ocupacional</h1>
          <p className="text-sm text-gray-500">Fase 1 — núcleo operativo</p>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {rutas.map((r) => (
          <Link
            key={r.href}
            href={r.href}
            className="rounded-xl border border-gray-200 bg-white p-4 transition hover:border-teal-500/50"
          >
            <span className="text-2xl">{r.icono}</span>
            <p className="mt-2 font-semibold text-gray-900">{r.label}</p>
            <p className="text-xs text-gray-500">{r.desc}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
