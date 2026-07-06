import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Autorización centralizada por ruta (CLAUDE.md §7).
 *
 * - Sin sesión: cualquier ruta protegida redirige a /login.
 * - Con sesión: cada rol solo entra a sus rutas; si intenta otra,
 *   se le redirige a su home. "/" y "/login" redirigen al home del rol.
 * - /pantalla/[sede] es pública (TV de sala de espera) — no se protege.
 *
 * Nota: esto es UX/navegación. La seguridad REAL está en el backend
 * (permisos DRF por objeto + scoping de querysets); aunque alguien
 * salte este middleware, la API no le entrega nada que no le corresponda.
 */

const HOME_POR_ROL: Record<string, string> = {
  recepcion: "/recepcion",
  medico: "/consultorio/mi-cola",
  tecnico: "/estaciones",
  coordinador: "/gerencia",
  empresa_cliente: "/portal-empresa",
  psicologo_sst: "/psicosocial",
  admin_sistema: "/login",
};

// Prefijo de ruta → roles autorizados (espejo de la matriz §4).
const ROLES_POR_RUTA: Array<[string, string[]]> = [
  ["/recepcion", ["recepcion"]],
  ["/consultorio", ["medico"]],
  ["/estaciones", ["tecnico"]],
  ["/gerencia", ["coordinador"]],
  ["/portal-empresa", ["empresa_cliente"]],
  ["/psicosocial", ["psicologo_sst"]],
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const auth = request.cookies.get("halu_auth")?.value;
  const rol = request.cookies.get("halu_rol")?.value ?? "";

  const esLogin = pathname === "/login";
  const esRaiz = pathname === "/";

  // Sin sesión → solo /login (y las públicas fuera del matcher).
  if (!auth) {
    if (esLogin) return NextResponse.next();
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  // Con sesión: "/" y "/login" van al home del rol.
  if (esLogin || esRaiz) {
    const url = request.nextUrl.clone();
    url.pathname = HOME_POR_ROL[rol] ?? "/login";
    if (url.pathname === pathname) return NextResponse.next();
    return NextResponse.redirect(url);
  }

  // Con sesión: verificar que la ruta corresponde al rol.
  const regla = ROLES_POR_RUTA.find(([prefijo]) => pathname.startsWith(prefijo));
  if (regla && !regla[1].includes(rol)) {
    const url = request.nextUrl.clone();
    url.pathname = HOME_POR_ROL[rol] ?? "/login";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/login",
    "/recepcion/:path*",
    "/consultorio/:path*",
    "/estaciones/:path*",
    "/estaciones",
    "/gerencia/:path*",
    "/portal-empresa/:path*",
    "/psicosocial/:path*",
  ],
};
