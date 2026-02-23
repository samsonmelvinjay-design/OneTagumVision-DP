# Generated manually for storing progress as float (exact input, no rounding)

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('projeng', '0029_alter_project_prn'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='progress',
            field=models.FloatField(blank=True, default=0, help_text='Project progress in percentage (0-100); decimals allowed', null=True),
        ),
        migrations.AlterField(
            model_name='projectprogress',
            name='percentage_complete',
            field=models.FloatField(
                help_text='Percentage of project completion (0-100); decimals allowed (e.g. 20.25)',
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
    ]
