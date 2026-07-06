"""
Diagnóstico de Condiciones de Salud (epidemiología agregada) por empresa.

Regla 1/4: la empresa cliente SOLO ve agregados, nunca datos individuales; se
aplica un mínimo de anonimato (no se entrega detalle si hay muy pocos casos).
El coordinador ve el consolidado de cualquier empresa (o de toda la IPS).
"""
from collections import Counter

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.atenciones.models import Atencion, PruebaAtencion
from apps.usuarios.roles import Rol

from .models import ConceptoMedicoOcupacional, Diagnostico

MIN_ANONIMATO = 4
HALLAZGOS = {
    "hipoacusia": "Hipoacusia",
    "trauma acústico": "Trauma acústico",
    "obstructiv": "Patrón obstructivo",
    "restrictiv": "Patrón restrictivo",
    "mixto": "Patrón mixto",
    "alterad": "Agudeza visual alterada",
}


class EpidemiologiaView(APIView):
    """GET /epidemiologia/?empresa=&desde=&hasta="""

    def get(self, request):
        u = request.user
        if not (u and u.is_authenticated and u.rol):
            return Response(status=status.HTTP_403_FORBIDDEN)

        if u.rol == Rol.EMPRESA_CLIENTE:
            empresa_id = u.empresa_id
        elif u.rol == Rol.COORDINADOR:
            empresa_id = request.query_params.get("empresa") or None
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

        atenciones = Atencion.objects.all()
        if empresa_id:
            atenciones = atenciones.filter(empresa_id=empresa_id)
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        if desde:
            atenciones = atenciones.filter(created_at__date__gte=desde)
        if hasta:
            atenciones = atenciones.filter(created_at__date__lte=hasta)

        total = atenciones.count()
        conceptos = ConceptoMedicoOcupacional.objects.filter(atencion__in=atenciones, firmado=True)
        aptitud = dict(Counter(conceptos.values_list("aptitud", flat=True)))

        base = {"total_atenciones": total, "aptitud": aptitud}

        # Mínimo de anonimato para la empresa cliente.
        if u.rol == Rol.EMPRESA_CLIENTE and total < MIN_ANONIMATO:
            base["detalle_restringido"] = True
            base["diagnosticos"] = []
            base["hallazgos"] = []
            base["pruebas"] = []
            return Response(base)

        diags = Counter(
            Diagnostico.objects.filter(historia__atencion__in=atenciones)
            .values_list("cie10_codigo", "cie10_desc")
        )
        base["diagnosticos"] = [
            {"codigo": c, "descripcion": d, "casos": n}
            for (c, d), n in diags.most_common(15)
        ]

        pruebas = PruebaAtencion.objects.filter(atencion__in=atenciones, estado="realizada")
        base["pruebas"] = [
            {"tipo": t, "realizadas": n}
            for t, n in Counter(pruebas.values_list("tipo_prueba", flat=True)).items()
        ]
        # Prevalencia de hallazgos por palabra clave en el resumen.
        hall = Counter()
        for resumen in pruebas.values_list("resumen", flat=True):
            low = (resumen or "").lower()
            for kw, etiqueta in HALLAZGOS.items():
                if kw in low:
                    hall[etiqueta] += 1
        base["hallazgos"] = [{"hallazgo": h, "casos": n} for h, n in hall.most_common()]
        return Response(base)
