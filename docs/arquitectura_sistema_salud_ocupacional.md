# Arquitectura del sistema para IPS de salud ocupacional
### Halu Salud Ocupacional — documento de arquitectura previo a desarrollo

---

## 1. Resumen ejecutivo

Este documento consolida la investigación normativa y funcional necesaria para diseñar, antes de escribir una sola línea de código, un sistema robusto para IPS de salud ocupacional en Colombia. Cubre: marco legal aplicable, módulos funcionales completos, modelo de roles y permisos, modelo de datos de alto nivel, arquitectura técnica (backend Django + frontend Next.js), integraciones externas obligatorias, seguridad/cumplimiento y fases de implementación.

---

## 2. Marco normativo consolidado (lo que el sistema DEBE reflejar)

### 2.1 Evaluaciones médicas e historia clínica ocupacional
- **Resolución 1843 de 2025** (Min. Trabajo) — norma central vigente. Deroga la Resolución 2346 de 2007. Define tipos mínimos de evaluación (pre-ingreso, periódica, egreso, post-incapacidad, retorno laboral, seguimiento/control), contenido mínimo del concepto médico ocupacional, plazo de 20 días hábiles para adaptación de condiciones de trabajo tras una recomendación, y separación estricta entre historia clínica (reservada) y concepto de aptitud (lo único que recibe el empleador).
- **Resolución 1995 de 1999** — define la historia clínica como documento privado, obligatorio y sometido a reserva.
- **Ley 23 de 1981** — reserva profesional y ética médica.
- **Retención documental**: mínimo 15 años desde la última atención (Acuerdos AGN 07/1994, 011/1996, 049/2000).
- **Resolución 4502 de 2012** — licencia SST vigente obligatoria para el profesional que practica el examen.

### 2.2 Sistema de Gestión de Seguridad y Salud en el Trabajo (SG-SST)
- **Decreto 1072 de 2015** — Decreto Único Reglamentario del Sector Trabajo; columna estructural del SG-SST.
- **Resolución 312 de 2019** — estándares mínimos verificables del SG-SST.
- **Resolución 2404 de 2019** (modifica Resolución 2646 de 2008) — batería de riesgo psicosocial: cuestionarios intralaboral, extralaboral, estrés y ficha sociodemográfica. Solo aplicable por psicólogo con licencia SST vigente. Periodicidad: anual (riesgo alto) o cada 2 años (riesgo medio/bajo). Custodia obligatoria dentro de la historia clínica ocupacional cuando la aplica la IPS — el empleador NUNCA puede tener copia de los instrumentos individuales, solo informes consolidados agregados.
- **Resolución 1401 de 2007** — investigación de accidentes e incidentes de trabajo; define accidente grave/leve/mortal y plazos de investigación (15 días si hay fallecimiento).
- **FURAT / FUREL** — reporte obligatorio a la ARL dentro de 2 días hábiles tras accidente de trabajo o diagnóstico de enfermedad laboral (Resolución 1570 de 2005, Decreto 1295 de 1994, Ley 1562 de 2012). Multas hasta 500 SMLMV al empleador por reporte incompleto.

### 2.3 Habilitación como prestador de servicios de salud
- **Resolución 3100 de 2019** (modificada por Res. 2215/2020 y Res. 544/2023) — habilitación ante el REPS. Define "Sistema de Información Clínico" de forma que cualquier software que gestione historia clínica queda cubierto por el estándar de Historia Clínica y Registros del Sistema Único de Habilitación.
- **Resolución 2654 de 2019** — telemedicina, si la IPS presta servicios remotos (frecuente para empresas con sedes alejadas).

### 2.4 Interoperabilidad de historia clínica electrónica (obligación a mediano plazo)
- **Ley 2015 de 2020** — crea la Historia Clínica Electrónica Interoperable (HCEI) nacional.
- **Resolución 866 de 2021** — conjunto de datos clínicos relevantes obligatorio: (i) identificación del usuario, (ii) contacto con el servicio de salud, (iii) tecnologías en salud usadas, (iv) resultados de su uso. Estándar técnico de intercambio: **HL7 FHIR**.
- **Resolución 1888 de 2025** — adopta el Resumen Digital de Atención (RDA) como mecanismo concreto de implementación de la interoperabilidad, con arquitectura basada en API y referencia explícita al **OWASP Top 10** como marco de seguridad exigido.

