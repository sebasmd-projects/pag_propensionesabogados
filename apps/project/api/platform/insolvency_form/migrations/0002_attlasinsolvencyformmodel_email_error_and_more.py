# Generated by Django 4.2.13 on 2025-04-02 04:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insolvency_form', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attlasinsolvencyformmodel',
            name='email_error',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='attlasinsolvencyformmodel',
            name='email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
