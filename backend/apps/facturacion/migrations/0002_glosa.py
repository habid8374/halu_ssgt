import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Glosa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(blank=True, default="", help_text="Código de glosa (Res. 3047/2008).", max_length=20)),
                ("descripcion", models.CharField(max_length=255)),
                ("valor", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("estado", models.CharField(choices=[("pendiente", "Pendiente"), ("aceptada", "Aceptada (IPS acepta)"), ("rechazada", "Rechazada (IPS ratifica)"), ("subsanada", "Subsanada"), ("conciliada", "Conciliada / cerrada")], default="pendiente", max_length=12)),
                ("respuesta", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("creada_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="glosas_creadas", to=settings.AUTH_USER_MODEL)),
                ("factura", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="glosas", to="facturacion.factura")),
                ("factura_arl", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="glosas", to="facturacion.facturaarl")),
            ],
            options={"verbose_name": "Glosa", "verbose_name_plural": "Glosas", "ordering": ["-created_at"]},
        ),
    ]
