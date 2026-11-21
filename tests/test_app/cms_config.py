"""cms_config consumer: contributes an independent endpoint (alias-style) and page extensions."""

from django.urls import path

from cms.app_base import CMSAppConfig

from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DemoPageExtension
from .serializers import DemoSeoExtensionSerializer


class DemoAliasView(APIView):
    http_method_names = ("get", "options")

    def get(self, request, language, pk):
        return Response({"id": pk, "language": language, "kind": "demo-alias"})


class DemoAppCMSConfig(CMSAppConfig):
    cms_enabled = False
    djangocms_rest_enabled = True
    cms_rest_endpoints = [
        path(
            "<slug:language>/demo-aliases/<int:pk>/",
            DemoAliasView.as_view(),
            name="demo-alias-detail",
        ),
    ]
    cms_rest_page_extensions = [
        ("seo", DemoSeoExtensionSerializer),  # explicit serializer -> used as is
        ("appearance", DemoPageExtension),  # bare model -> auto-serialized
    ]
