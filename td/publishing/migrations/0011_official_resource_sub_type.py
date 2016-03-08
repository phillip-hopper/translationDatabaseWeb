from __future__ import unicode_literals
from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ("publishing", "0010_publishrequest_reject"),
    ]

    # noinspection SqlResolve
    operations = [
        migrations.CreateModel(
            name='OfficialResourceSubType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_name', models.CharField(help_text=b'a 5 character identification code', max_length=5)),
                ('long_name', models.CharField(help_text=b'a more descriptive name', max_length=50)),
            ],
        ),

        migrations.AddField(
            model_name='officialresourcetype',
            name='sub_types',
            field=models.ManyToManyField(to='publishing.OfficialResourceSubType'),
        ),

        migrations.RunSQL(
            "UPDATE publishing_officialresourcetype "
            "SET short_name = 'tn', long_name = 'translationNotes' "
            "WHERE id = 2"),

        migrations.RunSQL(
            "UPDATE publishing_officialresourcetype "
            "SET short_name = 'tw', long_name = 'translationWords' "
            "WHERE id = 3"),

        migrations.RunSQL(
            "UPDATE publishing_officialresourcetype "
            "SET short_name = 'tq', long_name = 'translationQuestions' "
            "WHERE id = 4"),

        migrations.RunSQL(
            "INSERT INTO publishing_officialresourcetype "
            "  (id, short_name, long_name, description) "
            "VALUES "
            "  (6, 'ulb', 'Unlocked Literal Bible', ''), "
            "  (7, 'udb', 'Unlocked Dynamic Bible', '')"),

        migrations.RunSQL(
            "INSERT INTO publishing_officialresourcesubtype "
            "  (id, short_name, long_name) "
            "VALUES "
            "  (1, 'nt', 'New Testament'), "
            "  (2, 'ot', 'Old Testament'), "
            "  (3, 'obs', 'Open Bible Stories'), "
            "  (4, 'vol1', 'Volume 1'), "
            "  (5, 'vol2', 'Volume 2')"),

        migrations.RunSQL(
            # translationAcademy
            "INSERT INTO public.publishing_officialresourcetype_sub_types "
            "  (officialresourcetype_id, officialresourcesubtype_id) "
            "VALUES "
            "  (5, 4), "
            "  (5, 5)"),

        migrations.RunSQL(
            # translationQuestions
            "INSERT INTO public.publishing_officialresourcetype_sub_types "
            "(officialresourcetype_id, officialresourcesubtype_id) "
            "VALUES "
            "  (4, 1), "
            "  (4, 2), "
            "  (4, 3)"),

        migrations.RunSQL(
            # translationNotes
            "INSERT INTO public.publishing_officialresourcetype_sub_types "
            "(officialresourcetype_id, officialresourcesubtype_id) "
            "VALUES "
            "  (2, 1), "
            "  (2, 2), "
            "  (2, 3)"),

        migrations.RunSQL(
            # ULB
            "INSERT INTO public.publishing_officialresourcetype_sub_types "
            "(officialresourcetype_id, officialresourcesubtype_id) "
            "VALUES "
            "  (6, 1), "
            "  (6, 2)"),

        migrations.RunSQL(
            # ULB
            "INSERT INTO public.publishing_officialresourcetype_sub_types "
            "(officialresourcetype_id, officialresourcesubtype_id) "
            "VALUES "
            "  (7, 1), "
            "  (7, 2)"),
    ]
