import operator
import re
import urlparse

from django import forms
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, UpdateView, TemplateView, DetailView, FormView

from account.mixins import LoginRequiredMixin

from .forms import (
    CharterForm,
    EventForm,
    MultiCharterStarter,
    MultiCharterEventForm1,
    MultiCharterEventForm2,
)
from .models import (
    Charter,
    Event,
    Facilitator,
    Material,
    Translator,
    TranslationMethod,
    Hardware,
    Software,
    Network,
    Output,
    Publication,
)

from td.utils import DataTableSourceView

from django.core.urlresolvers import reverse as urlReverse

from formtools.wizard.views import SessionWizardView


# ------------------------------- #
#            HOME VIEWS           #
# ------------------------------- #


class CharterTableSourceView(DataTableSourceView):

    @property
    def queryset(self):
        if "pk" in self.kwargs:
            return Charter.objects.filter(language=self.kwargs["pk"])
        else:
            return self.model._default_manager.all()

    @property
    def filtered_data(self):
        if len(self.search_term) and len(self.search_term) <= 3:
            qs = self.queryset.filter(
                reduce(
                    operator.or_,
                    [Q(language__name__istartswith=self.search_term)]
                )
            ).order_by("start_date")
            if qs.count():
                return qs
        return self.queryset.filter(
            reduce(
                operator.or_,
                [Q(x) for x in self.filter_predicates]
            )
        ).order_by(
            self.order_by
        )


class EventTableSourceView(DataTableSourceView):

    @property
    def queryset(self):
        if "pk" in self.kwargs:
            return Event.objects.filter(charter=self.kwargs["pk"])
        else:
            return self.model._default_manager.all()

    @property
    def filtered_data(self):
        if len(self.search_term) and len(self.search_term) <= 3:
            qs = self.queryset.filter(
                reduce(
                    operator.or_,
                    [Q(number__icontains=self.search_term)]
                )
            ).order_by("start_date")
            if qs.count():
                return qs
        return self.queryset.filter(
            reduce(
                operator.or_,
                [Q(x) for x in self.filter_predicates]
            )
        ).order_by(
            self.order_by
        )


class AjaxCharterListView(CharterTableSourceView):
    model = Charter
    fields = [
        "language__name",
        "language__code",
        "start_date",
        "end_date",
        "contact_person"
    ]
    # link is on column because name can"t handle non-roman characters
    link_column = "language__code"
    link_url_name = "language_detail"
    link_url_field = "lang_id"


class AjaxCharterEventsListView(EventTableSourceView):
    model = Event
    fields = [
        "number",
        "location",
        "start_date",
        "end_date",
        "lead_dept__name",
        "contact_person",
    ]
    link_column = "number"
    link_url_name = "tracking:event_detail"
    link_url_field = "pk"


# ---------------------------------- #
#            CHARTER VIEWS           #
# ---------------------------------- #


class CharterAdd(LoginRequiredMixin, CreateView):
    model = Charter
    form_class = CharterForm

    # Overwritten to set initial values
    def get_initial(self):
        return {
            "start_date": timezone.now().date(),
            "created_by": self.request.user.username
        }

    # Overwritten to redirect upon valid submission
    def form_valid(self, form):
        self.object = form.save()
        return redirect("tracking:charter_add_success", obj_type="charter", pk=self.object.id)


class CharterUpdate(LoginRequiredMixin, UpdateView):
    model = Charter
    form_class = CharterForm
    template_name_suffix = "_update_form"

    # Overwritten to redirect upon valid submission
    def form_valid(self, form):
        self.object = form.save()
        return redirect("tracking:charter_add_success", obj_type="charter", pk=self.object.id)


# -------------------------------- #
#            EVENT VIEWS           #
# -------------------------------- #


