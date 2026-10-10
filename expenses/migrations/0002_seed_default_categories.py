from django.db import migrations

DEFAULT_CATEGORIES = (
    "Alimentação",
    "Moradia",
    "Transporte",
    "Saúde",
    "Educação",
    "Lazer",
    "Compras",
    "Contas e serviços",
    "Viagens",
    "Impostos",
    "Outros",
)


def seed_default_categories(apps, schema_editor):
    category_model = apps.get_model("expenses", "Category")
    database = schema_editor.connection.alias
    for name in DEFAULT_CATEGORIES:
        category_model.objects.using(database).get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("expenses", "0001_initial")]

    operations = [migrations.RunPython(seed_default_categories, migrations.RunPython.noop)]