### 2.5 Protección de datos personales
- **Ley 1581 de 2012** — los datos de salud son datos sensibles; exige manual de tratamiento, autorización, y trazabilidad de accesos. El empleador solo puede acceder a la historia clínica ocupacional sin autorización del titular si actúa cumpliendo obligación legal de investigar accidentes/enfermedades, y a través del médico laboral — nunca directamente.

### 2.6 Facturación y reporte al sistema de salud (RIPS — cuándo aplica y cuándo no)
- **Resolución 948 de 2026** (Min. Salud, 14 de mayo de 2026) reemplaza por completo a la Resolución 2275 de 2023 y sus modificatorias (558 y 1884 de 2024). Reglamenta el RIPS como soporte obligatorio de la Factura Electrónica de Venta (FEV) en salud.
- Mecánica: el prestador genera el RIPS en JSON, lo envía junto a la FEV al **MUV** (Mecanismo Único de Validación) del Ministerio, y obtiene el **CUV** (Código Único de Validación). Sin CUV, la Entidad Responsable de Pago no puede recibir ni tramitar la factura.
- **CUCON** (Código Único de Contrato, 64 caracteres, SHA-256) se genera en el **SIIFA** al inscribir el contrato entre prestador y pagador; es obligatorio para facturar salvo excepciones puntuales (urgencias sin contrato, ADRES, SOAT, órdenes judiciales).
- Cronograma de transición: desde el 1 de junio de 2026, 14 reglas de validación pasaron de "notificación" a "rechazo"; desde el 1 de julio de 2026 entran 5 reglas nuevas de rechazo y cambios estructurales obligatorios en el JSON del RIPS. Incluye campos paralelos CIE-10/CIE-11 durante la transición.

**Cuándo NO aplica RIPS a este sistema**: la Resolución 948/2026 excluye explícitamente de RIPS a la medicina preventiva/ocupacional no amparada por el SGSSS (el mismo tratamiento que da a los Centros de Reconocimiento de Conductores). Esto significa que los exámenes de ingreso, periódicos, de egreso, la batería psicosocial y el profesiograma —pagados directamente por la empresa cliente— **no requieren RIPS**, porque son un servicio privado fuera del SGSSS.

**Cuándo SÍ aplica RIPS a este sistema**: cuando la IPS atiende y factura a la **ARL** (que sí está entre los actores obligados por la Res. 948, en su componente de salud) atenciones derivadas de un **accidente de trabajo o enfermedad laboral** — incluidas urgencias facturadas al SGSSS por esa vía. Este caso queda acoplado al módulo de gestión de accidentes (FURAT/FUREL, sección 3), no al flujo general de admisión.

**Implicación de diseño**: no es necesario construir el motor de RIPS/FEV en la fase 1 (núcleo operativo). Se recomienda incorporarlo en la fase 2-3, exclusivamente ligado al módulo de accidentes de trabajo, reutilizando el mismo patrón ya implementado en Halu Medic (Factus, CUV, CUCON, RIPS JSON) en lugar de reconstruirlo desde cero.

---

## 3. Módulos funcionales del sistema

| Módulo | Función | Norma que lo exige |
|---|---|---|
| Admisión / recepción | Registro de paciente, verificación de convenio/empresa, consentimiento informado digital, asignación a cola | Res. 1843/2025, Ley 1581/2012 |
| Tablero de flujo (kanban por colores) | Visibilidad en tiempo real del estado de cada atención para recepción y médico | Buena práctica operativa (no normativo) |
| Historia clínica ocupacional | Registro clínico completo, reservado, con plantilla por tipo de examen | Res. 1843/2025, Res. 1995/1999 |
| Concepto médico ocupacional | Documento que sí ve el empleador — generado a partir de la historia clínica pero con campos filtrados | Res. 1843/2025 art. 19 |
| Consentimiento informado | Captura firmada/con trazabilidad antes de pruebas complementarias | Ley 23/1981, Ley 1581/2012 |
| Batería de riesgo psicosocial | Cuestionarios digitales intralaboral/extralaboral/estrés con custodia separada del resto de la historia clínica | Res. 2404/2019 |
| Profesiograma / matriz de peligros | Catálogo de exámenes requeridos por cargo/empresa | Decreto 1072/2015 |
| Gestión de accidentes e incidentes (FURAT/FUREL) | Registro, investigación y generación de reporte a ARL dentro de plazo | Res. 1401/2007, Res. 1570/2005 |
| Agenda / programación de citas | Periodicidad de exámenes, alertas de vencimiento | Res. 1843/2025 |
| Gestión de convenios empresariales | Tarifas, empresas afiliadas, tipos de examen contratados | — |
| Facturación | Factura al empleador y, si aplica, facturación electrónica DIAN (Factus) | Normativa DIAN |
| Auditoría / trazabilidad de accesos | Log inmutable de quién vio o modificó cada historia clínica | Ley 1581/2012, Res. 1888/2025 (seguridad) |
| Interoperabilidad (fase 2) | Generación de RDA / estructura FHIR para conexión futura al mecanismo nacional | Ley 2015/2020, Res. 866/2021 |
| Reportes gerenciales | Indicadores de tiempos de atención, cumplimiento SG-SST, productividad | Res. 312/2019 (evidencia de estándares) |
| Notificaciones | WhatsApp/email para citas, vencimiento de exámenes periódicos, seguimiento a recomendaciones (plazo 20 días hábiles) | Res. 1843/2025 |
| Portal empresa-cliente | El empleador consulta únicamente conceptos de aptitud de sus trabajadores, nunca historia clínica | Res. 1843/2025 |

