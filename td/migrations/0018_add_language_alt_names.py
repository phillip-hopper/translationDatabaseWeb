# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-02-08 15:53
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('td', '0017_remove_language_alternate_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='language',
            name='alt_names',
            field=models.TextField(blank=True, editable=False),
        ),
        migrations.AlterField(
            model_name='language',
            name='alt_name',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='td.LanguageAltName'),
        ),
    ]