# Generated by Django 3.0.3 on 2020-02-21 21:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0004_email_slug'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='email',
            name='draft',
        ),
    ]
