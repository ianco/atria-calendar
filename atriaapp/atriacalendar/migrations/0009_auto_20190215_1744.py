# Generated by Django 2.0.10 on 2019-02-15 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atriacalendar', '0008_auto_20190215_1655'),
    ]

    operations = [
        migrations.AlterField(
            model_name='atriaorgannouncement',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='atriarelationship',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
