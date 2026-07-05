# Halu Salud Ocupacional

Sistema SaaS multi-tenant para IPS de salud ocupacional en Colombia. Parte del
ecosistema Halu (Django multi-tenant + Next.js).

> Reglas de negocio, normativa y arquitectura: ver [`CLAUDE.md`](./CLAUDE.md) y
> [`docs/arquitectura_sistema_salud_ocupacional.md`](./docs/arquitectura_sistema_salud_ocupacional.md).

## Stack

- **Backend**: Django 5 + DRF + Django Channels + Celery + Redis + PostgreSQL
  (multi-tenant por esquema, `django-tenants` — **un esquema por IPS**).
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion.
- **Tiempo real**: Channels + Redis pub/sub (sin polling).

## Estructura

```
backend/
  config/            # settings (base/dev), asgi, wsgi, celery, routing WS, urls
  apps/
    tenants/         # IPS (tenant) + Dominio   [SHARED_APPS]
    usuarios/        # Usuario, roles, Profesional, LicenciaSST, AuditLog
    atenciones/      # Empresa, Sede, Consultorio, Trabajador, Atencion, HistorialEstado
    historia_clinica/# HistoriaClinica (cifrada), Concepto, Consentimiento, Adjunto
    accidentes/      # scaffold (FURAT/FUREL) — fase 2
frontend/
  src/app/           # /recepcion /consultorio/[id] /gerencia /portal-empresa /pantalla/[sede]
  src/hooks/         # useAtencionesSocket (tablero en tiempo real)
docker-compose.yml   # db, redis, web (Daphne/ASGI), worker, beat
```

## Decisiones de arquitectura (fase 1)

| Punto (CLAUDE.md §8) | Decisión |
|---|---|
| Aislamiento tenant | Un esquema por **IPS**; Sede/Consultorio son modelos internos. |
| Cifrado de campos clínicos (regla 10) | App-level (`django-cryptography`, Fernet), aislado en `historia_clinica/fields.py`. |
| Almacenamiento de adjuntos | Abstraído con `django-storages`; FileSystem en dev, S3-compatible por env. |

## Desarrollo

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build      # migra + siembra datos demo + levanta la API
cd frontend && npm install && npm run dev
```

### Accesos de desarrollo (multi-tenant por dominio)

| URL | Qué es | Credenciales |
|---|---|---|
| http://localhost:3000 | IPS Demo Salud Ocupacional | `recepcion@demo.com` · `medico@demo.com` · `coordinador@demo.com` · `empresa@demo.com` (pass `demo1234`) |
| http://demo2.localhost:3000 | IPS Norte SST (segunda IPS: aislamiento) | mismos roles con `@demo2.com` (pass `demo1234`) |
| http://admin.localhost:8000/admin | Admin de plataforma (gestionar IPS y dominios) | `admin@halu.co` / `admin1234` |
| http://localhost:3000/pantalla/1 | Pantalla pública de sala de espera | sin login |

El tenant se resuelve por dominio: cada IPS ve exclusivamente sus datos y los
JWT quedan amarrados a su esquema (claim `schema`). Ver CLAUDE.md §8.

## Estado — Fase 1 COMPLETA ✅

Núcleo operativo terminado: modelos + migraciones multi-tenant, roles y
permisos legales por objeto (con tests), JWT amarrado por IPS, tablero en
tiempo real (Channels), admisión, historia clínica cifrada + concepto con
firma (licencia SST), portal empresa, agenda de citas con admisión al
tablero, admin de plataforma y sidebar por rol.

## Fase 2 — Cumplimiento ampliado ✅

- **Accidentes/enfermedad laboral**: registro FURAT/FUREL con plazo de 2 días
  hábiles calculado automáticamente, marcado de envío a ARL con radicado e
  investigación (Res. 1401/2007). UI en /gerencia/accidentes.
- **Alertas de plazo** (Celery beat, cada hora): FURAT/FUREL por vencer o
  vencidos y adaptación de condiciones (20 días hábiles, Res. 1843/2025).
  Bandeja en /gerencia/alertas; se auto-resuelven al enviar el reporte o
  marcar el seguimiento del concepto.
- **Batería psicosocial** (Res. 2404/2019): instrumentos individuales con
  custodia separada (solo el psicólogo que los aplicó, contenido cifrado,
  lecturas auditadas) e informe consolidado agregado con mínimo de
  anonimato. UI en /psicosocial (rol psicologo_sst: psicologo@demo.com).
- **Profesiograma**: matriz de exámenes por cargo/empresa (admin del tenant).

**Sin** RIPS ni facturación hasta fase 3 (CLAUDE.md §6).
