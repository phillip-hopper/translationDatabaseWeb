from django.db import models
from django.utils import timezone

from td.models import Language, Country, Network


# ------------- #
#    CHOICES    #
# ------------- #
CHECKING_LEVEL = (
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
)


# ------------- #
#    CHARTER    #
# ------------- #
class Charter(models.Model):

    language = models.OneToOneField(
        Language,
        unique=True,
        verbose_name="Target Language",
    )
    countries = models.ManyToManyField(
        Country,
        verbose_name="Countries that speak this language",
        help_text="Hold Ctrl while clicking to select multiple countries",
    )
    start_date = models.DateField(
        verbose_name="Start Date",
    )
    end_date = models.DateField(
        verbose_name="Projected Completion Date",
    )
    number = models.CharField(
        max_length=10,
        verbose_name="Project Accounting Number",
        blank=True,
    )
    lead_dept = models.ForeignKey(
        "Department",
        verbose_name="Lead Department",
    )
    contact_person = models.CharField(
        max_length=200,
        verbose_name="Follow-up Person",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
    )
    created_by = models.CharField(
        max_length=200,
    )
    modified_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    modified_by = models.CharField(
        max_length=200,
        blank=True,
    )

    def __unicode__(self):
        # Returning the language.name cause encoding error in admin
        return self.language.code.encode("utf-8")

    __unicode__.allow_tags = True
    __unicode__.admin_order_field = "language"

    @property
    def lang_id(self):
        return self.language.id

    @classmethod
    def lang_data(cls):
        return [
            dict(pk=x.language.pk, lc=x.language.lc, ln=x.language.ln, cc=[x.language.cc], lr=x.language.lr)
            for x in cls.objects.all()
        ]


# ----------- #
#    EVENT    #
# ----------- #
class Event(models.Model):

    charter = models.ForeignKey(
        Charter,
        verbose_name="Project Charter",
    )
    number = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
    )
    location = models.CharField(
        max_length=200,
    )
    start_date = models.DateField(
        verbose_name="Start Date",
    )
    end_date = models.DateField(
        verbose_name="End Date",
    )
    lead_dept = models.ForeignKey(
        "Department",
        verbose_name="Lead Department",
        related_name="event_lead_dept",
    )
    output_target = models.ManyToManyField(
        "Output",
        blank=True,
        verbose_name="Output Target"
    )
    publication = models.ManyToManyField(
        "Publication",
        blank=True,
        verbose_name="Distribution Method"
    )
    current_check_level = models.SlugField(
        choices=CHECKING_LEVEL,
        verbose_name="Current Checking Level",
        blank=True,
        null=True,
    )
    target_check_level = models.SlugField(
        choices=CHECKING_LEVEL,
        verbose_name="Anticipated Checking Level",
        blank=True,
        null=True,
    )
    translation_methods = models.ManyToManyField(
        "TranslationMethod",
        blank=True,
        verbose_name="Translation Methodologies",
    )
    software = models.ManyToManyField(
        "Software",
        blank=True,
        verbose_name="Software/App Used",
    )
    hardware = models.ManyToManyField(
        "Hardware",
        blank=True,
        verbose_name="Hardware Used",
    )
    contact_person = models.CharField(
        max_length=200,
    )
    materials = models.ManyToManyField(
        "Material",
        blank=True,
    )
    translators = models.ManyToManyField(
        "Translator",
        blank=True,
    )
    facilitators = models.ManyToManyField(
        "Facilitator",
        blank=True,
    )
    networks = models.ManyToManyField(
        Network,
        blank=True,
    )
    departments = models.ManyToManyField(
        "Department",
        related_name="event_supporting_dept",
        blank=True,
        verbose_name="Supporting Departments",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        null=True,
    )
    created_by = models.CharField(
        max_length=200,
        default="unknown",
    )
    modified_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    modified_by = models.CharField(
        max_length=200,
        blank=True,
    )
    comment = models.TextField(
        blank=True,
    )

    def __unicode__(self):
        return str(self.id)


# ------------------------ #
#    TRANSLATIONSMETHOD    #
# ------------------------ #
class TranslationMethod(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name


# -------------- #
#    SOFTWARE    #
# -------------- #
class Software(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name


# -------------- #
#    HARDWARE    #
# -------------- #
class Hardware(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name


# -------------- #
#    MATERIAL    #
# -------------- #
class Material(models.Model):

    name = models.CharField(
        max_length=200
    )

    licensed = models.BooleanField(
        default=False
    )

    def __unicode__(self):
        return self.name


# ---------------- #
#    TRANSLATOR    #
# ---------------- #
class Translator(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name


# ----------------- #
#    FACILITATOR    #
# ----------------- #
class Facilitator(models.Model):

    name = models.CharField(
        max_length=200
    )

    is_lead = models.BooleanField(
        default=False
    )

    speaks_gl = models.BooleanField(
        default=False
    )

    def __unicode__(self):
        return self.name


# ---------------- #
#    DEPARTMENT    #
# ---------------- #
class Department(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name


# ------------------- #
#    OUTPUT TARGET    #
# ------------------- #
class Output(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name


# ----------------- #
#    PUBLICATION    #
# ----------------- #
class Publication(models.Model):

    name = models.CharField(
        max_length=200
    )

    def __unicode__(self):
        return self.name
