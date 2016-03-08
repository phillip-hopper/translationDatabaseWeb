from __future__ import unicode_literals
from django.forms import widgets
from td.publishing.models import OfficialResourceType, OfficialResourceSubType, ScriptureBook


class ResourceTypeWidget(widgets.MultiWidget):

    def __init__(self, attrs=None):

        resource_types = [(r.short_name, r.long_name) for r in OfficialResourceType.objects.all()]
        resource_subtypes = [(r.short_name, r.long_name) for r in OfficialResourceSubType.objects.all()]
        scripture_books = [(r.short_name, r.long_name) for r in ScriptureBook.objects.all()]

        _widgets = (
            widgets.Select(attrs=attrs, choices=resource_types),
            widgets.Select(attrs=attrs, choices=resource_subtypes),
            widgets.Select(attrs=attrs, choices=scripture_books),
        )
        super(ResourceTypeWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            return [value["resource_type"], value["resource_subtype"], value["scripture_book"]]
        return [None, None, None]
