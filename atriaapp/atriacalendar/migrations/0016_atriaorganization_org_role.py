# Generated by Django 2.0.9 on 2019-02-01 23:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('atriacalendar', '0015_merge_20190127_1728'),
    ]

    operations = [
        migrations.AddField(
            model_name='atriaorganization',
            name='org_role',
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
