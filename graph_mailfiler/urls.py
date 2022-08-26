# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <UrlConfSnippet>
from django.contrib import admin
from django.urls import path, include
from mailfiler import views

urlpatterns = [
    path('', include('mailfiler.urls')),
    path('admin/', admin.site.urls)
]
# </UrlConfSnippet>
