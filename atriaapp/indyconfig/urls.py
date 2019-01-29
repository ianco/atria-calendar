from django.urls import path
from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
#from rest_framework_swagger.views import get_swagger_view

from .views import *


#schema_view = get_swagger_view(title='Pastebin API')

app_name = "indyconfig"

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('send_invitation/', handle_connection_request, name='send_invitation'),
    path('list_connections/', list_connections, name='list_connections'),
    path('connection_response/', handle_connection_response, name='connection_response'),
    path('check_connection/', poll_connection_status, name='check_connection'),
    path('form_response/', form_response, name='form_response'),
    path('list_conversations/', list_conversations, name='list_conversations'),
    path('conversation_response/', handle_conversation_response, name='conversation_response'),
    path('credential_offer/', handle_credential_offer, name='credential_offer'),
    path('check_conversation/', poll_conversation_status, name='check_conversation'),
    path('wallet_login/', handle_wallet_login, name='wallet_login'),
    path('wallet_logout/', handle_wallet_logout, name='wallet_logout'),

    path('connections/', VcxConnectionView.as_view()),
#    url(r'^$', schema_view),
]

#urlpatterns = format_suffix_patterns(urlpatterns)
