const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

// --- Sesión (JWT en localStorage; solo cliente) ----------------------------
export interface Sesion {
  access: string;
  refresh: string;
}

export interface Yo {
  id: number;
  email: string;
  nombre_completo: string;
  rol: string;
  sede: number | null;
  empresa: number | null;
}

export function getSesion(): Sesion | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("halu_sesion");
  return raw ? (JSON.parse(raw) as Sesion) : null;
}

export function setSesion(s: Sesion | null) {
  if (s) localStorage.setItem("halu_sesion", JSON.stringify(s));
  else localStorage.removeItem("halu_sesion");
}

export async function login(email: string, password: string): Promise<Sesion> {
  const res = await fetch(`${API_URL}/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Credenciales inválidas");
  const s = (await res.json()) as Sesion;
  setSesion(s);
  return s;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const sesion = getSesion();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(sesion ? { Authorization: `Bearer ${sesion.access}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    setSesion(null);
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Sesión expirada");
  }
  if (!res.ok) {
    const cuerpo = await res.text();
    throw new Error(`API ${res.status}: ${cuerpo}`);
  }
  return res.json() as Promise<T>;
}

export const ESTADOS = [
  "registrado",
  "espera",
  "llamado",
  "atencion",
  "paraclinicos",
  "finalizado",
] as const;

export type Estado = (typeof ESTADOS)[number];

export const ESTADO_LABEL: Record<Estado, string> = {
  registrado: "Registrado",
  espera: "En espera",
  llamado: "Llamado",
  atencion: "En atención",
  paraclinicos: "Paraclínicos",
  finalizado: "Finalizado",
};

// Transiciones válidas (espejo de la máquina de estados del backend).
export const SIGUIENTES: Record<Estado, Estado[]> = {
  registrado: ["espera"],
  espera: ["llamado"],
  llamado: ["atencion", "espera"],
  atencion: ["paraclinicos", "finalizado"],
  paraclinicos: ["atencion", "finalizado"],
  finalizado: [],
};

export interface Atencion {
  id: number;
  trabajador_nombre: string;
  empresa_nombre: string;
  sede: number;
  consultorio_nombre: string | null;
  tipo_examen: string;
  estado: Estado;
  profesional_nombre: string | null;
  estado_actualizado_at: string;
}

export const TIPO_EXAMEN_LABEL: Record<string, string> = {
  pre_ingreso: "Pre-ingreso",
  periodico: "Periódico",
  egreso: "Egreso",
  post_incapacidad: "Post-incapacidad",
  retorno_laboral: "Retorno laboral",
  seguimiento: "Seguimiento",
};
