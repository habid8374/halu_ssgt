"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export interface ItemCatalogo {
  codigo: string;
  nombre: string;
}

const norm = (s: string) =>
  s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

const inputCls =
  "mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-teal-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500";

/**
 * Combobox con búsqueda: el usuario escribe para filtrar y selecciona de la
 * lista (por código o por nombre). No permite texto libre — el valor siempre
 * corresponde a un ítem del catálogo. Muestra «código · nombre».
 */
export default function Combobox({
  items,
  value,
  onSelect,
  placeholder = "Buscar…",
  disabled = false,
  mostrarCodigo = true,
}: {
  items: ItemCatalogo[];
  value: string; // código seleccionado ("" = ninguno)
  onSelect: (item: ItemCatalogo | null) => void;
  placeholder?: string;
  disabled?: boolean;
  mostrarCodigo?: boolean;
}) {
  const [abierto, setAbierto] = useState(false);
  const [query, setQuery] = useState("");
  const cajaRef = useRef<HTMLDivElement>(null);

  const etiqueta = (i: ItemCatalogo) =>
    mostrarCodigo ? `${i.codigo} · ${i.nombre}` : i.nombre;

  const seleccionado = useMemo(
    () => items.find((i) => i.codigo === value) ?? null,
    [items, value],
  );

  // Sincroniza el texto visible cuando cambia el valor desde afuera.
  useEffect(() => {
    if (!abierto) setQuery(seleccionado ? etiqueta(seleccionado) : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seleccionado, abierto]);

  // Cierra al hacer clic fuera.
  useEffect(() => {
    function fuera(e: MouseEvent) {
      if (cajaRef.current && !cajaRef.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, []);

  const filtrados = useMemo(() => {
    const q = norm(query.trim());
    const base = !q || (seleccionado && query === etiqueta(seleccionado))
      ? items
      : items.filter((i) => norm(i.nombre).includes(q) || i.codigo.startsWith(q));
    return base.slice(0, 60);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, query, seleccionado]);

  return (
    <div ref={cajaRef} className="relative">
      <input
        value={query}
        disabled={disabled}
        placeholder={placeholder}
        onFocus={() => {
          setAbierto(true);
          setQuery("");
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setAbierto(true);
        }}
        className={inputCls}
        autoComplete="off"
      />
      {abierto && !disabled && (
        <ul className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          {filtrados.length === 0 && (
            <li className="px-3 py-2 text-sm text-gray-400">Sin resultados</li>
          )}
          {filtrados.map((i) => (
            <li key={i.codigo}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onSelect(i);
                  setQuery(etiqueta(i));
                  setAbierto(false);
                }}
                className={`flex w-full items-baseline gap-2 px-3 py-1.5 text-left text-sm hover:bg-teal-50 ${
                  i.codigo === value ? "bg-teal-50 font-semibold text-teal-700" : "text-gray-700"
                }`}
              >
                {mostrarCodigo && (
                  <span className="min-w-[3.2rem] shrink-0 font-mono text-xs text-gray-400">
                    {i.codigo}
                  </span>
                )}
                <span>{i.nombre}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
