"""
Capa de servicio del tablero: transiciona la atención y emite el evento
WebSocket al grupo de la sede (Channels + Redis pub/sub — nunca polling).

El modelo NO conoce Channels; este módulo es el único punto de acople.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connection


def grupo_tablero(schema_name: str, sede_id: int) -> str:
    """Nombre del grupo de Channels, aislado por tenant y sede."""
    return f"tablero_{schema_name}_{sede_id}"


def grupo_pantalla(schema_name: str, sede_id: int) -> str:
    """Grupo de la pantalla pública de sala de espera (solo llamados)."""
    return f"pantalla_{schema_name}_{sede_id}"


def transicionar_atencion(atencion, nuevo_estado, usuario, nota=""):
    """
    Valida y aplica la transición (Atencion.cambiar_estado) y luego difunde
    el evento al tablero de la sede. Devuelve el HistorialEstado creado.
    Lanza TransicionInvalidaError si la máquina de estados lo rechaza.
    """
    historial = atencion.cambiar_estado(nuevo_estado, usuario, nota)

    schema = connection.schema_name  # tenant activo (django-tenants)
    layer = get_channel_layer()
    evento = {
        "type": "evento.atencion",
        "payload": {
            "atencion_id": atencion.id,
            "estado_anterior": historial.estado_anterior,
            "estado_nuevo": historial.estado_nuevo,
            "sede_id": atencion.sede_id,
            "consultorio_id": atencion.consultorio_id,
            "trabajador_nombre": f"{atencion.trabajador.nombres} {atencion.trabajador.apellidos}",
            "timestamp": historial.timestamp.isoformat(),
        },
    }
    async_to_sync(layer.group_send)(grupo_tablero(schema, atencion.sede_id), evento)

    # La pantalla pública solo recibe llamados (sin más datos que nombre y consultorio).
    if historial.estado_nuevo == "llamado":
        async_to_sync(layer.group_send)(
            grupo_pantalla(schema, atencion.sede_id),
            {
                "type": "evento.llamado",
                "payload": {
                    "atencion_id": atencion.id,
                    "trabajador_nombre": evento["payload"]["trabajador_nombre"],
                    "consultorio_nombre": atencion.consultorio.nombre if atencion.consultorio else None,
                    "timestamp": evento["payload"]["timestamp"],
                },
            },
        )
    return historial
