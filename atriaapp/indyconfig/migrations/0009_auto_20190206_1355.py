# Generated by Django 2.0.9 on 2019-02-06 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indyconfig', '0008_indyproofrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='indyproofrequest',
            name='proof_req_attrs',
            field=models.TextField(blank=True, max_length=4000),
        ),
        migrations.AddField(
            model_name='indyproofrequest',
            name='proof_req_predicates',
            field=models.TextField(blank=True, max_length=4000),
        ),
    ]