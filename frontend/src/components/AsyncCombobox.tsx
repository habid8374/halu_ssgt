"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ItemCatalogo } from "./Combobox";

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none disabled:bg-gray-100";

/**
 * Combobox con búsqueda en el servidor (para catálogos grandes que viven en la
 * base de datos, p. ej. CUPS). Consulta `buscar(q)` con debounce mientras se
 * escribe; el valor siempre corresponde a un ítem del catálogo.
 */
export default function AsyncCombobox({
  buscar,
  seligido,
  onSelect,
  placeholder = "Buscar…",
  disabled = false,
}: {
  buscar: (q: string) => Promise<ItemCatalogo[]>;
  seligido: ItemCatalogo | null;
  onSelect: (item: ItemCatalogo | null) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [abierto, setAbierto] = useState(false);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<ItemCatalogo[]>([]);
  const [cargando, setCargando] = useState(false);
  const cajaRef = useRef<HTMLDivElement>(null);

  const etiqueta = (i: ItemCatalogo) => `${i.codigo} · ${i.nombre}`;

  // Texto visible cuando no se está editando.
  useEffect(() => {
    if (!abierto) setQuery(seligido ? etiqueta(seligido) : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seligido, abierto]);

  // Cierra al hacer clic fuera.
  useEffect(() => {
    function fuera(e: MouseEvent) {
      if (cajaRef.current && !cajaRef.current.contains(e.target as Node)) setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, []);

  // Búsqueda con debounce cuando el combo está abierto.
  const q = abierto ? query : "";
  useEffect(() => {
    if (!abierto) return;
    let vivo = true;
    setCargando(true);
    const t = setTimeout(() => {
      void buscar(q).then((res) => { if (vivo) { setItems(res); setCargando(false); } })
        .catch(() => { if (vivo) setCargando(false); });
    }, 250);
    return () => { vivo = false; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, abierto]);

  const lista = useMemo(() => items.slice(0, 50), [items]);

  return (
    <div ref={cajaRef} className="relative">
      <input
        value={query}
        disabled={disabled}
        placeholder={placeholder}
        onFocus={() => { setAbierto(true); setQuery(""); }}
        onChange={(e) => { setQuery(e.target.value); setAbierto(true); }}
        className={inputCls}
        autoComplete="off"
      />
      {abierto && !disabled && (
        <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          {cargando && <li className="px-3 py-2 text-sm text-gray-400">Buscando…</li>}
          {!cargando && lista.length === 0 && (
            <li className="px-3 py-2 text-sm text-gray-400">Sin resultados</li>
          )}
          {!cargando && lista.map((i) => (
            <li key={i.codigo}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => { onSelect(i); setQuery(etiqueta(i)); setAbierto(false); }}
                className="flex w-full items-baseline gap-2 px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-teal-50"
              >
                <span className="min-w-[3.8rem] shrink-0 font-mono text-xs text-gray-400">{i.codigo}</span>
                <span>{i.nombre}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
