from functools import cached_property

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.cms_menus import CMSMenu
from cms.models import Page, PageContent
from cms.utils.i18n import force_language, get_current_language
from menus import base

from rest_framework import serializers

from djangocms_rest.serializers.plugins import GenericPluginSerializer

try:
    from filer.models import File
except ImportError:
    File = None


def get_page_api_endpoint(page, language=None, fallback=True):
    """Get the API endpoint for a given page in a specific language.
    If the page is a home page, return the root endpoint.
    """
    if not language:
        language = get_current_language()

    with force_language(language):
        try:
            if page.is_home:
                return reverse("page-root", kwargs={"language": language})
            path = page.get_path(language, fallback)
            return reverse("page-detail", kwargs={"language": language, "path": path}) if path else None
        except NoReverseMatch:
            return None


def get_file_api_endpoint(file):
    """For a file reference, return the URL of the file if it is public."""
    if not file:
        return None
    return file.url if file.is_public else None


def patch_get_menu_node_for_page_content(method: callable) -> callable:
    def inner(self, page_content: PageContent, *args, **kwargs):
        node = method(self, page_content, *args, **kwargs)
        node.api_endpoint = get_page_api_endpoint(
            page_content.page,
            page_content.language,
        )
        # To save API calls, we add the page's path to the node attributes
        node.attr["path"] = page_content.page.get_path(
            page_content.language,
        )
        return node

    return inner


def patch_page_menu(menu: type[CMSMenu]):
    """Patch the CMSMenu to use the REST API endpoint for pages."""
    if hasattr(menu, "get_menu_node_for_page_content"):
        menu.get_menu_node_for_page_content = patch_get_menu_node_for_page_content(menu.get_menu_node_for_page_content)


class NavigationNodeMixin:
    """Mixin to add API endpoint and selection logic to NavigationNode."""

    api_endpoint = None

    def get_api_endpoint(self):
        """Get the API endpoint for the navigation node."""
        return self.api_endpoint

    def is_selected(self, request):
        """Check if the navigation node is selected."""
        return (
            self.api_endpoint == request.api_endpoint
            if hasattr(request, "api_endpoint")
            else super().is_selected(request)
        )


class NavigationNodeWithAPI(NavigationNodeMixin, base.NavigationNode):
    # NavigationNodeWithAPI must be defined statically at the module level
    # to allow it being pickled for cache
    pass


def add_api_endpoint(navigation_node: type[base.NavigationNode]):
    """Add an API endpoint to the CMSNavigationNode."""
    if not issubclass(navigation_node, NavigationNodeMixin):
        navigation_node = NavigationNodeWithAPI
    return navigation_node


class RESTToolbarMixin:
    """
    Mixin to add REST rendering capabilities to the CMS toolbar.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    if getattr(settings, "REST_JSON_RENDERING", not getattr(settings, "CMS_TEMPLATES", False)):
        try:
            from djangocms_text import settings as text_settings

            text_settings.TEXT_INLINE_EDITING = False
        except ImportError:
            pass

        @cached_property
        def content_renderer(self):
            from .plugin_rendering import RESTRenderer

            return RESTRenderer(request=self.request)


class RESTExtension(CMSAppExtension):
    """Collects REST API extensions contributed by third-party apps.

    A consumer app opts in from its own ``cms_config.py`` by setting
    ``djangocms_rest_enabled = True`` and declaring any of:

    * ``cms_rest_endpoints`` -- a list of url patterns that are mounted under
      the API root. The patterns are expected to be self-contained (including
      any ``<slug:language>/`` prefix), so they are collected as they are.
    * ``cms_rest_page_extensions`` -- a list of ``(name, serializer_or_model)``
      pairs for django CMS page extensions, collected into ``page_extensions``
      (name -> serializer). A bare extension model is auto-serialized.
    """

    def __init__(self):
        self.endpoints = []
        self.page_extensions = {}

    def configure_app(self, cms_config):
        endpoints = getattr(cms_config, "cms_rest_endpoints", None)
        if endpoints:
            self.endpoints.extend(endpoints)
        page_extensions = getattr(cms_config, "cms_rest_page_extensions", None)
        if page_extensions:
            for name, serializer_or_model in page_extensions:
                self.page_extensions[name] = get_page_extension_serializer(serializer_or_model)


def get_page_extension_serializer(serializer_or_model):
    """Use a registered serializer as is, or auto-serialize a bare extension model
    with the ``GenericPluginSerializer`` machinery, so relations resolve to API
    endpoints exactly as they do for plugins."""
    if issubclass(serializer_or_model, serializers.BaseSerializer):
        return serializer_or_model
    return type(
        f"{serializer_or_model.__name__}AutoSerializer",
        (GenericPluginSerializer,),
        {
            "Meta": type("Meta", (), {"model": serializer_or_model, "fields": "__all__"}),
            # Plugin-only field: it reads ``obj.parent``, which extensions do not have.
            "parent_plugin_type": None,
        },
    )


class RESTCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_mixin = RESTToolbarMixin

    Page.add_to_class("get_api_endpoint", get_page_api_endpoint)
    File.add_to_class("get_api_endpoint", get_file_api_endpoint) if File else None

    base.NavigationNode = add_api_endpoint(base.NavigationNode)
    patch_page_menu(CMSMenu)
