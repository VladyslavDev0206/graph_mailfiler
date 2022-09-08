# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register('accounts', views.DropBoxViewset)

urlpatterns = [
  # /
  path('', views.home, name='home'),
  # TEMPORARY
  path('connect', views.connect, name='connect'),
  path('disconnect', views.disconnect, name='disconnect'),
  path('calendar', views.calendar, name='calendar'),
  path('mail', views.mail, name='mail'),
  path('mail/save', views.mailSave, name='saveMail'),
  path('callback', views.callback, name='callback'),
  path('calendar/new', views.newevent, name='newevent'),
  path("register", views.register_request, name="register"),
  path("login", views.login_request, name="login"),
  path("logout", views.logout_request, name= "logout"),
]

urlpatterns.extend(router.urls)
