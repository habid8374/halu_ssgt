"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { apiFetch } from "@/lib/api";

interface Item { id: number; descripcion: string; valor: string }
interface Factura {
  id: number; numero: string; estado: string; total: string;
  periodo_desde: string; periodo_hasta: string; items: Item[];
}

/** Facturas de la empresa cliente (solo emitidas/pagadas, solo las suyas). */
export default function FacturasEmpresaPage() {
  const [facturas, setFacturas] = useState<Factura[] | null>(null);

  useEffect(() => {
    apiFetch<Factura[]>("/facturas/").then(setFacturas).catch(() => setFacturas([]));
  }, []);

  return (
    <AppShell titulo="Facturación — Mis facturas">
      {facturas === null ? (
        <p className="text-sm text-gray-500">Cargando…</p>
      ) : facturas.length === 0 ? (
        <p className="text-sm text-gray-500">Aún no hay facturas emitidas.</p>
      ) : (
        <div className="space-y-3">
          {facturas.map((f) => (
            <article key={f.id} className="rounded-xl border border-gray-200 bg-white p-4">
              <div className="flex flex-wrap items-center gap-3">
                <p className="flex-1 text-sm font-bold text-gray-900">{f.numero}</p>
                <p className="text-xs text-gray-500">{f.periodo_desde} → {f.periodo_hasta}</p>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                  f.estado === "pagada" ? "bg-emerald-50 text-emerald-600" : "bg-blue-50 text-blue-700"
                }`}>
                  {f.estado}
                </span>
                <p className="text-base font-bold text-gray-900">
                  ${Number(f.total).toLocaleString("es-CO")}
                </p>
              </div>
              <ul className="mt-3 divide-y divide-gray-100 border-t border-gray-100 pt-2">
                {f.items.map((i) => (
                  <li key={i.id} className="flex justify-between py-1.5 text-xs text-gray-600">
                    <span>{i.descripcion}</span>
                    <span>${Number(i.valor).toLocaleString("es-CO")}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}
    </AppShell>
  );
}
