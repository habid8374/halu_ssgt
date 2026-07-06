import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("atenciones", "0006_configuracionips"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PruebaRequerida",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo_prueba", models.CharField(choices=[("medicina", "Evaluación médica ocupacional"), ("visiometria", "Visiometría / Optometría"), ("audiometria", "Audiometría"), ("espirometria", "Espirometría"), ("laboratorio", "Laboratorio clínico"), ("psicologia", "Evaluación psicológica"), ("otro", "Otro paraclínico")], max_length=15)),
                ("detalle", models.CharField(blank=True, default="", help_text="Ej. Cuadro hemático, glicemia.", max_length=150)),
                ("profesiograma", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pruebas", to="atenciones.profesiograma")),
            ],
            options={"verbose_name": "Prueba requerida", "verbose_name_plural": "Pruebas requeridas"},
        ),
        migrations.CreateModel(
            name="PruebaAtencion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo_prueba", models.CharField(choices=[("medicina", "Evaluación médica ocupacional"), ("visiometria", "Visiometría / Optometría"), ("audiometria", "Audiometría"), ("espirometria", "Espirometría"), ("laboratorio", "Laboratorio clínico"), ("psicologia", "Evaluación psicológica"), ("otro", "Otro paraclínico")], max_length=15)),
                ("detalle", models.CharField(blank=True, default="", max_length=150)),
                ("estado", models.CharField(choices=[("pendiente", "Pendiente"), ("en_proceso", "En proceso"), ("realizada", "Realizada"), ("no_aplica", "No aplica")], db_index=True, default="pendiente", max_length=12)),
                ("resultado", models.JSONField(blank=True, default=dict)),
                ("resumen", models.CharField(blank=True, default="", max_length=255)),
                ("archivo", models.FileField(blank=True, null=True, upload_to="pruebas/%Y/%m/")),
                ("realizada_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("atencion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pruebas", to="atenciones.atencion")),
                ("realizada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pruebas_realizadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Prueba de atención", "verbose_name_plural": "Pruebas de atención", "ordering": ["created_at"]},
        ),
    ]
