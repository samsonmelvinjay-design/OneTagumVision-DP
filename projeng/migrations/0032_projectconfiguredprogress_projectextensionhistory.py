from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projeng", "0031_edit_history_float"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectExtensionHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_end_date", models.DateField()),
                ("new_end_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extension_history", to="projeng.project")),
                ("set_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="project_extensions_set", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name_plural": "Project Extension History",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ProjectConfiguredProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_date", models.DateField()),
                ("percentage", models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="configured_progress", to="projeng.project")),
                ("set_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="configured_progress_set", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name_plural": "Project Configured Progress",
                "ordering": ["target_date"],
                "unique_together": {("project", "target_date")},
            },
        ),
    ]
