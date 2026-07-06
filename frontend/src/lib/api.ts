/**
 * Multi-tenant por dominio: la API y el WebSocket usan SIEMPRE el mismo
 * hostname con el que el usuario entró (localhost → IPS demo,
 * demo2.localhost → IPS Norte, ips-x.halu.co → IPS X en producción).
 * Así el backend (django-tenants) resuelve el esquema correcto y todos los
 * datos quedan amarrados a esa IPS sin selector manual en el login.
 * Las variables NEXT_PUBLIC_* siguen disponibles como override explícito.
 */
function hostActual(): string {
  return typeof window !== "undefined" ? window.location.hostname : "localhost";
}

function apiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? `http://${hostActual()}:8000/api`;
}

export function wsUrl(): string {
  return process.env.NEXT_PUBLIC_WS_URL ?? `ws://${hostActual()}:8000/ws`;
}

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
  if (s) {
    localStorage.setItem("halu_sesion", JSON.stringify(s));
    // Marcador para el middleware (server-side no ve localStorage).
    document.cookie = "halu_auth=1; path=/; max-age=86400; samesite=lax";
  } else {
    localStorage.removeItem("halu_sesion");
    localStorage.removeItem("halu_yo");
    document.cookie = "halu_auth=; path=/; max-age=0";
    document.cookie = "halu_rol=; path=/; max-age=0";
  }
}

export function setYo(yo: Yo) {
  localStorage.setItem("halu_yo", JSON.stringify(yo));
  document.cookie = `halu_rol=${yo.rol}; path=/; max-age=86400; samesite=lax`;
}

/** Cierra la sesión y regresa al login. */
export function logout() {
  setSesion(null);
  window.location.href = "/login";
}

export async function login(email: string, password: string): Promise<Sesion> {
  const res = await fetch(`${apiUrl()}/token/`, {
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
  const res = await fetch(`${apiUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(sesion ? { Authorization: `Bearer ${sesion.access}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 401) {
    // Token vencido o inválido: limpiar sesión y volver al login.
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

/** Subida de archivos (multipart). No fija Content-Type: lo pone el navegador. */
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const sesion = getSesion();
  const res = await fetch(`${apiUrl()}${path}`, {
    method: "POST",
    body: form,
    headers: sesion ? { Authorization: `Bearer ${sesion.access}` } : {},
  });
  if (res.status === 401) {
    setSesion(null);
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Sesión expirada");
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
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
  trabajador_documento?: string;
  empresa_nombre: string;
  sede: number;
  consultorio_nombre: string | null;
  tipo_examen: string;
  estado: Estado;
  profesional_nombre: string | null;
  estado_actualizado_at: string;
  created_at: string;
}

export const TIPO_EXAMEN_LABEL: Record<string, string> = {
  pre_ingreso: "Pre-ingreso",
  periodico: "Periódico",
  egreso: "Egreso",
  post_incapacidad: "Post-incapacidad",
  retorno_laboral: "Retorno laboral",
  seguimiento: "Seguimiento",
};
