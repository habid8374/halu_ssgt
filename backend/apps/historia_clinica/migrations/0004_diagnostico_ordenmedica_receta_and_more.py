import django.db.models.deletion
import django_cryptography.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("atenciones", "0005_remove_trabajador_apellidos_and_more"),
        ("historia_clinica", "0003_conceptomedicoocupacional_seguimiento_completado_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Campos nuevos de la historia clínica ---
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="antecedentes_laborales",
            field=django_cryptography.fields.encrypt(models.TextField(blank=True)),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="peso_kg",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="talla_cm",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="presion_arterial",
            field=models.CharField(blank=True, default="", help_text="Ej. 120/80", max_length=12),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="frecuencia_cardiaca",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="frecuencia_respiratoria",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="temperatura",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
        migrations.AddField(
            model_name="historiaclinicaocupacional",
            name="saturacion_o2",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
        # --- Diagnóstico codificado ---
        migrations.CreateModel(
            name="Diagnostico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cie10_codigo", models.CharField(max_length=6)),
                ("cie10_desc", models.CharField(max_length=255)),
                ("cie11_codigo", models.CharField(blank=True, default="", max_length=12)),
                ("cie11_desc", models.CharField(blank=True, default="", max_length=255)),
                ("relacion", models.CharField(choices=[("principal", "Principal"), ("relacionado", "Relacionado")], default="principal", max_length=12)),
                ("tipo", models.CharField(choices=[("01", "Impresión diagnóstica"), ("02", "Confirmado nuevo"), ("03", "Confirmado repetido")], default="01", max_length=2)),
                ("observacion", django_cryptography.fields.encrypt(models.TextField(blank=True))),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("historia", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="diagnosticos_cie", to="historia_clinica.historiaclinicaocupacional")),
            ],
            options={
                "verbose_name": "Diagnóstico",
                "verbose_name_plural": "Diagnósticos",
                "ordering": ["relacion", "created_at"],
            },
        ),
        # --- Orden médica ---
        migrations.CreateModel(
            name="OrdenMedica",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("laboratorio", "Laboratorio clínico"), ("imagen", "Imagen diagnóstica"), ("paraclinico", "Otro paraclínico"), ("procedimiento", "Procedimiento"), ("interconsulta", "Interconsulta / remisión"), ("incapacidad", "Incapacidad médica"), ("otro", "Otra orden")], default="laboratorio", max_length=15)),
                ("descripcion", models.CharField(help_text="Estudio, procedimiento o servicio solicitado.", max_length=255)),
                ("codigo_cups", models.CharField(blank=True, default="", help_text="Código CUPS (opcional).", max_length=12)),
                ("cantidad", models.PositiveSmallIntegerField(default=1)),
                ("diagnostico_cie10", models.CharField(blank=True, default="", max_length=6)),
                ("indicaciones", models.TextField(blank=True, default="")),
                ("estado", models.CharField(choices=[("solicitada", "Solicitada"), ("realizada", "Realizada"), ("anulada", "Anulada")], default="solicitada", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("atencion", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordenes", to="atenciones.atencion")),
                ("profesional", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordenes_emitidas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Orden médica",
                "verbose_name_plural": "Órdenes médicas",
                "ordering": ["-created_at"],
            },
        ),
        # --- Receta + medicamentos ---
        migrations.CreateModel(
            name="Receta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("diagnostico_cie10", models.CharField(blank=True, default="", max_length=6)),
                ("observaciones", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("atencion", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recetas", to="atenciones.atencion")),
                ("profesional", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recetas_emitidas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Receta",
                "verbose_name_plural": "Recetas",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MedicamentoRecetado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("medicamento", models.CharField(max_length=200)),
                ("concentracion", models.CharField(blank=True, default="", help_text="Ej. 500 mg", max_length=60)),
                ("forma_farmaceutica", models.CharField(blank=True, default="", help_text="Ej. tableta, jarabe", max_length=60)),
                ("dosis", models.CharField(blank=True, default="", help_text="Ej. 1 tableta", max_length=120)),
                ("via", models.CharField(blank=True, default="", help_text="Ej. oral", max_length=40)),
                ("frecuencia", models.CharField(blank=True, default="", help_text="Ej. cada 8 horas", max_length=60)),
                ("duracion", models.CharField(blank=True, default="", help_text="Ej. 7 días", max_length=60)),
                ("cantidad", models.CharField(blank=True, default="", help_text="Ej. 21 tabletas", max_length=40)),
                ("indicaciones", models.TextField(blank=True, default="")),
                ("receta", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="medicamentos", to="historia_clinica.receta")),
            ],
            options={
                "verbose_name": "Medicamento recetado",
                "verbose_name_plural": "Medicamentos recetados",
            },
        ),
    ]
