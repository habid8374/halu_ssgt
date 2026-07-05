from django.contrib import admin

from .models import Factura, FacturaARL, FacturaItem, TarifaConvenio


@admin.register(TarifaConvenio)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ("empresa", "tipo_examen", "valor")
    list_filter = ("empresa",)


class ItemInline(admin.TabularInline):
    model = FacturaItem
    extra = 0


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ("numero", "empresa", "estado", "total", "periodo_desde", "periodo_hasta")
    list_filter = ("estado",)
    inlines = [ItemInline]


@admin.register(FacturaARL)
class FacturaARLAdmin(admin.ModelAdmin):
    list_display = ("numero", "accidente", "valor", "estado", "cuv")
    readonly_fields = ("rips_json", "cuv")
