# Generated by Django 3.0.4 on 2020-03-10 19:40

import django.core.validators
from django.db import migrations, models
import users.models
from users.validators import validate_mxid


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_auto_20200307_1417_squashed_0014_auto_20200308_1414"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="customuser", options={"ordering": ("first_name", "last_name")},
        ),
        migrations.AddField(
            model_name="memberservice",
            name="days_until_suspending",
            field=models.IntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="How many days service can be in payment pending state until it is moved to suspended state",
            ),
        ),
        migrations.AlterField(
            model_name="banktransaction",
            name="message",
            field=models.CharField(
                blank=True,
                help_text="Message attached to transaction by sender. Should not normally be used.",
                max_length=512,
                verbose_name="Message",
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="mxid",
            field=models.CharField(
                help_text="Matrix ID (@user:example.org)",
                max_length=255,
                null=True,
                unique=True,
                validators=[validate_mxid],
                verbose_name="Matrix ID",
            ),
        ),
        migrations.AlterField(
            model_name="memberservice",
            name="days_before_warning",
            field=models.IntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="How many days before payment expiration a warning message shall be sent",
            ),
        ),
        migrations.AlterField(
            model_name="nfccard",
            name="cardid",
            field=models.CharField(
                help_text="Usually hex format",
                max_length=255,
                null=True,
                unique=True,
                verbose_name="NFC card id number as read by the card reader",
            ),
        ),
    ]
