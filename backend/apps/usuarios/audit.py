"""
Helper de auditoría (regla 9): registrar toda lectura/escritura sobre datos
clínicos. Solo metadatos — jamás contenido clínico.
"""
from .models import AccionAudit, AuditLog


def registrar(usuario, accion: AccionAudit, obj, campo: str = "", descripcion: str = "", ip=None):
    AuditLog.objects.create(
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        accion=accion,
        modelo=f"{obj._meta.app_label}.{obj.__class__.__name__}",
        objeto_id=str(obj.pk),
        campo=campo,
        descripcion=descripcion,
        ip=ip,
    )


def ip_de(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
