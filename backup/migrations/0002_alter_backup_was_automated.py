# Generated by Django 4.2.11 on 2025-04-23 23:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backup', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='backup',
            name='was_automated',
            field=models.BooleanField(default=False),
        ),
    ]
