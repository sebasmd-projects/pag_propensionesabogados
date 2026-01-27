import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.text import slugify

from apps.common.utils.models import TimeStampedModel

class TeamMemberModel(TimeStampedModel):
    """
    Mini-blog por empleado: perfil, resumen, foto y LinkedIn.
    Estable a largo plazo: orden fijo y bandera is_active.
    """
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    full_name = models.CharField(_("full name"), max_length=255)
    role = models.CharField(_("role"), max_length=255)

    slug = models.SlugField(_("slug"), max_length=255, unique=True, blank=True)
    linkedin_url = models.URLField(_("LinkedIn URL"), max_length=500, blank=True, null=True)

    # Texto del mini-blog (resumen + contenido extendido opcional)
    professional_summary = models.TextField(_("professional summary"), blank=True, null=True)
    bio = models.TextField(_("bio (extended)"), blank=True, null=True)

    # Foto (si ya manejas static, puedes dejarlo como ImageField o como ruta static)
    photo = models.ImageField(_("photo"), upload_to="team/", blank=True, null=True)

    # Control estable
    is_active = models.BooleanField(_("is active"), default=True)
    display_order = models.PositiveIntegerField(_("display order"), default=0)

    class Meta:
        db_table = "apps_common_core_team_member"
        verbose_name = _("Team Member")
        verbose_name_plural = _("Team Members")
        ordering = ["display_order", "full_name"]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.full_name)
            candidate = base
            i = 2
            while TeamMemberModel.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{i}"
                i += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("core:team_member_detail", kwargs={"slug": self.slug})

class ContactModel(TimeStampedModel):
    class StatesChoices(models.TextChoices):
        UNATTENDED = 'UNATTENDED', _('Unattended')
        ATTENDED = 'ATTENDED', _('Attended')
        IN_PROGRESS = 'IN_PROGRESS', _('In progress')

    class PageChoices(models.TextChoices):
        PROPENSIONES = 'PROPENSIONES', _('Propensiones')
        ATTLAS = 'ATTLAS', _('Attlas')
        GEA = 'GEA', _('GEA')

    unique_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True
    )

    name = models.CharField(
        _('name'),
        max_length=255
    )

    last_name = models.CharField(
        _('last name'),
        max_length=255
    )

    email = models.EmailField(
        _('email'),
        max_length=255,
    )

    subject = models.CharField(
        _('subject'),
        max_length=255
    )

    message = models.TextField(
        _('message'),
    )

    state = models.CharField(
        _('state'),
        max_length=50,
        choices=StatesChoices.choices,
        default=StatesChoices.UNATTENDED,
        blank=True,
        null=True
    )

    from_page = models.CharField(
        _('from page'),
        max_length=255,
        choices=PageChoices.choices,
        default=PageChoices.PROPENSIONES,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'apps_common_core_contact'
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        ordering = ['-created']

    def __str__(self):
        return self.name


class ModalBannerModel(TimeStampedModel):
    title = models.CharField(
        _('title'),
        max_length=255
    )

    title_en = models.CharField(
        _('title (English)'),
        max_length=255,
        blank=True,
        null=True
    )

    description = models.TextField(
        _('description'),
        blank=True, null=True
    )

    image_file = models.ImageField(
        _('image file'),
        upload_to='modal_banners/'
    )

    image_file_en = models.ImageField(
        _('image file (English)'),
        upload_to='modal_banners/',
        blank=True,
        null=True
    )

    link = models.URLField(
        _('link'),
        max_length=255,
        blank=True,
        null=True
    )

    link_en = models.URLField(
        _('link (English)'),
        max_length=255,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        if self.is_active:
            ModalBannerModel.objects.filter(
                is_active=True
            ).update(
                is_active=False
            )
        return super().save(*args, **kwargs)

    class Meta:
        db_table = 'apps_common_core_modal_banner'
        verbose_name = _('Modal Banner')
        verbose_name_plural = _('Modal Banners')
        ordering = ['-created']

    def __str__(self):
        return self.title
