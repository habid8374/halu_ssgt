"""
Consumer del tablero de flujo en tiempo real (Channels + Redis pub/sub).

Dos niveles de suscripción sobre el mismo endpoint /ws/tablero/<sede_id>/:

  - Usuario autenticado con rol de tablero (recepción/médico/coordinador):
    grupo `tablero_<schema>_<sede>` — recibe TODOS los cambios de estado.
    La matriz §4 se respeta: recepción solo puede suscribirse a SU sede;
    el coordinador a cualquiera.

  - Conexión anónima (pantalla pública de sala de espera): grupo
    `pantalla_<schema>_<sede>` — SOLO recibe eventos de llamado
    (nombre + consultorio), sin ningún otro dato.

Los eventos los emite apps.atenciones.services.transicionar_atencion().
"""
import json

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.usuarios.roles import Rol

from .services import grupo_pantalla, grupo_tablero

ROLES_TABLERO = {Rol.RECEPCION, Rol.MEDICO, Rol.COORDINADOR}


class TableroConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sede_id = int(self.scope["url_route"]["kwargs"]["sede_id"])
        tenant = self.scope.get("tenant")
        user = self.scope.get("user")
        if tenant is None:
            await self.close(code=4404)
            return

        schema = tenant.schema_name

        if user is not None and user.is_authenticated and user.rol in ROLES_TABLERO:
            # Recepción y médico: solo su propia sede. Coordinador: todas (§4).
            if user.rol in {Rol.RECEPCION, Rol.MEDICO} and user.sede_id != self.sede_id:
                await self.close(code=4403)
                return
            self.grupo = grupo_tablero(schema, self.sede_id)
            self.modo = "tablero"
        else:
            # Anónimo o rol sin tablero: solo pantalla pública (llamados).
            self.grupo = grupo_pantalla(schema, self.sede_id)
            self.modo = "pantalla"

        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"type": "conectado", "modo": self.modo, "sede_id": self.sede_id}))

    async def disconnect(self, code):
        if hasattr(self, "grupo"):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    # --- handlers de eventos emitidos por services.transicionar_atencion ---
    async def evento_atencion(self, event):
        await self.send(json.dumps({"type": "atencion", **event["payload"]}))

    async def evento_llamado(self, event):
        await self.send(json.dumps({"type": "llamado", **event["payload"]}))
