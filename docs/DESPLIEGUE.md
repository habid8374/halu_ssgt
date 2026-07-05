# Despliegue: Railway (backend) + Vercel (frontend)

Guía para desplegar SIN dominio propio, usando los dominios gratuitos
`*.up.railway.app` y `*.vercel.app`. El multi-tenant queda intacto: hoy la
IPS principal usa el dominio de Railway; cuando compres un dominio, agregas
IPS/dominios desde el admin sin tocar código.

> Datos de salud reales: antes de subir pacientes reales, documenta la
> transferencia internacional (Ley 1581/2012) en tu manual de tratamiento de
> datos, o migra a VPS (plan original, CLAUDE.md §2).

---

## 0. Genera tus secretos (una sola vez)

En cualquier terminal con Python (o https://djecrety.ir para el primero):

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"   # DJANGO_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"   # CRYPTOGRAPHY_KEY (¡distinta!)
```

Guárdalos en un lugar seguro. **Nunca** en el repositorio.

---

## 1. Railway — backend (≈15 min)

1. https://railway.app → **Login with GitHub** → autoriza.
2. **New Project → Deploy from GitHub repo** → `habid8374/halu_ssgt`.
3. En el servicio creado: **Settings → Root Directory = `backend`** (usa el
   Dockerfile automáticamente).
4. Agrega las bases de datos: **+ New → Database → PostgreSQL** y luego
   **+ New → Database → Redis**.
5. Servicio backend → **Settings → Networking → Generate Domain**. Anota el
   dominio (ej: `halu-ssgt-production.up.railway.app`).
6. Servicio backend → **Variables** (pestaña) → agrega:

   | Variable | Valor |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
   | `DJANGO_SECRET_KEY` | (secreto 1 del paso 0) |
   | `CRYPTOGRAPHY_KEY` | (secreto 2 del paso 0) |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` |
   | `ALLOWED_HOSTS` | `TU-BACKEND.up.railway.app,TU-FRONTEND.vercel.app` |
   | `CSRF_TRUSTED_ORIGINS` | `https://TU-BACKEND.up.railway.app` |
   | `CORS_ALLOWED_ORIGINS` | `https://TU-FRONTEND.vercel.app` |
   | `BOOTSTRAP_DOMINIO` | `TU-BACKEND.up.railway.app` |
   | `BOOTSTRAP_IPS_NOMBRE` | el nombre de tu IPS |
   | `BOOTSTRAP_IPS_NIT` | el NIT de tu IPS |
   | `DJANGO_SUPERUSER_EMAIL` | tu correo |
   | `DJANGO_SUPERUSER_PASSWORD` | una clave FUERTE (es la llave maestra) |

   (El dominio de Vercel lo obtienes en el paso 2; vuelve y complétalo.)
7. **Settings → Deploy → Custom Start Command**: `sh entrypoint.prod.sh`
8. **Worker de Celery**: + New → GitHub repo (el mismo) → Root Directory
   `backend` → Start Command `celery -A config worker -l info` → copia las
   MISMAS variables (Railway permite "Shared Variables" para no repetir).
9. **Beat de Celery** (alertas de plazos): igual que el worker pero con
   Start Command `celery -A config beat -l info`.
10. Deploy. En los logs del servicio web debes ver:
    `IPS '...' creada con dominio ...` y `Superusuario ... (admin: ...)`.

**Tu admin**: `https://TU-BACKEND.up.railway.app/admin` con el correo/clave
del superusuario. Desde ahí creas usuarios con su rol (Usuarios → Añadir),
sedes, consultorios, empresas, tarifas, profesiogramas, y las IPS/dominios
futuros (visible solo para superusuario).

---

## 2. Vercel — frontend (≈5 min)

1. https://vercel.com → **Continue with GitHub**.
2. **Add New → Project** → importa `habid8374/halu_ssgt`.
3. **Root Directory**: `frontend` (Framework: Next.js, se detecta solo).
4. **Environment Variables**:

   | Variable | Valor |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://TU-BACKEND.up.railway.app/api` |
   | `NEXT_PUBLIC_WS_URL` | `wss://TU-BACKEND.up.railway.app/ws` |

5. **Deploy**. Tu app queda en `https://TU-PROYECTO.vercel.app`.
6. Vuelve a Railway y completa `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` con
   este dominio de Vercel (paso 1.6) → redeploy del backend.

Entra a la app con tu superusuario **no** — el superusuario es para el
/admin. Para la app, crea en el admin los usuarios operativos (recepción,
médico con su perfil profesional y licencia SST, coordinador, psicólogo,
portal de empresa) y entra con ellos.

---

## 3. Cuando compres el dominio

1. Vercel → Domains → agrega `app.tudominio.com` (o wildcard por IPS).
2. Railway → Settings → Networking → Custom Domain `api.tudominio.com`.
3. Admin → Dominios → agrega `api.tudominio.com` a tu IPS (o crea nuevas IPS
   con su subdominio cada una).
4. Actualiza las variables (`ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`,
   `CSRF_TRUSTED_ORIGINS`, `NEXT_PUBLIC_*`).

---

## Seguridad aplicada (OWASP Top 10 — Res. 1888/2025)

- TLS forzado + HSTS + cookies Secure/HttpOnly/SameSite; DEBUG off; el
  arranque FALLA si faltan secretos o si la clave de cifrado clínico no es
  dedicada.
- Rate-limiting: login 10/min por IP; API 60/min anónimo, 600/min autenticado.
- JWT de 30 min con refresh rotado, amarrado al tenant (claim `schema`).
- Permisos por objeto + scoping por rol en cada queryset (matriz §4).
- Cifrado a nivel de columna de campos clínicos; AuditLog append-only.
- Cabeceras: nosniff, X-Frame-Options DENY, Referrer-Policy same-origin.
- Multi-tenant: esquema por IPS; hosts y orígenes explícitos, sin comodines.

Pendientes conocidos (siguiente iteración de seguridad): bloqueo de cuenta
tras N intentos en el admin (django-axes), 2FA para superusuario, backups
automatizados verificados (retención 15 años) y rotación documentada de
claves de cifrado.
