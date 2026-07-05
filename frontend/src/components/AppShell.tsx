"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSesion, logout, type Yo } from "@/lib/api";

const ROL_LABEL: Record<string, string> = {
  recepcion: "Recepción",
  medico: "Médico ocupacional",
  psicologo_sst: "Psicólogo SST",
  coordinador: "Coordinación",
  empresa_cliente: "Empresa cliente",
  admin_sistema: "Administración",
};

interface ItemNav {
  href: string;
  label: string;
  icono: string;
  deshabilitado?: boolean;
}

/**
 * Navegación por rol (matriz §4). Los usuarios NUNCA navegan escribiendo
 * URLs: todo se alcanza desde este sidebar. Los ítems "Próximamente"
 * marcan módulos de la fase en curso aún no construidos.
 */
const NAV_POR_ROL: Record<string, ItemNav[]> = {
  recepcion: [
    { href: "/recepcion", label: "Tablero de flujo", icono: "🗂️" },
    { href: "/recepcion/admision", label: "Admisión", icono: "📝" },
    { href: "/recepcion/agenda", label: "Agenda", icono: "📅" },
  ],
  medico: [
    { href: "/consultorio/mi-cola", label: "Mi cola de atención", icono: "🩺" },
    { href: "#historias", label: "Historias clínicas", icono: "📋", deshabilitado: true },
  ],
  coordinador: [
    { href: "/gerencia", label: "Tablero de sedes", icono: "🏥" },
    { href: "#reportes", label: "Reportes", icono: "📊", deshabilitado: true },
  ],
  empresa_cliente: [
    { href: "/portal-empresa", label: "Conceptos de aptitud", icono: "📄" },
  ],
};

export default function AppShell({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [yo, setYo] = useState<Yo | null>(null);

  useEffect(() => {
    if (!getSesion()) {
      router.replace("/login");
      return;
    }
    const raw = localStorage.getItem("halu_yo");
    if (raw) setYo(JSON.parse(raw) as Yo);
  }, [router]);

  const nav = yo ? (NAV_POR_ROL[yo.rol] ?? []) : [];

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* ------------------------------- Sidebar ------------------------------ */}
      <aside className="fixed inset-y-0 left-0 z-20 flex w-60 flex-col border-r border-slate-800 bg-slate-900">
        <div className="flex items-center gap-2.5 border-b border-slate-800 px-4 py-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-teal-500/15 text-lg">
            🩺
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold leading-tight text-white">
              Halu Salud Ocupacional
            </p>
            <p className="truncate text-[11px] leading-tight text-slate-500">
              Sistema para IPS
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {nav.map((item) =>
            item.deshabilitado ? (
              <span
                key={item.href}
                title="Disponible próximamente"
                className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-600"
              >
                <span className="text-base opacity-50">{item.icono}</span>
                {item.label}
                <span className="ml-auto rounded bg-slate-800 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-slate-500">
                  Pronto
                </span>
              </span>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  pathname === item.href
                    ? "bg-teal-500/15 text-teal-300"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <span className="text-base">{item.icono}</span>
                {item.label}
              </Link>
            ),
          )}
        </nav>

        <div className="border-t border-slate-800 p-3">
          {yo && (
            <div className="mb-2 rounded-lg bg-slate-950/60 px-3 py-2.5">
              <p className="truncate text-sm font-semibold text-white">{yo.nombre_completo}</p>
              <p className="truncate text-xs text-teal-400">{ROL_LABEL[yo.rol] ?? yo.rol}</p>
            </div>
          )}
          <button
            onClick={logout}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-red-500/50 hover:text-red-400"
          >
            ⏻ Cerrar sesión
          </button>
        </div>
      </aside>

      {/* ------------------------------ Contenido ----------------------------- */}
      <div className="ml-60 flex-1">
        <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/90 px-6 py-4 backdrop-blur">
          <h1 className="text-lg font-bold text-white">{titulo}</h1>
        </header>
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
