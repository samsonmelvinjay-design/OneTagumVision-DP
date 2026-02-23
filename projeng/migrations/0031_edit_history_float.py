# Store edit history percentages as float to match ProjectProgress

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projeng', '0030_progress_float'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectprogressedithistory',
            name='from_percentage',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='projectprogressedithistory',
            name='to_percentage',
            field=models.FloatField(),
        ),
    ]
