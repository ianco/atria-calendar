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
    path('check_messages/', check_connection_messages, name='check_messages'),
    path('list_conversations/', list_conversations, name='list_conversations'),
    path('cred_offer_response/', handle_cred_offer_response, name='cred_offer_response'),
    path('proof_req_response/', handle_proof_req_response, name='proof_req_response'),
    path('proof_select_claims/', handle_proof_select_claims, name='proof_select_claims'),
    path('credential_offer/', handle_credential_offer, name='credential_offer'),
    path('proof_request/', handle_proof_request, name='proof_request'),
    path('check_conversation/', poll_conversation_status, name='check_conversation'),
    path('list_credentials/', list_wallet_credentials, name='list_credentials'),
    path('wallet_login/', handle_wallet_login, name='wallet_login'),
    path('wallet_logout/', handle_wallet_logout, name='wallet_logout'),

    path('connections/', VcxConnectionView.as_view()),
#    url(r'^$', schema_view),
]

#urlpatterns = format_suffix_patterns(urlpatterns)
