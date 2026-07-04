import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware de autorización por ruta (segregación por rol, CLAUDE.md §7).
 *
 * Estructura lista; la validación real de sesión/rol y el mapeo ruta→rol se
 * implementan junto con la autenticación JWT. Recordatorio normativo:
 * `empresa_cliente` NUNCA debe alcanzar rutas de historia clínica — la
 * autorización se aplica también en el backend (permisos DRF por objeto), no
 * solo aquí.
 */
export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: ["/recepcion/:path*", "/consultorio/:path*", "/gerencia/:path*", "/portal-empresa/:path*"],
};
