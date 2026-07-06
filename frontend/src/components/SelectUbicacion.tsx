"use client";

import { useEffect, useMemo, useState } from "react";
import Combobox, { type ItemCatalogo } from "./Combobox";

interface Departamento {
  codigo: string;
  nombre: string;
  municipios: ItemCatalogo[];
}

const norm = (s: string) =>
  s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();

const labelCls = "block text-xs font-medium uppercase tracking-wide text-gray-500";

// Catálogo DANE DIVIPOLA cargado una sola vez y compartido entre instancias.
let cache: Departamento[] | null = null;

/**
 * Selección en cascada Departamento → Municipio con códigos DANE (DIVIPOLA).
 * Guarda el nombre del departamento, el nombre del municipio y el código DANE
 * de 5 dígitos del municipio (para RIPS/RDA). El usuario solo consulta y elige.
 */
export default function SelectUbicacion({
  departamento,
  municipioDane,
  onChange,
  disabled = false,
}: {
  departamento: string; // nombre del departamento
  municipioDane: string; // código DANE de 5 dígitos del municipio
  onChange: (v: { departamento: string; municipio: string; municipio_dane: string }) => void;
  disabled?: boolean;
}) {
  const [deptos, setDeptos] = useState<Departamento[]>(cache ?? []);

  useEffect(() => {
    if (cache) return;
    void fetch("/divipola.json")
      .then((r) => r.json())
      .then((d: { departamentos: Departamento[] }) => {
        cache = d.departamentos;
        setDeptos(cache);
      });
  }, []);

  // El departamento seleccionado se deriva del código DANE del municipio
  // (2 primeros dígitos) o, si aún no hay municipio, del nombre guardado.
  const deptoSel = useMemo(() => {
    if (municipioDane) return deptos.find((d) => d.codigo === municipioDane.slice(0, 2)) ?? null;
    if (departamento) return deptos.find((d) => norm(d.nombre) === norm(departamento)) ?? null;
    return null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deptos, departamento, municipioDane]);

  const municipios = deptoSel?.municipios ?? [];

  return (
    <>
      <label className={labelCls}>
        Departamento
        <div className="mt-1">
          <Combobox
            items={deptos}
            value={deptoSel?.codigo ?? ""}
            disabled={disabled}
            placeholder="Departamento…"
            onSelect={(d) =>
              onChange({ departamento: d?.nombre ?? "", municipio: "", municipio_dane: "" })
            }
          />
        </div>
      </label>
      <label className={labelCls}>
        Municipio
        <div className="mt-1">
          <Combobox
            items={municipios}
            value={municipioDane}
            disabled={disabled || !deptoSel}
            placeholder={deptoSel ? "Municipio…" : "Elija departamento primero"}
            onSelect={(m) =>
              onChange({
                departamento: deptoSel?.nombre ?? departamento,
                municipio: m?.nombre ?? "",
                municipio_dane: m?.codigo ?? "",
              })
            }
          />
        </div>
      </label>
    </>
  );
}
