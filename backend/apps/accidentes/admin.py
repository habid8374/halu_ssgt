from django.contrib import admin

from .models import (
    AccidenteTrabajo,
    Alerta,
    InvestigacionAccidente,
    ReporteFUREL,
    ReporteFURAT,
)


@admin.register(AccidenteTrabajo)
class AccidenteAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo_evento", "trabajador", "empresa", "fecha_evento", "gravedad")
    list_filter = ("tipo_evento", "gravedad")


@admin.register(InvestigacionAccidente)
class InvestigacionAdmin(admin.ModelAdmin):
    list_display = ("accidente", "fecha_limite", "completada")


class ReporteAdminBase(admin.ModelAdmin):
    list_display = ("accidente", "estado", "fecha_limite", "enviado_at", "radicado_arl")
    readonly_fields = ("fecha_limite",)


admin.site.register(ReporteFURAT, ReporteAdminBase)
admin.site.register(ReporteFUREL, ReporteAdminBase)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("tipo", "mensaje", "vence", "vencida", "resuelta")
    list_filter = ("tipo", "vencida", "resuelta")