---

## 4. Roles y control de acceso (el corazón legal del sistema)

| Rol | Ve historia clínica completa | Ve concepto de aptitud | Ve tablero operativo | Ve reportes agregados |
|---|---|---|---|---|
| Recepción/admisión | No | No | Sí (todos los pacientes) | No |
| Médico ocupacional | Sí (solo pacientes asignados) | Sí | Sí (su cola) | No |
| Psicólogo SST | Solo instrumentos psicosociales que aplicó | No | No | Informes consolidados agregados |
| Coordinador/gerencia IPS | No | No (salvo excepción legal auditada) | Sí (todas las sedes) | Sí |
| Empresa cliente (portal externo) | No, nunca | Sí (solo sus trabajadores) | No | No |
| Administrador de sistema | No (acceso técnico, no clínico) | No | No | Métricas técnicas |

Esta tabla es, en la práctica, tu especificación de permisos a nivel de base de datos y de API — no una simple guía de UI. Row-level security o filtros a nivel de queryset en Django deben aplicar esta matriz sin excepción.

---

## 5. Modelo de datos — entidades principales (alto nivel)

```
Empresa (convenio)
 └── Trabajador
      └── Atencion (examen/consulta)
           ├── estado (registrado, espera, llamado, atencion, paraclinicos, finalizado)
           ├── HistorialEstado (auditoría de cada cambio, timestamp, usuario)
           ├── HistoriaClinicaOcupacional (reservada)
           ├── ConceptoMedicoOcupacional (visible al empleador)
           ├── ConsentimientoInformado
           ├── InstrumentoPsicosocial (si aplica, custodia separada)
           └── DocumentoAdjunto (paraclínicos, exámenes complementarios)

Profesional (médico/psicólogo)
 └── LicenciaSST (número, vigencia — validación obligatoria)

AccidenteTrabajo
 ├── InvestigacionAccidente
 └── ReporteFURAT / ReporteFUREL (estado de envío a ARL)

Profesiograma
 └── TipoExamenRequerido (por cargo/empresa)

AuditLog (inmutable)
 └── quién, qué, cuándo, sobre qué registro
```

---

## 6. Arquitectura técnica

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│        Next.js 14            │        │         Django (DRF)         │
│  /recepcion   (tablero)       │◄──────►│  API REST                     │
│  /consultorio/[id] (médico)   │  HTTPS │  ├─ pacientes, atenciones     │
│  /gerencia    (reportes)       │        │  ├─ historia clínica (RBAC)   │
│  /portal-empresa (cliente)    │        │  ├─ concepto médico            │
│  /pantalla/[sede] (pública)   │        │  └─ facturación / Factus       │
│                               │        │                              │
│  hook useAtencionesSocket() ──┼──WS───►│  Django Channels (consumer)  │
└─────────────────────────────┘        │  ├─ eventos de cambio de estado│
                                        └──────────────┬───────────────┘
                                                        │
                                        ┌───────────────▼───────────────┐
                                        │   Celery + Redis (async)       │
                                        │  ├─ semáforo de tiempos        │
                                        │  ├─ alertas 20 días hábiles     │
                                        │  ├─ recordatorios WhatsApp/mail │
                                        │  └─ generación RDA/FHIR (fase 2)│
                                        └───────────────┬───────────────┘
                                                        │
                                        ┌───────────────▼───────────────┐
                                        │   PostgreSQL (multi-tenant)    │
                                        │  esquema por IPS/sede           │
                                        └─────────────────────────────────┘
