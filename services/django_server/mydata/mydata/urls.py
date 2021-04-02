"""mydata URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import routers

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

router = routers.DefaultRouter()

if "timeline" in settings.INSTALLED_APPS:
    from timeline import views

    router.register(r"timeline/sources", views.SourceViewSet)
    router.register(r"timeline/events", views.EventViewSet)

if "track" in settings.INSTALLED_APPS:
    from track import views

    router.register(r"track/trackpoints", views.TrackpointViewSet)
    router.register(r"track/tracksegs", views.TracksegViewSet)
    router.register(r"track/trackfiles", views.TrackfileViewSet)

if "logbook" in settings.INSTALLED_APPS:
    from logbook import views

    router.register(r"logbook/messages", views.MessageViewSet)
    router.register(r"logbook/keywords", views.KeywordViewSet)

urlpatterns += [
    path("api/", include(router.urls)),
]
