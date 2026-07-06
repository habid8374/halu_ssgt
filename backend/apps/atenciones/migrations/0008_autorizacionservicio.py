import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("atenciones", "0007_pruebas"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AutorizacionServicio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("trabajador_documento", models.CharField(db_index=True, max_length=30)),
                ("trabajador_nombre", models.CharField(blank=True, default="", max_length=200)),
                ("tipo_examen", models.CharField(blank=True, choices=[("pre_ingreso", "Pre-ingreso"), ("periodico", "Periódico"), ("egreso", "Egreso"), ("post_incapacidad", "Post-incapacidad"), ("retorno_laboral", "Retorno laboral"), ("seguimiento", "Seguimiento / control")], default="", max_length=20)),
                ("cargo", models.CharField(blank=True, default="", max_length=150)),
                ("numero", models.CharField(blank=True, default="", help_text="N.º de autorización de la empresa.", max_length=40)),
                ("vigencia_hasta", models.DateField(blank=True, null=True)),
                ("estado", models.CharField(choices=[("activa", "Activa"), ("usada", "Usada"), ("vencida", "Vencida"), ("anulada", "Anulada")], default="activa", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("atencion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="autorizaciones_usadas", to="atenciones.atencion")),
                ("creada_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="autorizaciones_creadas", to=settings.AUTH_USER_MODEL)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="autorizaciones", to="atenciones.empresa")),
            ],
            options={"verbose_name": "Autorización de servicio", "verbose_name_plural": "Autorizaciones de servicio", "ordering": ["-created_at"]},
        ),
    ]
