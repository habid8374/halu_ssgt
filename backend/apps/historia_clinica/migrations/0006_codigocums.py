import csv
import gzip
import os

from django.db import migrations, models

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "cums.csv.gz")


def sembrar_cums(apps, schema_editor):
    """Carga el vademécum CUMS (deduplicado) desde el archivo del repo."""
    CodigoCums = apps.get_model("historia_clinica", "CodigoCums")
    if not os.path.exists(DATA):
        return
    objetos = []
    with gzip.open(DATA, "rt", encoding="utf-8", newline="") as gz:
        for fila in csv.reader(gz):
            if len(fila) < 2:
                continue
            codigo = fila[0].strip()
            nombre = fila[1].strip()
            if not codigo or not nombre:
                continue
            objetos.append(CodigoCums(
                codigo=codigo, nombre=nombre,
                forma_farmaceutica=(fila[2].strip() if len(fila) > 2 else ""),
                via=(fila[3].strip() if len(fila) > 3 else ""),
                atc=(fila[4].strip() if len(fila) > 4 else ""),
                activo=True,
            ))
    CodigoCums.objects.bulk_create(objetos, batch_size=2000, ignore_conflicts=True)


def borrar_cums(apps, schema_editor):
    apps.get_model("historia_clinica", "CodigoCums").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("historia_clinica", "0005_codigocups"),
    ]

    operations = [
        migrations.CreateModel(
            name="CodigoCums",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(db_index=True, help_text="CUM", max_length=20, unique=True)),
                ("nombre", models.CharField(db_index=True, help_text="Denominación genérica (DCI)", max_length=180)),
                ("forma_farmaceutica", models.CharField(blank=True, default="", max_length=80)),
                ("via", models.CharField(blank=True, default="", max_length=40)),
                ("atc", models.CharField(blank=True, default="", max_length=12)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Código CUMS",
                "verbose_name_plural": "Códigos CUMS",
                "ordering": ["nombre", "forma_farmaceutica"],
            },
        ),
        migrations.RunPython(sembrar_cums, borrar_cums),
    ]
