"""
Fase 4 — Interoperabilidad nacional (Ley 2015/2020, Res. 866/2021, Res. 1888/2025).

Genera el Resumen Digital de Atención (RDA) como Bundle FHIR R4 con el
conjunto de datos clínicos relevantes obligatorio:
  (i)   identificación del usuario        -> Patient
  (ii)  contacto con el servicio de salud -> Encounter
  (iii) tecnologías en salud usadas       -> Procedure (tipo de examen)
  (iv)  resultados de su uso              -> Observation (concepto de aptitud)

El RDA NO expone la historia clínica reservada: solo el conjunto mínimo
interoperable. La conexión al mecanismo nacional (cuando esté operativo
para IPS de este tamaño) consumirá estos Bundles vía API, con el hardening
OWASP que exige la Res. 1888/2025.
"""
import uuid


def _referencia(recurso: dict) -> dict:
    return {"reference": f"urn:uuid:{recurso['id']}"}


def construir_rda(atencion) -> dict:
    """Bundle FHIR R4 (document) del Resumen Digital de Atención."""
    trabajador = atencion.trabajador
    concepto = getattr(atencion, "concepto", None)

    patient = {
        "resourceType": "Patient",
        "id": str(uuid.uuid4()),
        "identifier": [{
            "type": {"coding": [{"code": trabajador.tipo_documento}]},
            "value": trabajador.numero_documento,
        }],
        "name": [{"family": trabajador.apellidos, "given": [trabajador.nombres]}],
        "gender": {"M": "male", "F": "female"}.get(trabajador.sexo, "unknown"),
        "birthDate": str(trabajador.fecha_nacimiento) if trabajador.fecha_nacimiento else None,
    }

    encounter = {
        "resourceType": "Encounter",
        "id": str(uuid.uuid4()),
        "status": "finished" if atencion.estado == "finalizado" else "in-progress",
        "class": {"code": "AMB", "display": "ambulatory"},
        "type": [{"text": f"Evaluación médica ocupacional — {atencion.get_tipo_examen_display()}"}],
        "subject": _referencia(patient),
        "period": {"start": atencion.created_at.isoformat()},
        "serviceProvider": {"display": atencion.sede.nombre},
    }

    procedure = {
        "resourceType": "Procedure",
        "id": str(uuid.uuid4()),
        "status": "completed" if atencion.estado == "finalizado" else "in-progress",
        "code": {"text": atencion.get_tipo_examen_display()},
        "subject": _referencia(patient),
        "encounter": _referencia(encounter),
    }

    recursos = [patient, encounter, procedure]

    if concepto is not None and concepto.firmado:
        observation = {
            "resourceType": "Observation",
            "id": str(uuid.uuid4()),
            "status": "final",
            "code": {"text": "Concepto de aptitud ocupacional (Res. 1843/2025)"},
            "valueString": concepto.get_aptitud_display(),
            "subject": _referencia(patient),
            "encounter": _referencia(encounter),
            "effectiveDateTime": str(concepto.fecha_emision),
            "performer": [{"display": concepto.profesional.nombre_completo}],
            "note": (
                [{"text": f"Recomendaciones: {concepto.recomendaciones_laborales}"}]
                if concepto.recomendaciones_laborales else []
            ),
        }
        recursos.append(observation)

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "document",
        "timestamp": atencion.updated_at.isoformat(),
        "entry": [{"fullUrl": f"urn:uuid:{r['id']}", "resource": r} for r in recursos],
    }
