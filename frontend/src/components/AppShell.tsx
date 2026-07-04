"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSesion, setSesion, type Yo } from "@/lib/api";

const ROL_LABEL: Record<string, string> = {
  recepcion: "Recepción",
  medico: "Médico ocupacional",
  psicologo_sst: "Psicólogo SST",
  coordinador: "Coordinación",
  empresa_cliente: "Empresa cliente",
  admin_sistema: "Administración",
};

/** Marco autenticado: barra superior con identidad, rol y salida. */
export default function AppShell({
  titulo,
  children,
}: {
  titulo: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [yo, setYo] = useState<Yo | null>(null);

  useEffect(() => {
    if (!getSesion()) {
      router.replace("/login");
      return;
    }
    const raw = localStorage.getItem("halu_yo");
    if (raw) setYo(JSON.parse(raw) as Yo);
  }, [router]);

  function salir() {
    setSesion(null);
    localStorage.removeItem("halu_yo");
    router.replace("/login");
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-500/15 text-lg">
              🩺
            </span>
            <div>
              <p className="text-sm font-bold leading-tight text-white">Halu Salud Ocupacional</p>
              <p className="text-xs leading-tight text-slate-400">{titulo}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {yo && (
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium leading-tight text-white">{yo.nombre_completo}</p>
                <p className="text-xs leading-tight text-teal-400">{ROL_LABEL[yo.rol] ?? yo.rol}</p>
              </div>
            )}
            <button
              onClick={salir}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
            >
              Salir
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1600px] px-4 py-6">{children}</main>
    </div>
  );
}
