from django.db import models

from cms.extensions import PageContentExtension, PageExtension
from cms.models import CMSPlugin

from djangocms_text.fields import HTMLField
from filer.fields.image import FilerImageField


class SimpleText(models.Model):
    text = HTMLField(blank=True)


class DummyLink(CMSPlugin):
    label = models.TextField()
    page = models.ForeignKey(
        "cms.Page",
        on_delete=models.CASCADE,
        related_name="dummy_links",
        blank=True,
        null=True,
    )

    class Meta:
        abstract = False

    def __str__(self):
        return "dummy link object"


class DummyImage(CMSPlugin):
    image = models.ImageField(upload_to="dummy_images/")
    filer_image = FilerImageField(on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        abstract = False

    def __str__(self):
        return "dummy image object"


class DummySpacer(CMSPlugin):
    class Meta:
        abstract = False

    def __str__(self):
        return "dummy spacer object"


class Pizza(models.Model):
    description = HTMLField()
    allergens = HTMLField(blank=True)


class Topping(models.Model):
    name = models.CharField(max_length=255)
    description = HTMLField()
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE)


class DemoPageExtension(PageExtension):
    """Registered for the API as a bare model (auto-serialized)."""

    theme_color = models.CharField(max_length=7, blank=True)
    featured_pizza = models.ForeignKey(Pizza, on_delete=models.SET_NULL, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)


class DemoPageContentExtension(PageContentExtension):
    """Registered for the API with an explicit serializer."""

    seo_title = models.CharField(max_length=255, blank=True)