class EventAddView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm

    # Overwritten to include initial values
    def get_initial(self):
        return {
            "start_date": timezone.now().date(),
            "created_by": self.request.user.username,
        }

    # Overwritten to pass URL argument to forms.py
    def get_form_kwargs(self, **kwargs):
        keywords = super(EventAddView, self).get_form_kwargs(**kwargs)
        if "pk" in self.kwargs:
            keywords["pk"] = self.kwargs["pk"]
        return keywords

    # Overwritten to include custom data
    def get_context_data(self, *args, **kwargs):
        context = super(EventAddView, self).get_context_data(**kwargs)
        context["translators"] = self.get_translator_data(self)
        context["facilitators"] = self.get_facilitator_data(self)
        context["materials"] = self.get_material_data(self)
        return context

    # Overwritten to execute custom save and redirect upon valid submission
    def form_valid(self, form):
        event = self.object = form.save()

        # Add translators info
        translators = self.get_translator_data(self)
        translator_ids = self.get_translator_ids(translators)
        event.translators.add(*list(Translator.objects.filter(id__in=translator_ids)))

        # Add facilitators info
        facilitators = self.get_facilitator_data(self)
        facilitator_ids = self.get_facilitator_ids(facilitators)
        event.facilitators.add(*list(Facilitator.objects.filter(id__in=facilitator_ids)))

        # Add materials info
        materials = self.get_material_data(self)
        material_ids = self.get_material_ids(materials)
        event.materials.add(*list(Material.objects.filter(id__in=material_ids)))

        self.set_event_number()

        new_items = check_for_new_items(event)
        if len(new_items):
            print '\nNEW ITEMS DETECTED IN', new_items
            self.request.session["new_item_info"] = {
                "object": "event",
                "id": [event.id],
                "fields": new_items,
            }
            messages.warning(self.request, "Almost done! Your event has been saved. But...")
            return redirect("tracking:new_item")
        else:
            return redirect("tracking:charter_add_success", obj_type="event", pk=self.object.id)

    # ----------------------------------- #
    #    EVENTADDVIEW CUSTOM FUNCTIONS    #
    # ----------------------------------- #

    # Function: Returns an array of Translator objects' properties
    def get_translator_data(self, form):
        translators = []
        if self.request.POST:
            post = self.request.POST
            for key in sorted(post):
                if key.startswith("translator") and key != "translator-count":
                    name = post[key] if post[key] else ""
                    if name:
                        translators.append({"name": name})
        return translators

    # Function: Returns an array of Facilitator objects' properties
    def get_facilitator_data(self, form):
        facilitators = []
        if self.request.POST:
            post = self.request.POST
            for key in sorted(post):
                if key.startswith("facilitator") and key != "facilitator-count":
                    name = post[key] if post[key] else ""
                    if name:
                        number = key[11:]
                        is_lead = True if "is_lead" + number in post else False
                        speaks_gl = True if "speaks_gl" + number in post else False
                        facilitators.append({"name": name, "is_lead": is_lead, "speaks_gl": speaks_gl})
        return facilitators

    # Function: Returns an array of Material objects' properties
    def get_material_data(self, form):
        materials = []
        if self.request.POST:
            post = self.request.POST
            for key in sorted(post):
                if key.startswith("material") and key != "material-count":
                    name = post[key] if post[key] else ""
                    if name:
                        number = key[8:]
                        licensed = True if "licensed" + number in post else False
                        materials.append({"name": name, "licensed": licensed})
        return materials

    # Function: Takes an array of translator properties and returns an array of their ids
    def get_translator_ids(self, array):
        ids = []
        for translator in array:
            try:
                person = Translator.objects.get(name=translator["name"])
            except Translator.DoesNotExist:
                person = Translator.objects.create(name=translator["name"])
            ids.append(person.id)

        return ids

    # Function: Takes an array of facilitator properties and returns an array of their ids
    def get_facilitator_ids(self, array):
        ids = []
        for facilitator in array:
            try:
                person = Facilitator.objects.get(name=facilitator["name"])
            except Facilitator.DoesNotExist:
                person = Facilitator.objects.create(
                    name=facilitator["name"],
                    is_lead=facilitator["is_lead"],
                    speaks_gl=facilitator["speaks_gl"],
                )
            ids.append(person.id)

        return ids

    # Function: Takes an array of material properties and returns an array of their ids
    def get_material_ids(self, array):
        ids = []
        for material in array:
            try:
                object = Material.objects.get(name=material["name"])
            except Material.DoesNotExist:
                object = Material.objects.create(
                    name=material["name"],
                    licensed=material["licensed"],
                )
            ids.append(object.id)

        return ids

    # Function: Sets property:number in event
    def set_event_number(self):
        events = Event.objects.filter(charter=self.object.charter)
        event_numbers = []
        for event in events:
            event_numbers.append(event.number)
        latest = 0
        for number in event_numbers:
            if number > latest:
                latest = number
        Event.objects.filter(pk=self.object.id).update(number=(latest + 1))


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name_suffix = "_update_form"

    # Overwritten to include custom data
    def get_context_data(self, *args, **kwargs):
        context = super(EventUpdateView, self).get_context_data(**kwargs)
        context["translators"] = self.get_translator_data(self)
        context["facilitators"] = self.get_facilitator_data(self)
        context["materials"] = self.get_material_data(self)
        return context

    # Overwritten to execute custom save and redirect upon valid submission
    def form_valid(self, form):
        event = self.object = form.save()

        # Update translators info
        translators = self.get_translator_data(self)
        translator_ids = self.get_translator_ids(translators)
        event.translators.clear()
        event.translators.add(*list(Translator.objects.filter(id__in=translator_ids)))

        # Add facilitators info
        facilitators = self.get_facilitator_data(self)
        facilitator_ids = self.get_facilitator_ids(facilitators)
        event.facilitators.clear()
        event.facilitators.add(*list(Facilitator.objects.filter(id__in=facilitator_ids)))

        # Add materials info
        materials = self.get_material_data(self)
        material_ids = self.get_material_ids(materials)
        event.materials.clear()
        event.materials.add(*list(Material.objects.filter(id__in=material_ids)))

        return redirect("tracking:charter_add_success", obj_type="event", pk=self.object.id)

    # ----------------------------------- #
    #    EVENTADDVIEW CUSTOM FUNCTIONS    #
    # ----------------------------------- #

    # Function: Returns an array of Translator objects' properties
    def get_translator_data(self, form):
        translators = []
        if self.request.POST:
            post = self.request.POST
            for key in sorted(post):
                if key.startswith("translator") and key != "translator-count":
                    name = post[key] if post[key] else ""
                    if name:
                        translators.append({"name": name})
        else:
            people = Event.objects.get(pk=self.kwargs["pk"]).translators.all()
            for person in people:
                translators.append({"name": person.name})
        return translators

    # Function: Returns an array of Facilitator objects' properties
    def get_facilitator_data(self, form):
        facilitators = []
        if self.request.POST:
            post = self.request.POST
            for key in sorted(post):
                if key.startswith("facilitator") and key != "facilitator-count":
                    name = post[key] if post[key] else ""
                    if name:
                        number = key[11:]
                        is_lead = True if "is_lead" + number in post else False
                        speaks_gl = True if "speaks_gl" + number in post else False
                        facilitators.append({"name": name, "is_lead": is_lead, "speaks_gl": speaks_gl})
        else:
            people = Event.objects.get(pk=self.kwargs["pk"]).facilitators.all()
            for person in people:
                facilitators.append({"name": person.name, "is_lead": person.is_lead, "speaks_gl": person.speaks_gl})
        return facilitators

    # Function: Returns an array of Material objects' properties
    def get_material_data(self, form):
        materials = []
        if self.request.POST:
            post = self.request.POST
            for key in sorted(post):
                if key.startswith("material") and key != "material-count":
                    name = post[key] if post[key] else ""
                    if name:
                        number = key[8:]
                        licensed = True if "licensed" + number in post else False
                        materials.append({"name": name, "licensed": licensed})
        else:
            mats = Event.objects.get(pk=self.kwargs["pk"]).materials.all()
            for mat in mats:
                materials.append({"name": mat.name, "licensed": mat.licensed})
        return materials

    # Function: Takes an array of translator properties and returns an array of their ids
    def get_translator_ids(self, array):
        ids = []
        for translator in array:
            try:
                person = Translator.objects.get(name=translator["name"])
            except Translator.DoesNotExist:
                person = Translator.objects.create(name=translator["name"])
            ids.append(person.id)

        return ids

    # Function: Takes an array of facilitator properties and returns an array of their ids
    def get_facilitator_ids(self, array):
        ids = []
        for facilitator in array:
            try:
                person = Facilitator.objects.get(name=facilitator["name"])
            except Facilitator.DoesNotExist:
                person = Facilitator.objects.create(
                    name=facilitator["name"],
                    is_lead=facilitator["is_lead"],
                    speaks_gl=facilitator["speaks_gl"],
                )
            ids.append(person.id)

        return ids

    # Function: Takes an array of material properties and returns an array of their ids
    def get_material_ids(self, array):
        ids = []
        for material in array:
            try:
                object = Material.objects.get(name=material["name"])
            except Material.DoesNotExist:
                object = Material.objects.create(
                    name=material["name"],
                    licensed=material["licensed"],
                )
            ids.append(object.id)

        return ids


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event

    def get_context_data(self, **kwargs):
        context = super(EventDetailView, self).get_context_data(**kwargs)
        context["event"] = self.object
        return context


