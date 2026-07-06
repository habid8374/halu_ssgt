import csv
import gzip
import os

from django.db import migrations, models

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "cups.csv.gz")


def sembrar_cups(apps, schema_editor):
    """Carga el catálogo CUPS oficial (MinSalud/SISPRO) desde el archivo del repo."""
    CodigoCups = apps.get_model("historia_clinica", "CodigoCups")
    if not os.path.exists(DATA):
        return
    objetos = []
    with gzip.open(DATA, "rt", encoding="utf-8", newline="") as gz:
        for fila in csv.reader(gz):
            if len(fila) < 4:
                continue
            codigo, nombre, seccion, activo = fila[0], fila[1], fila[2], fila[3]
            if not codigo or not nombre:
                continue
            objetos.append(CodigoCups(
                codigo=codigo, nombre=nombre, seccion=seccion, activo=(activo == "1"),
            ))
    CodigoCups.objects.bulk_create(objetos, batch_size=2000, ignore_conflicts=True)


def borrar_cups(apps, schema_editor):
    apps.get_model("historia_clinica", "CodigoCups").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("historia_clinica", "0004_diagnostico_ordenmedica_receta_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CodigoCups",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(db_index=True, max_length=10, unique=True)),
                ("nombre", models.CharField(max_length=255)),
                ("seccion", models.CharField(blank=True, default="", max_length=120)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Código CUPS",
                "verbose_name_plural": "Códigos CUPS",
                "ordering": ["codigo"],
            },
        ),
        migrations.RunPython(sembrar_cups, borrar_cups),
    ]
