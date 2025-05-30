# Generated by Django 4.2.13 on 2025-04-12 15:15

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('auth_platform', '0005_alter_attlasinsolvencyauthmodel_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttlasInsolvencyAuthConsultantsModel',
            fields=[
                ('language', models.CharField(blank=True, choices=[('es', 'Spanish'), ('en', 'English')], default='es', max_length=4, null=True, verbose_name='language')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='updated')),
                ('is_active', models.BooleanField(default=True, verbose_name='is active')),
                ('default_order', models.PositiveIntegerField(blank=True, default=1, null=True, verbose_name='priority')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100, verbose_name='first name')),
                ('last_name', models.CharField(max_length=100, verbose_name='last name')),
                ('user', models.CharField(blank=True, max_length=15, null=True, unique=True, verbose_name='user')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
            ],
            options={
                'verbose_name': 'ATTLAS Insolvency | Consultants',
                'verbose_name_plural': 'ATTLAS Insolvency | Consultants',
                'db_table': 'apps_project_api_platform_attlas_insolvency_consultants',
                'ordering': ['-created'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='attlasinsolvencyauthmodel',
            unique_together={('document_number_hash', 'birth_date_hash')},
        ),
        migrations.RemoveField(
            model_name='attlasinsolvencyauthmodel',
            name='document_issue_date',
        ),
        migrations.RemoveField(
            model_name='attlasinsolvencyauthmodel',
            name='document_issue_date_hash',
        ),
    ]