# -------------------------------- #
#            OTHER VIEWS           #
# -------------------------------- #


class SuccessView(LoginRequiredMixin, TemplateView):
    template_name = "tracking/charter_add_success.html"

    def get(self, request, *args, **kwargs):
        # Redirects user to tracking home page if he doesn't get here from new
        #    charter or event forms
        try:
            referer = request.META["HTTP_REFERER"]
        except KeyError:
            return redirect("tracking:project_list")

        allowed_urls = [
            re.compile(r"^{}$".format(urlReverse("tracking:charter_add"))),
            re.compile(r"^{}$".format(urlReverse("tracking:charter_update", kwargs={'pk': kwargs["pk"]}))),
            re.compile(r"^{}$".format(urlReverse("tracking:event_add"))),
            re.compile(r"^{}$".format(urlReverse("tracking:event_add_specific", kwargs={'pk': kwargs["pk"]}))),
            re.compile(r"^{}$".format(urlReverse("tracking:event_update", kwargs={'pk': kwargs["pk"]}))),
        ]

        path = urlparse.urlparse(referer).path

        if any(url.match(path) for url in allowed_urls):
            return super(SuccessView, self).get(self, *args, **kwargs)
        else:
            return redirect("tracking:project_list")

    def get_context_data(self, *args, **kwargs):
        # Append additional context to display custom message
        # NOTE: Maybe the logic for custom message should go in the template?
        context = super(SuccessView, self).get_context_data(**kwargs)
        context["link_id"] = kwargs["pk"]
        context["obj_type"] = kwargs["obj_type"]
        context["status"] = "Success"
        if kwargs["obj_type"] == "charter":
            charter = Charter.objects.get(pk=kwargs["pk"])
            context["message"] = "Project " + charter.language.name + " has been successfully added."
        elif kwargs["obj_type"] == "event":
            event = Event.objects.get(pk=kwargs["pk"])
            context["message"] = "Your event for " + event.charter.language.name + " has been successfully added."
        else:
            context["status"] = "Sorry :("
            context["message"] = "It seems like you got here by accident"
        return context


class MultiCharterSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "tracking/multi_charter_success.html"

    def get(self, request, *args, **kwargs):
        # Redirects user to tracking home page if he doesn't get here from new
        #    charter or event forms
        try:
            referer = request.META["HTTP_REFERER"]
        except KeyError:
            return redirect("tracking:project_list")

        allowed_urls = [
            re.compile(r"^{}$".format(urlReverse("tracking:multi_charter_event_add"))),
        ]

        path = urlparse.urlparse(referer).path

        if any(url.match(path) for url in allowed_urls):
            return super(MultiCharterSuccessView, self).get(self, *args, **kwargs)
        else:
            return redirect("tracking:project_list")

    def get_context_data(self, *args, **kwargs):
        # Append additional context to display custom message
        # NOTE: Maybe the logic for custom message should go in the template?
        context = super(MultiCharterSuccessView, self).get_context_data(**kwargs)
        context["charters"] = self.request.session.get("mc-event-succes-charters", [])
        print '\nCONTEXT', context["charters"]
        return context


class MultiCharterEventView(LoginRequiredMixin, SessionWizardView):
    template_name = 'tracking/multi_charter_event_form.html'
    form_list = [MultiCharterStarter, MultiCharterEventForm2]
    success_url = '/success/'
    initial_dict = {
        "1": {"start_date": timezone.now().date()}
    }

    def done(self, form_list, form_dict, **kwargs):
        data = self.get_all_cleaned_data()

        charters = []
        charter_info = []
        for key in data:
            if key.startswith("0-language"):
                # No try..pass because the assumption is user can only select existing project charter
                charters.append(Charter.objects.get(pk=data[key]))

        new_items = []
        ids = []
        for charter in charters:
            event = Event.objects.create(
                charter=charter,
                location=data.get("location"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                lead_dept=data.get("lead_dept"),
                current_check_level=data.get("current_check_level"),
                target_check_level=data.get("target_check_level"),
                contact_person=data.get("contact_person"),
                created_at=timezone.now(),
                created_by=self.request.user.username,
                number=self.get_next_event_number(charter),
            )
            event.save()

            event.hardware.add(*data.get("hardware"))
            event.software.add(*data.get("software"))
            event.networks.add(*data.get("networks"))
            event.departments.add(*data.get("departments"))
            event.translation_methods.add(*data.get("translation_methods"))
            event.publication.add(*data.get("publication"))
            event.output_target.add(*data.get("output_target"))

            facilitators = get_facilitator_data(self)
            facilitator_ids = get_facilitator_ids(facilitators)
            event.facilitators.add(*list(Facilitator.objects.filter(id__in=facilitator_ids)))

            translators = get_translator_data(self)
            translator_ids = get_translator_ids(translators)
            event.translators.add(*list(Translator.objects.filter(id__in=translator_ids)))

            materials = get_material_data(self)
            material_ids = get_material_ids(materials)
            event.materials.add(*list(Material.objects.filter(id__in=material_ids)))

            charter_info.append({"name": charter.language.name, "id": charter.language.id})

            new_items = check_for_new_items(event)
            if len(new_items):
                ids.append(event.id)
        
        if len(new_items):
            self.request.session["new_item_info"] = {
                "object": "event",
                "id": ids,
                "fields": new_items,
            }
            messages.warning(self.request, "Almost done! Your event has been saved. But...")
            return redirect("tracking:new_item")
        else:
            self.request.session["mc-event-succes-charters"] = charter_info
            return redirect("tracking:multi_charter_success")

    def get_context_data(self, form, **kwargs):
        context = super(MultiCharterEventView, self).get_context_data(form=form, **kwargs)
        if self.steps.current == "1":
            context.update({"translators": get_translator_data(self)})
            context.update({"facilitators": get_facilitator_data(self)})
            context.update({"materials": get_material_data(self)})
        return context

    def get_form(self, step=None, data=None, files=None):
        if step == None:
            step = self.steps.current

        if step == '0' and self.request.POST:
            # Create array container for field names
            charter_fields = []
            # Iterate through post data...
            for key in sorted(data):
                # ... to look for our language fields and add them to the array
                if key.startswith("0-language"):
                    charter_fields.append(key)
            # Create a a dictionary of the field name and field definition for every language fields we have
            attrs = dict((field, forms.CharField(
                label="Charter",
                max_length=200,
                widget=forms.TextInput(
                    attrs={
                        "class": "language-selector form-control",
                        "data-source-url": urlReverse("tracking:charters_autocomplete"),
                        "value": data[field],
                    }
                ),
                required=True,
            )) for field in charter_fields)
            # Dynamically create a new Form object with the field definitions
            NewForm = type("NewForm", (MultiCharterEventForm1,), attrs)
            # Bind modified posted data to the new form
            form = NewForm(data)
        else:
            form = super(MultiCharterEventView, self).get_form(step, data, files)

        return form

    def get_next_event_number(self, charter):
        events = Event.objects.filter(charter=charter)
        latest = 0
        for event in events:
            if event.number > latest:
                latest = event.number
        return latest + 1


class NewCharterModalView(CharterAdd):

    template_name = 'tracking/new_charter_modal.html'

    def form_valid(self, form):
        self.object = form.save()
        return render(self.request, "tracking/new_charter_modal.html", {"success": True})


class NewItemView(LoginRequiredMixin, FormView):
    template_name = "tracking/new_item_form.html"

    def get_context_data(self, *args, **kwargs):
        context = super(NewItemView, self).get_context_data(**kwargs)
        context["new_item_info"] = self.request.session.get("new_item_info", [])
        return context

    def get_form(self):
        object = self.get_context_data().get("new_item_info")
        attrs = {}
        for field in object["fields"]:
            attrs[field] = forms.CharField(
                label=self.get_label(field),
                max_length=None,
                widget=forms.TextInput(
                    attrs={
                        "class": "new-items form-control",
                        "data-event": object["id"],
                    }
                ),
                required=False,
            )
        NewItemForm = type("NewItemForm", (forms.Form,), attrs)
        if self.request.POST:
            form = NewItemForm(self.request.POST)
        else:
            form = NewItemForm()
        return form

    def form_valid(self, form):
        self.create_new_item(self.request.session.get("new_item_info"), self.request.POST)
        send_mail(
            'tD New Item',
            'Some new items needs to be added to the event.' + str(self.request.POST),
            'vleong@gmail.com',
            ['vleong2332@gmail.com'],
            fail_silently=False
        )
        messages.success(self.request, "Yes! Your submission info has been updated. If there's any problem with your submission, you'll be contacted via email by the admin.")
        return HttpResponseRedirect(urlReverse("tracking:project_list"))

    def get_label(self, field):
        if field == "translation_methods":
            label = "Translation Methodology"
        elif field == "hardware":
            label = "Hardware Used"
        elif field == "software":
            label = "Software/App used"
        elif field == "networks":
            label = "Network"
        elif field == "output_target":
            label = "Output Target"
        elif field == "publication":
            label = "Publishing Means"
        else:
            label = "Unknown"
        return label

    def create_new_item(self, info, post):
        print '\nCREATING NEW ITEM', info["id"]
        # Start by going through each fields
        for field in info["fields"]:
            # Create a list of cleaned strings from the user input
            data = post[field].split(',')
            for index in range(len(data)):
                data[index] = data[index].rstrip().lstrip().capitalize()
            # Go through each cleaned string, which is the value to be added
            for string in data:
                # Check against empty string
                if len(string):
                    # Determine the field type
                    if field == "translation_methods":
                        # Check to see if item exists first
                        try:
                            new_item = TranslationMethod.objects.get(name=string)
                        # Only create if item doesn't exist
                        except TranslationMethod.DoesNotExist:
                            # Create new item
                            new_item = TranslationMethod.objects.create(name=string)
                        # Go through each id in the list of event ids
                        for id in info["id"]:
                            # Get the event object
                            event = Event.objects.get(pk=id)
                            # Add the new item to the event object to the appropriate field
                            event.translation_methods.add(new_item)
                            # Try to remove the "Other" from the list
                            try:
                                other = event.translation_methods.get(name="Other")
                                event.translation_methods.remove(other)
                            # If no "Other", just pass because it's been deleted
                            except:
                                pass
                    elif field == "hardware":
                        try:
                            new_item = Hardware.objects.get(name=string)
                        except Hardware.DoesNotExist:
                            new_item = Hardware.objects.create(name=string)
                        for id in info["id"]:
                            event = Event.objects.get(pk=id)
                            event.hardware.add(new_item)
                            try:
                                other = event.hardware.get(name="Other")
                                event.hardware.remove(other)
                            except:
                                pass
                    elif field == "software":
                        try:
                            new_item = Software.objects.get(name=string)
                        except Software.DoesNotExist:
                            new_item = Software.objects.create(name=string)
                        for id in info["id"]:
                            event = Event.objects.get(pk=id)
                            event.software.add(new_item)
                            try:
                                other = event.software.get(name="Other")
                                event.software.remove(other)
                            except:
                                pass
                    elif field == "networks":
                        try:
                            new_item = Network.objects.get(name=string)
                        except Network.DoesNotExist:
                            new_item = Network.objects.create(name=string)
                        for id in info["id"]:
                            event = Event.objects.get(pk=id)
                            event.networks.add(new_item)
                            try:
                                other = event.networks.get(name="Other")
                                event.networks.remove(other)
                            except:
                                pass
                    elif field == "output_target":
                        try:
                            new_item = Output.objects.get(name=string)
                        except Output.DoesNotExist:
                            new_item = Output.objects.create(name=string)
                        for id in info["id"]:
                            event = Event.objects.get(pk=id)
                            event.output_target.add(new_item)
                            try:
                                other = event.output_target.get(name="Other")
                                event.output_target.remove(other)
                            except:
                                pass
                    elif field == "publication":
                        try:
                            new_item = Publication.objects.get(name=string)
                        except Publication.DoesNotExist:
                            new_item = Publication.objects.create(name=string)
                        for id in info["id"]:
                            event = Event.objects.get(pk=id)
                            event.publication.add(new_item)
                            try:
                                other = event.publication.get(name="Other")
                                event.publication.remove(other)
                            except:
                                pass
                    else:
                        pass


# -------------------- #
#    VIEW FUNCTIONS    #
# -------------------- #


def charters_autocomplete(request):
    term = request.GET.get("q").lower().encode("utf-8")
    charters = Charter.objects.filter(Q(language__code__icontains=term) | Q(language__name__icontains=term))
    data = [
        {
            "pk": charter.id,
            "ln": charter.language.ln,
            "lc": charter.language.lc,
            "lr": charter.language.lr,
            "gl": charter.language.gateway_flag
        }
        for charter in charters
    ]
    return JsonResponse({"results": data, "count": len(data), "term": term})


def charters_autocomplete_lid(request):
    term = request.GET.get("q").lower().encode("utf-8")
    charters = Charter.objects.filter(Q(language__code__icontains=term) | Q(language__name__icontains=term))
    data = [
        {
            "pk": charter.language.id,
            "ln": charter.language.ln,
            "lc": charter.language.lc,
            "lr": charter.language.lr,
            "gl": charter.language.gateway_flag
        }
        for charter in charters
    ]
    return JsonResponse({"results": data, "count": len(data), "term": term})


def get_translator_data(self):
    translators = []
    if self.request.POST:
        post = self.request.POST
        for key in sorted(post):
            if key.startswith("translator") and key != "translator-count":
                name = post[key] if post[key] else ""
                if name:
                    translators.append({"name": name})
    return translators

# Function: Returns an array of Facilitator objects' properties
def get_facilitator_data(self):
    facilitators = []
    if self.request.POST:
        post = self.request.POST
        for key in sorted(post):
            if key.startswith("facilitator") and key != "facilitator-count":
                name = post[key] if post[key] else ""
                if name:
                    number = key[11:]
                    is_lead = True if "is_lead" + number in post else False
                    speaks_gl = True if "speaks_gl" + number in post else False
                    facilitators.append({"name": name, "is_lead": is_lead, "speaks_gl": speaks_gl})
    return facilitators

# Function: Returns an array of Material objects' properties
def get_material_data(self):
    materials = []
    if self.request.POST:
        post = self.request.POST
        for key in sorted(post):
            if key.startswith("material") and key != "material-count":
                name = post[key] if post[key] else ""
                if name:
                    number = key[8:]
                    licensed = True if "licensed" + number in post else False
                    materials.append({"name": name, "licensed": licensed})
    return materials

# Function: Takes an array of translator properties and returns an array of their ids
def get_translator_ids(array):
    ids = []
    for translator in array:
        try:
            person = Translator.objects.get(name=translator["name"])
        except Translator.DoesNotExist:
            person = Translator.objects.create(name=translator["name"])
        ids.append(person.id)

    return ids

# Function: Takes an array of facilitator properties and returns an array of their ids
def get_facilitator_ids(array):
    ids = []
    for facilitator in array:
        try:
            person = Facilitator.objects.get(name=facilitator["name"])
        except Facilitator.DoesNotExist:
            person = Facilitator.objects.create(
                name=facilitator["name"],
                is_lead=facilitator["is_lead"],
                speaks_gl=facilitator["speaks_gl"],
            )
        ids.append(person.id)

    return ids

# Function: Takes an array of material properties and returns an array of their ids
def get_material_ids(array):
    ids = []
    for material in array:
        try:
            object = Material.objects.get(name=material["name"])
        except Material.DoesNotExist:
            object = Material.objects.create(
                name=material["name"],
                licensed=material["licensed"],
            )
        ids.append(object.id)

    return ids

# 
def check_for_new_items(event):
    fields = []
    if len(event.translation_methods.filter(name="Other")):
        fields.append("translation_methods")
    if len(event.software.filter(name="Other")):
        fields.append("software")
    if len(event.hardware.filter(name="Other")):
        fields.append("hardware")
    if len(event.output_target.filter(name="Other")):
        fields.append("output_target")
    if len(event.publication.filter(name="Other")):
        fields.append("publication")
    return fields
