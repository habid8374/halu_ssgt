import type { ItemCatalogo } from "@/components/Combobox";

// Catálogos clínicos servidos como estáticos (public/). Se cargan una sola vez
// y se cachean en memoria (el CIE-10 es grande: se pide solo cuando se usa).
const cache: Record<string, ItemCatalogo[]> = {};

async function cargar(url: string, clave: string): Promise<ItemCatalogo[]> {
  if (cache[clave]) return cache[clave];
  const r = await fetch(url);
  const d = (await r.json()) as { diagnosticos?: ItemCatalogo[]; ocupaciones?: ItemCatalogo[] };
  cache[clave] = d.diagnosticos ?? d.ocupaciones ?? [];
  return cache[clave];
}

export const cargarCie10 = () => cargar("/cie10.json", "cie10");
export const cargarCie11 = () => cargar("/cie11.json", "cie11");