```

**Backend — Django + DRF + Channels**
- Multi-tenant (mismo patrón que Halu Plataforma Escolar): un esquema por IPS o por sede, según cuántos clientes IPS distintos manejará el producto.
- Django Channels + Redis pub/sub para WebSockets del tablero en tiempo real — evita polling.
- Celery + Redis para tareas asíncronas: recálculo del semáforo de espera cada minuto, alertas de plazo de 20 días hábiles, recordatorios de exámenes periódicos, envío de reportes FURAT/FUREL.
- Django REST Framework con permisos a nivel de objeto (no solo de vista) para aplicar la matriz de roles de la sección 4.

**Frontend — Next.js 14 + TypeScript + Tailwind + Framer Motion**
- App Router con rutas segregadas por rol y middleware de autenticación/autorización.
- Client components para el tablero en tiempo real (WebSocket nativo contra el consumer de Channels).
- Server components para reportes gerenciales pesados (menor carga en cliente).
- Framer Motion para las transiciones de las tarjetas de paciente entre columnas del tablero.

**Almacenamiento y retención**
- PostgreSQL con backups automatizados; política de retención de 15 años para historia clínica (no borrado físico, archivado en frío tras cierto tiempo).
- Documentos adjuntos (paraclínicos, PDFs firmados) en almacenamiento de objetos con cifrado en reposo.

---

## 7. Integraciones externas

| Integración | Propósito | Estado/prioridad |
|---|---|---|
| REPS (Min. Salud) | Consulta de habilitación del prestador | Consulta manual/validación en fase 1 |
| RETHUS | Validación de licencia SST del profesional | Recomendable automatizar en fase 2 |
| ARL (FURAT/FUREL) | Reporte de accidentes/enfermedades laborales | Fase 1: generar el formato; fase 2: envío automatizado si la ARL expone API |
| RIPS / MUV / SIIFA (CUCON, CUV) | Solo para atenciones de accidente de trabajo/enfermedad laboral facturadas a la ARL — no aplica a exámenes ocupacionales pagados por la empresa | Fase 2-3, acoplado al módulo de accidentes |
| Factus (DIAN) | Facturación electrónica del componente RIPS/ARL cuando aplique | Reutilizable de Halu Medic |
| WhatsApp Business API | Recordatorios y notificaciones | Fase 1 |
| Mecanismo de interoperabilidad nacional (RDA/FHIR) | Cumplimiento Ley 2015/2020 y Res. 866/2021 | Fase 2-3, cuando el mecanismo esté operativo a nivel nacional |

---

## 8. Seguridad y cumplimiento

- **Separación de datos por diseño**: la historia clínica completa y el concepto de aptitud nunca deben residir en el mismo endpoint de API accesible por el rol "empresa cliente".
- **Cifrado**: en tránsito (TLS) y en reposo (campos clínicos sensibles cifrados a nivel de columna, no solo de disco).
- **Auditoría inmutable**: cada lectura/escritura sobre historia clínica queda registrada (quién, cuándo, qué campo) — exigible ante la SIC bajo Ley 1581/2012.
- **OWASP Top 10**: ya viene siendo tu práctica en Halu; la Resolución 1888/2025 lo cita explícitamente como referencia de seguridad para el mecanismo de interoperabilidad — así que este hardening no es opcional, es normativo.
- **Consentimiento informado con trazabilidad**: versión del documento firmado, timestamp, IP/dispositivo si aplica.
- **Manual de tratamiento de datos** (documento legal, no solo técnico) — debe existir junto al sistema, no reemplazarlo.

---

## 9. Fases de implementación sugeridas

1. **Fase 1 — Núcleo operativo**: admisión, historia clínica ocupacional, concepto médico, tablero en tiempo real, agenda, roles y permisos base.
2. **Fase 2 — Cumplimiento ampliado**: batería psicosocial, gestión de accidentes (FURAT/FUREL), profesiograma, portal empresa-cliente, auditoría completa.
3. **Fase 3 — Facturación e integraciones**: facturación estándar a empresas (sin RIPS), RIPS/MUV/Factus **solo** para el módulo de accidentes de trabajo facturados a ARL, notificaciones WhatsApp, reportes gerenciales avanzados.
4. **Fase 4 — Interoperabilidad nacional**: estructura de datos alineada a Resolución 866/2021, generación de RDA, preparación para conexión FHIR cuando el mecanismo nacional esté disponible para IPS de este tamaño.

---

*Este documento es la base de diseño. El siguiente paso natural es el modelo de datos Django detallado (con migraciones) y el consumer de Channels para el tablero en tiempo real.*
