# Generated by Django 4.2.13 on 2025-04-20 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('insolvency_form', '0003_attlasinsolvencyincomemodel_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attlasinsolvencycreditorsmodel',
            name='creditor_contact',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Creditor Contact'),
        ),
        migrations.AddField(
            model_name='attlasinsolvencycreditorsmodel',
            name='nit',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='NIT'),
        ),
    ]
