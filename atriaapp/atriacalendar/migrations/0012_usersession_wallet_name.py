# Generated by Django 2.0.9 on 2019-01-24 16:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atriacalendar', '0011_usersession'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersession',
            name='wallet_name',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
