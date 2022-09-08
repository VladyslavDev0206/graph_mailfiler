# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <UrlConfSnippet>
from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # new
from django.conf.urls.static import static  # new

urlpatterns = [
    path('api/', include('rest_framework.urls')),  # new
    path('', include('mailfiler.urls')),
    path('admin/', admin.site.urls)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# </UrlConfSnippet>
