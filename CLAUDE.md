# Halu Salud Ocupacional — contexto del proyecto para Claude Code

Este archivo se lee automáticamente al iniciar cualquier sesión en este repositorio. Contiene las reglas de negocio, arquitectura y convenciones que NO deben violarse, aunque el prompt de una sesión puntual no las repita.

> Documento de arquitectura completo (investigación normativa detallada): `docs/arquitectura_sistema_salud_ocupacional.md`. Consúltalo antes de tomar decisiones de modelado que no estén resueltas aquí.

---

## 1. Qué es este proyecto

Sistema SaaS multi-tenant para IPS de salud ocupacional en Colombia. Cubre: admisión con tablero de flujo por colores en tiempo real, historia clínica ocupacional, concepto médico ocupacional, batería de riesgo psicosocial, gestión de accidentes de trabajo (FURAT/FUREL), agenda, portal para empresas cliente y facturación.

Parte del ecosistema Halu (mismo patrón que Halu Plataforma Escolar y Halu Medic): Django multi-tenant + Next.js.

---

## 2. Stack tecnológico (decisión ya tomada, no reabrir)

- **Backend**: Django 5 + Django REST Framework + Django Channels (WebSockets) + Celery + Redis + PostgreSQL (multi-tenant por esquema, `django-tenants`).
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS + Framer Motion.
- **Tiempo real**: Channels + Redis pub/sub. Nunca implementar el tablero con polling.
- **Infraestructura objetivo**: Docker Compose en desarrollo; Hostinger VPS + Nginx + Gunicorn en producción (o equivalente), siguiendo el patrón ya usado en Halu Medic.

---

## 3. Reglas de negocio no negociables (normativa colombiana)

Estas reglas vienen de investigación regulatoria exhaustiva. No se simplifican ni se omiten, incluso si complican el código.

1. **Separación estricta de acceso a datos clínicos** (Resolución 1843 de 2025): el rol `empresa_cliente` NUNCA puede consultar la historia clínica ocupacional completa, solo el `ConceptoMedicoOcupacional`. Esto se implementa a nivel de queryset/permiso de DRF, no solo ocultando campos en el frontend.
2. **Retención de historia clínica**: mínimo 15 años desde la última atención. No implementar borrado físico de historias clínicas; solo archivado/soft-delete.
3. **Consentimiento informado**: obligatorio antes de pruebas complementarias, con timestamp y trazabilidad de versión del documento firmado.
4. **Batería de riesgo psicosocial** (Resolución 2404 de 2019): los instrumentos individuales solo los puede ver el psicólogo que los aplicó. El rol `empleador`/`empresa_cliente` solo accede a informes consolidados y agregados, nunca a instrumentos individuales.
5. **Licencia SST vigente**: todo profesional que firma un concepto médico ocupacional debe tener un registro de licencia SST validado (campo obligatorio, con fecha de vigencia).
6. **FURAT/FUREL**: reporte de accidente de trabajo o enfermedad laboral a la ARL dentro de 2 días hábiles. El sistema debe alertar automáticamente si se acerca ese plazo (Celery beat).
7. **Plazo de adaptación de condiciones de trabajo**: 20 días hábiles desde que se emite una recomendación médica ocupacional. Debe generar alerta automática de seguimiento.
8. **RIPS solo aplica al módulo de accidentes de trabajo** facturados a la ARL (Resolución 948 de 2026). Los exámenes ocupacionales pagados directamente por la empresa (ingreso, periódico, egreso, batería psicosocial) NUNCA generan RIPS — quedan fuera del SGSSS. No mezclar el motor de facturación estándar con el motor RIPS/MUV/Factus.
9. **Auditoría inmutable**: toda lectura o escritura sobre historia clínica queda registrada (usuario, timestamp, campo). No usar `UPDATE`/`DELETE` directos sobre historial de auditoría; es append-only.
10. **Datos sensibles cifrados**: campos clínicos sensibles cifrados a nivel de columna en PostgreSQL, no solo TLS en tránsito.

