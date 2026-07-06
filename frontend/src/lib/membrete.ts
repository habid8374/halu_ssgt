import { apiFetch } from "@/lib/api";
import type { Membrete } from "@/lib/imprimir";

// Membrete de la IPS (razón social, NIT, habilitación, logo…) para los
// documentos. Se carga una vez y se cachea; si falla, se imprime sin membrete.
let cache: Membrete | null = null;

export async function cargarMembrete(): Promise<Membrete | undefined> {
  if (cache) return cache;
  try {
    cache = await apiFetch<Membrete>("/configuracion/");
    return cache;
  } catch {
    return undefined;
  }
}

export function invalidarMembrete() {
  cache = null;
}

export type { Membrete };
