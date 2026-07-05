"""
Tareas de cumplimiento (Celery beat) — reglas 6 y 7 de CLAUDE.md.

`revisar_plazos` corre periódicamente (beat, ver settings) sobre TODOS los
tenants y genera/actualiza alertas:

  - FURAT/FUREL pendientes: alerta cuando falta <=1 día hábil o venció.
  - Adaptación de condiciones (Res. 1843/2025): 20 días hábiles desde
    fecha_recomendacion del concepto; alerta cuando faltan <=5 días o venció.
  - Investigación de accidente sin completar: alerta al acercarse la fecha.
"""
import datetime as dt

from celery import shared_task
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from .utils import sumar_dias_habiles

PLAZO_ADAPTACION_DIAS_HABILES = 20
AVISO_ADAPTACION_DIAS = 5  # alertar cuando falten <= 5 días hábiles


def _asegurar_alerta(tipo, modelo, obj_id, mensaje, vence, hoy):
    from .models import Alerta

    alerta, creada = Alerta.objects.get_or_create(
        tipo=tipo,
        referencia_modelo=modelo,
        referencia_id=str(obj_id),
        defaults={"mensaje": mensaje, "vence": vence},
    )
    vencida = hoy > vence
    if not creada and (alerta.vencida != vencida or alerta.mensaje != mensaje):
        alerta.vencida = vencida
        alerta.mensaje = mensaje
        alerta.save(update_fields=["vencida", "mensaje"])
    elif creada and vencida:
        alerta.vencida = True
        alerta.save(update_fields=["vencida"])
    return alerta


def _revisar_tenant(hoy: dt.date) -> int:
    from apps.historia_clinica.models import ConceptoMedicoOcupacional

    from .models import Alerta, ReporteFUREL, ReporteFURAT

    generadas = 0

    # --- FURAT / FUREL pendientes (2 días hábiles) --------------------------
    for modelo, tipo in ((ReporteFURAT, "furat"), (ReporteFUREL, "furel")):
        pendientes = modelo.objects.filter(estado="pendiente").select_related(
            "accidente", "accidente__trabajador"
        )
        for rep in pendientes:
            umbral = sumar_dias_habiles(hoy, 1)  # falta <=1 día hábil
            if rep.fecha_limite <= umbral:
                estado = "VENCIDO" if hoy > rep.fecha_limite else "por vencer"
                _asegurar_alerta(
                    tipo, modelo.__name__, rep.pk,
                    f"Reporte {tipo.upper()} de {rep.accidente.trabajador} {estado} "
                    f"(límite {rep.fecha_limite}).",
                    rep.fecha_limite, hoy,
                )
                generadas += 1

    # --- Adaptación de condiciones: 20 días hábiles (regla 7) ---------------
    conceptos = ConceptoMedicoOcupacional.objects.filter(
        firmado=True, fecha_recomendacion__isnull=False, seguimiento_completado=False
    ).select_related("atencion__trabajador")
    for c in conceptos:
        vence = sumar_dias_habiles(c.fecha_recomendacion, PLAZO_ADAPTACION_DIAS_HABILES)
        aviso_desde = sumar_dias_habiles(hoy, AVISO_ADAPTACION_DIAS)
        if vence <= aviso_desde:
            estado = "VENCIDO" if hoy > vence else "por vencer"
            _asegurar_alerta(
                "adaptacion", "ConceptoMedicoOcupacional", c.pk,
                f"Adaptación de condiciones de {c.atencion.trabajador} {estado} "
                f"(20 días hábiles; límite {vence}).",
                vence, hoy,
            )
            generadas += 1

    # Cierra alertas cuya referencia ya se resolvió.
    for alerta in Alerta.objects.filter(resuelta=False, tipo__in=["furat", "furel"]):
        modelo = ReporteFURAT if alerta.tipo == "furat" else ReporteFUREL
        if modelo.objects.filter(pk=alerta.referencia_id, estado="enviado").exists():
            alerta.resuelta = True
            alerta.save(update_fields=["resuelta"])
    for alerta in Alerta.objects.filter(resuelta=False, tipo="adaptacion"):
        if ConceptoMedicoOcupacional.objects.filter(
            pk=alerta.referencia_id, seguimiento_completado=True
        ).exists():
            alerta.resuelta = True
            alerta.save(update_fields=["resuelta"])

    return generadas


@shared_task
def revisar_plazos():
    """Recorre todos los tenants y actualiza sus alertas de plazo."""
    hoy = timezone.localdate()
    total = 0
    tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
    for tenant in tenants:
        with schema_context(tenant.schema_name):
            total += _revisar_tenant(hoy)
    return total