---

## 4. Roles y permisos (matriz de referencia)

| Rol | Historia clínica completa | Concepto de aptitud | Tablero operativo | Reportes agregados |
|---|---|---|---|---|
| `recepcion` | No | No | Sí (todos) | No |
| `medico` | Sí (solo pacientes asignados) | Sí | Sí (su cola) | No |
| `psicologo_sst` | Solo instrumentos que aplicó | No | No | Informes consolidados |
| `coordinador` | No | No (salvo excepción legal auditada) | Sí (todas las sedes) | Sí |
| `empresa_cliente` | No, nunca | Sí (solo sus trabajadores) | No | No |
| `admin_sistema` | No (acceso técnico) | No | No | Métricas técnicas |

Implementar como permisos de DRF por objeto (`has_object_permission`), no solo por vista.

---

## 5. Modelo de datos — entidades base

```
Empresa (convenio)
 └── Trabajador
      └── Atencion (examen/consulta)
           ├── estado: registrado | espera | llamado | atencion | paraclinicos | finalizado
           ├── HistorialEstado (append-only, timestamp + usuario por cada cambio)
           ├── HistoriaClinicaOcupacional (reservada, cifrada)
           ├── ConceptoMedicoOcupacional (visible al empleador)
           ├── ConsentimientoInformado
           ├── InstrumentoPsicosocial (custodia separada)
           └── DocumentoAdjunto

Profesional (médico/psicólogo)
 └── LicenciaSST (número, vigencia)

AccidenteTrabajo
 ├── InvestigacionAccidente
 └── ReporteFURAT / ReporteFUREL (estado de envío, plazo 2 días hábiles)

Profesiograma
 └── TipoExamenRequerido (por cargo/empresa)

AuditLog (append-only)
```

---

## 6. Fases de desarrollo (construir en este orden)

1. **Fase 1 — Núcleo operativo**: modelos base, autenticación y roles, admisión, historia clínica ocupacional, concepto médico, tablero en tiempo real (Channels), agenda.
2. **Fase 2 — Cumplimiento ampliado**: batería psicosocial, gestión de accidentes (FURAT/FUREL) con alertas de plazo, profesiograma, portal empresa-cliente, auditoría completa.
3. **Fase 3 — Facturación**: facturación estándar a empresas (sin RIPS) y, por separado, motor RIPS/MUV/Factus acoplado únicamente al módulo de accidentes facturados a ARL.
4. **Fase 4 — Interoperabilidad nacional**: estructura de datos alineada a Resolución 866/2021, generación de RDA, preparación FHIR.

No adelantar fases: por ejemplo, no construir el motor RIPS en fase 1.

---

## 7. Convenciones de código

- Backend: `apps/` por dominio (`atenciones`, `historia_clinica`, `accidentes`, `facturacion`, `usuarios`). Migraciones siempre revisadas antes de aplicar en tenant compartido.
- Tests obligatorios para: transiciones de estado de `Atencion`, permisos por rol, generación de alertas de plazo (FURAT y 20 días hábiles).
- Frontend: rutas segregadas por rol bajo App Router (`/recepcion`, `/consultorio/[id]`, `/gerencia`, `/portal-empresa`, `/pantalla/[sede]`).
- Nunca loggear contenido de historia clínica en logs de aplicación (solo IDs y metadatos de auditoría).

---

## 8. Qué preguntar antes de asumir

Si una tarea toca alguno de estos puntos y no está resuelto en este documento ni en `docs/arquitectura_sistema_salud_ocupacional.md`, preguntar antes de implementar:
- Multi-tenant por esquema vs. por base de datos separada (definir según número de IPS cliente esperado).
- Proveedor de almacenamiento de objetos para documentos adjuntos.
- Si la IPS objetivo inicial atiende accidentes de trabajo (activa fase 3 RIPS) o no.
