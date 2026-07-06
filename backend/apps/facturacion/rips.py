"""
Motor RIPS (Res. 948/2026) — SOLO facturas ARL de accidentes/enfermedad laboral.

Genera el JSON del RIPS como soporte de la FEV y lo "valida" contra el MUV a
través de un adaptador. El adaptador real (credenciales del prestador,
endpoint del Ministerio, CUCON vía SIIFA, FEV vía Factus) se conecta en
despliegue — misma arquitectura ya probada en Halu Medic. Mientras tanto,
StubMUV deja el flujo completo operable en desarrollo y pruebas.
"""
import hashlib
import json

from django.db import connection


def construir_rips(factura_arl) -> dict:
    """
    Estructura mínima del RIPS JSON (Res. 948/2026) para la atención de un
    accidente de trabajo/enfermedad laboral facturada a la ARL. Incluye los
    campos duales CIE-10/CIE-11 del periodo de transición.
    """
    accidente = factura_arl.accidente
    trabajador = accidente.trabajador
    tenant = connection.tenant

    consulta = {
        "fechaInicioAtencion": str(accidente.fecha_evento),
        "codConsulta": "890201",  # consulta medicina general (parametrizable)
        "modalidadGrupoServicioTecSal": "01",
        "causaMotivoAtencion": "05" if accidente.tipo_evento == "accidente" else "06",
        # Transición CIE: ambos campos coexisten hasta cierre del cronograma.
        "codDiagnosticoPrincipal": "",       # CIE-10 (diligencia el médico)
        "codDiagnosticoPrincipalCIE11": "",  # CIE-11 (transición Res. 948/2026)
        "vrServicio": float(factura_arl.valor),
        "conceptoRecaudo": "05",  # ARL
    }
    if factura_arl.atencion_id:
        consulta["fechaInicioAtencion"] = str(factura_arl.atencion.created_at.date())

    return {
        "numDocumentoIdObligado": getattr(tenant, "nit", ""),
        "numFactura": factura_arl.numero or None,
        "tipoNota": None,
        "numNota": None,
        "cucon": factura_arl.cucon or None,
        "usuarios": [
            {
                "tipoDocumentoIdentificacion": trabajador.tipo_documento,
                "numDocumentoIdentificacion": trabajador.numero_documento,
                "tipoUsuario": "10",  # cotizante ARL
                "fechaNacimiento": str(trabajador.fecha_nacimiento or ""),
                "codSexo": trabajador.sexo or "",
                "codPaisResidencia": trabajador.pais_residencia or "170",
                "codMunicipioResidencia": trabajador.municipio_dane or "",
                "codZonaTerritorialResidencia": (
                    {"U": "02", "R": "01"}.get(trabajador.zona_territorial, "")
                ),
                "incapacidad": "NO",
                "codPaisOrigen": "170",
                "consecutivo": 1,
                "servicios": {"consultas": [consulta]},
            }
        ],
    }


class StubMUV:
    """
    Adaptador de validación MUV para desarrollo: calcula un CUV local
    (SHA-256 del RIPS) con el mismo formato del real. Sustituir por el
    cliente HTTP del MUV cuando existan credenciales del prestador.
    """

    @staticmethod
    def validar(rips: dict) -> str:
        canonico = json.dumps(rips, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonico.encode()).hexdigest()


def validar_en_muv(factura_arl) -> str:
    """Valida el RIPS y devuelve el CUV (stub en desarrollo)."""
    return StubMUV.validar(factura_arl.rips_json)
