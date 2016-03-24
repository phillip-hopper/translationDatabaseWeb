from django.conf.urls import url
from django.views.generic import TemplateView


from .views import (
    ajax_language_version,
    api_contact,
    ContactList,
    ContactCreate,
    ContactDetail,
    ContactUpdate,
    languages_autocomplete,
    OfficialResourceListView,
    OfficialResourceCreateView,
    OfficialResourceUpdateView,
    OfficialResourceDetailView,
    PublishRequestCreateView,
    PublishRequestUpdateView,
    PublishRequestDeleteView,
    source_languages_autocomplete,
    resource_language_json,
    resource_catalog_json,
    PublishRequestResubmitView,
    ajax_resource_subtypes)


urlpatterns = [
    url(r"^$", TemplateView.as_view(template_name="publishing/homepage.html"), name="publishing_home"),
    url(r"^api/contacts/", api_contact, name="api_contacts"),
    url(r"^contacts/$", ContactList.as_view(), name="contact_list"),
    url(r"^contacts/create/$", ContactCreate.as_view(), name="contact_create"),
    url(r"^contacts/(?P<pk>\d+)/$", ContactDetail.as_view(), name="contact_detail"),
    url(r"^contacts/(?P<pk>\d+)/update/$", ContactUpdate.as_view(), name="contact_update"),
    url(r"^oresource/$", OfficialResourceListView.as_view(), name="oresource_list"),
    url(r"^oresource/create/$", OfficialResourceCreateView.as_view(), name="oresource_create"),
    url(r"^oresource/(?P<pk>\d+)/$", OfficialResourceDetailView.as_view(), name="oresource_detail"),
    url(r"^oresource/(?P<pk>\d+)/update$", OfficialResourceUpdateView.as_view(), name="oresource_update"),
    url(r"^publish/request/$", PublishRequestCreateView.as_view(), name="publish_request"),
    url(r"^publish/request/(?P<pk>\d+)/", PublishRequestUpdateView.as_view(), name="publish_request_update"),
    url(r"^publish/request/(?P<permalink>\w+)/", PublishRequestResubmitView.as_view(), name="publish_request_resubmit"),
    url(r"^publish/request-reject/(?P<pk>\d+)/", PublishRequestDeleteView.as_view(), name="publish_request_delete"),
    url(r"^ac/langnames/", languages_autocomplete, name="names_autocomplete"),
    url(r"^ac/src-langnames/", source_languages_autocomplete, name="source_names_autocomplete"),
    url(r"^ajax/langversion/", ajax_language_version, name="ajax_language_version"),
    url(r"^ajax/resource-subtypes/", ajax_resource_subtypes, name="ajax_resource_subtypes"),
    url(r"^catalog.json$", resource_catalog_json, name="resource_catalog_json"),
    url(r"^(?P<kind>\w+)-catalog.json$", resource_catalog_json, name="resource_catalog_json"),
    url(r"^(?P<kind>\w+)-(?P<lang>\w+).json$", resource_language_json, name="resource_language_json"),
]
