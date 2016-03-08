from django.forms import fields
from td.publishing.widgets import ResourceTypeWidget


class ResourceTypeField(fields.MultiValueField):
    widget = ResourceTypeWidget

    def compress(self, data_list):
        pass
