# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from django.urls import path

from . import views

urlpatterns = [
  # /
  path('', views.home, name='home'),
  # TEMPORARY
  path('connect', views.connect, name='connect'),
  path('disconnect', views.disconnect, name='disconnect'),
  path('calendar', views.calendar, name='calendar'),
  path('mail', views.mail, name='mail'),
  path('callback', views.callback, name='callback'),
  path('calendar/new', views.newevent, name='newevent'),
  path("register", views.register_request, name="register"),
  path("login", views.login_request, name="login"),
  path("logout", views.logout_request, name= "logout"),
]
