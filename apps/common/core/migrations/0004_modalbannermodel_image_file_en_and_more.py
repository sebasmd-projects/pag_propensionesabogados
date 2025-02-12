# Generated by Django 4.2.7 on 2024-11-27 21:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_modalbannermodel_image_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='modalbannermodel',
            name='image_file_en',
            field=models.ImageField(blank=True, null=True, upload_to='modal_banners/', verbose_name='image file (English)'),
        ),
        migrations.AddField(
            model_name='modalbannermodel',
            name='link_en',
            field=models.URLField(blank=True, max_length=255, null=True, verbose_name='link (English)'),
        ),
        migrations.AddField(
            model_name='modalbannermodel',
            name='title_en',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='title (English)'),
        ),
    ]
