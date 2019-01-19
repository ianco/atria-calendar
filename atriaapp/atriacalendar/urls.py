"""
URL configuration for Atria Calendar app.
"""

from django.urls import path, include
from .forms import *
from .views import *


urlpatterns = [
    #path('login/', login, name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', signup_view, name='signup'),

    path('', calendar_home, name='calendar_home'),
    path('calendar/<int:year>/', atria_year_view, name='swingtime-yearly-view'),
    path('calendar/<int:year>/<int:month>/', atria_month_view, name='swingtime-monthly-view'),
    path('calendar/<int:year>/<int:month>/<int:day>/', atria_day_view, name='swingtime-daily-view'),

    path('create-event/', add_atria_event, name='swingtime-add-event'),
    path('create-event/participants/', add_participants, name='add_participants'),
    path('event-list/', EventListView.as_view(), name='event_list'),
    #path('event-detail/', event_detail, name='event_detail'),
    path('event-detail/<int:pk>/', EventUpdateView.as_view(), name='swingtime-event'),
    path('event-detail/<int:event_pk>/<int:pk>/', atria_occurrence_view, name='swingtime-occurrence'),

    path('send_invitation/', handle_connection_request, name='send_invitation'),
    path('list_connections/', list_connections, name='list_connections'),
    path('connection_response/', handle_connection_response, name='connection_response'),
    path('check_connection/', poll_connection_status, name='check_connection'),
    path('form_response/', form_response, name='form_response'),
    path('wallet_login/', handle_wallet_login, name='wallet_login'),
    path('wallet_logout/', handle_wallet_logout, name='wallet_logout'),
]
