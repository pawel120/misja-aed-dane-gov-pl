from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resources", "0075_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="resource",
            name="contains_aed_list",
            field=models.BooleanField(default=False, verbose_name="Contains AED list"),
        ),
    ]
