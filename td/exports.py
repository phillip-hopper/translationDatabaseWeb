import json

from django.db import connection

from td.imports.models import EthnologueLanguageCode

from .models import AdditionalLanguage


class Export(object):

    @property
    def additionals(self):
        if not hasattr(self, "_additionals"):
            self._additionals = {
                x.two_letter or x.three_letter or x.ietf_tag: x.native_name or x.common_name
                for x in AdditionalLanguage.objects.all()
            }
        return self._additionals


class LanguageCodesExport(Export):

    def data(self):
        cursor = connection.cursor()
        cursor.execute("""
    select coalesce(nullif(x.part_1, ''), x.code) as code
      from imports_ethnologuelanguagecode lc
 left join imports_sil_iso_639_3 x on x.code = lc.code
     where lc.status = %s order by code;
""", [EthnologueLanguageCode.STATUS_LIVING])
        rows = cursor.fetchall()
        codes = [row[0] for row in rows if row[0] is not None]
        codes.extend(self.additionals.keys())
        codes.sort()
        return codes

    @property
    def text(self):
        return " ".join(self.data()).encode("utf-8")


class LanguageNamesExport(Export):

    def data(self):
        cursor = connection.cursor()
        cursor.execute("""
    select coalesce(nullif(x.part_1, ''), x.code) as code,
           coalesce(nullif(nn1.native_name, ''), nullif(nn2.native_name, ''), x.ref_name) as name,
           coalesce(cc.code, '') as country_code,
           coalesce(cc.area, '') as region
      from imports_ethnologuelanguagecode lc
 left join imports_sil_iso_639_3 x on x.code = lc.code
 left join imports_wikipediaisolanguage nn1 on x.part_1 = nn1.iso_639_1
 left join imports_wikipediaisolanguage nn2 on x.code = nn2.iso_639_3
 left join imports_ethnologuecountrycode cc on lc.country_code = cc.code
     where lc.status = %s order by code;
""", [EthnologueLanguageCode.STATUS_LIVING])
        rows = cursor.fetchall()
        rows.extend([(x[0], x[1], "", "") for x in self.additionals.items()])
        rows.sort()
        for row in rows:
            if len(row) != 4:
                print row
        rows = [
            (
                r[0].encode("utf-8"),
                r[1].encode("utf-8"),
                r[2].encode("utf-8"),
                r[3].encode("utf-8")
            )
            for r in rows
            if r[0] is not None
        ]
        return rows

    @property
    def text(self):
        return "\n".join(["{}\t{}".format(r[0], r[1]) for r in self.data()])

    @property
    def json(self):
        return json.dumps([
            dict(lc=x[0], ln=x[1], cc=[x[2]], lr=x[3])
            for x in self.data()
        ])
