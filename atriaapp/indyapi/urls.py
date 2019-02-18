from django.urls import path
from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
#from rest_framework_swagger.views import get_swagger_view

from .views import *


#schema_view = get_swagger_view(title='Pastebin API')

app_name = "indyapi"

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('connections/', VcxConnectionView.as_view()),
    path('invitation/<token>/', get_invitation_text, name='invitation'),
#    url(r'^$', schema_view),
]
