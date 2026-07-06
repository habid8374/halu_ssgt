from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("atenciones", "0005_remove_trabajador_apellidos_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfiguracionIPS",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("razon_social", models.CharField(blank=True, default="", max_length=200)),
                ("nit", models.CharField(blank=True, default="", max_length=25)),
                ("codigo_habilitacion", models.CharField(blank=True, default="", help_text="Código de habilitación REPS", max_length=40)),
                ("direccion", models.CharField(blank=True, default="", max_length=255)),
                ("ciudad", models.CharField(blank=True, default="", max_length=120)),
                ("telefono", models.CharField(blank=True, default="", max_length=60)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("logo_data_uri", models.TextField(blank=True, default="", help_text="Logo en base64 (data URI).")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración de la IPS",
                "verbose_name_plural": "Configuración de la IPS",
            },
        ),
    ]
