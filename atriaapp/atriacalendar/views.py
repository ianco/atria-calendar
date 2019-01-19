from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone, translation
from django.contrib.auth import login, authenticate
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView

from swingtime import forms as swingtime_forms
from swingtime import views as swingtime_views

import asyncio
import json

from indyconfig.indyutils import create_wallet, open_wallet, get_wallet_name, initialize_and_provision_vcx, send_connection_invitation, send_connection_confirmation, check_connection_status
from indyconfig.indyauth import indy_wallet_logout
from indy.error import ErrorCode, IndyError

from django.conf import settings

from .forms import *
from .models import *


class TranslatedFormMixin(object):
    """
    Mixin that translates just the form for a FormView.

    Uses query_parameter attribute to determine which parameter to use for the
    language (defaults to 'language')
    """

    query_parameter = 'language'

    def set_language(self):
        # Changes the language to the one specified by query_parameter
        self.previous_language = translation.get_language()
        query_language = self.request.GET.get(self.query_parameter)

        if query_language:
            translation.activate(query_language)

    def wrap(self, method, *args, **kwargs):
        # Changes the language, calls the wrapped method, then reverts language.
        self.set_language()

        return_value = method(*args, **kwargs)

        translation.activate(self.previous_language)

        return return_value

    def get_form(self, *args, **kwargs):
        # Wraps .get_form() in query_parameter language context.
        return self.wrap(super().get_form, *args, **kwargs)

    def post(self, *args, **kwargs):
        # Wraps .post() in query_parameter language context.
        return self.wrap(super().post, *args, **kwargs)


####################################################################
# Wrappers around swingtme views:
####################################################################

def atria_year_view(request, year, template='swingtime/yearly_view.html', queryset=None):
    '''

    Context parameters:

    ``year``
        an integer value for the year in questin

    ``next_year``
        year + 1

    ``last_year``
        year - 1

    ``by_month``
        a sorted list of (month, occurrences) tuples where month is a
        datetime.datetime object for the first day of a month and occurrences
        is a (potentially empty) list of values for that month. Only months
        which have at least 1 occurrence is represented in the list

    '''
    return swingtime_views.year_view(request, year, template, queryset)


def atria_month_view(
    request,
    year,
    month,
    template='swingtime/monthly_view.html',
    queryset=None
):
    '''
    Render a tradional calendar grid view with temporal navigation variables.

    Context parameters:

    ``today``
        the current datetime.datetime value

    ``calendar``
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day

    ``this_month``
        a datetime.datetime representing the first day of the month

    ``next_month``
        this_month + 1 month

    ``last_month``
        this_month - 1 month

    '''
    return swingtime_views.month_view(request, year, month, template, queryset)


def atria_day_view(request, year, month, day, template='swingtime/daily_view.html', **params):
    '''
    See documentation for function``_datetime_view``.

    '''
    return swingtime_views.day_view(request, year, month, day, template, **params)


def atria_occurrence_view(
    request,
    event_pk,
    pk,
    template='swingtime/occurrence_detail.html',
    form_class=swingtime_forms.SingleOccurrenceForm
):
    '''
    View a specific occurrence and optionally handle any updates.

    Context parameters:

    ``occurrence``
        the occurrence object keyed by ``pk``

    ``form``
        a form object for updating the occurrence
    '''
    return swingtime_views.occurrence_view(request, event_pk, pk, template, form_class)


def add_atria_event(
    request,
    template='swingtime/add_event.html',
    event_form_class=AtriaEventForm,
    recurrence_form_class=swingtime_forms.MultipleOccurrenceForm
):
    '''
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.

    Context parameters:

    ``dtstart``
        a datetime.datetime object representing the GET request value if present,
        otherwise None

    ``event_form``
        a form object for updating the event

    ``recurrence_form``
        a form object for adding occurrences

    '''
    return swingtime_views.add_event(request, template, event_form_class, recurrence_form_class)


####################################################################
# Atria custom views:
####################################################################

#def login(request):
#    """Shell login view."""
#    return render(request, 'atriacalendar/login.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            print(" >>> registered", username)

            # create an Indy wallet - derive wallet name from email, and re-use raw password
            wallet_name = get_wallet_name(username)
            print(" >>> create", wallet_name)
            wallet_handle = create_wallet(wallet_name, raw_password)
            user.wallet_name = wallet_name
            user.save()

            # provision VCX for this Org/Wallet
            config = initialize_and_provision_vcx(wallet_name, raw_password, username)
            user.vcx_config = config
            user.save()
            print(" >>> created wallet", wallet_name)

            # need to auto-login with Atria custom user
            #login(request, user)

            return redirect('calendar_home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

def calendar_home(request):
    """Home page shell view."""

    return render(request, 'atriacalendar/calendar_home.html',
                  context={'active_view': 'calendar_home'})

def calendar_view(request, *args, **kwargs):
    """Whole Calendar shell view."""

    the_year = kwargs['year']
    the_month = kwargs['month']

    return render(request, 'atriacalendar/calendar_view.html',
                  context={'active_view': 'calendar_view', 'year': the_year, 'month': the_month})

def create_event(request):
    """Create Calendar Event shell view."""

    return render(request, 'atriacalendar/create_event.html',
                  context={'active_view': 'create_event'})

def add_participants(request):
    """Second step of Event creation, adding participants. Shell view."""

    return render(request, 'atriacalendar/add_participants.html')

def event_list(request):
    """List/Manage Calendar Events shell view."""

    return render(request, 'atriacalendar/event_list.html',
                  context={'active_view': 'calendar_list'})

def event_detail(request):
    """Shell view for viewing/editing a single Event."""

    return render(request, 'atriacalendar/event_detail.html')

def event_view(request, pk):
    lang = request.GET.get('event_lang')

    if lang:
        translation.activate(lang)

    return swingtime_views.event_view(request, pk, event_form_class=EventForm,
                                      recurrence_form_class=EventForm)

class EventListView(ListView):
    """
    View for listing all events, or events by type
    """
    model = AtriaEvent
    paginate_by = 25
    context_object_name = 'events'

    def get_queryset(self):
        if 'event_type' in self.kwargs and self.kwargs['event_type']:
            return AtriaEvent.objects.filter(event_type=self.kwargs['event_type'])
        else:
            return AtriaEvent.objects.all()

class EventUpdateView(TranslatedFormMixin, UpdateView):
    """
    View for viewing and updating a single Event.
    """
    form_class = AtriaEventForm
    model = AtriaEvent
    recurrence_form_class = swingtime_forms.MultipleOccurrenceForm
    template_name = 'swingtime/event_detail.html'
    query_parameter = 'event_lang'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)

        if self.form_class == self.recurrence_form_class:
            # There's been a validation error in the recurrence form
            context_data['recurrence_form'] = context_data['form']
            context_data['event_form'] = EventForm(instance=self.object)
        else:
            context_data['recurrence_form'] = self.recurrence_form_class(
                initial={'dstart': timezone.now()})
            context_data['event_form'] = context_data['form']

        return context_data

    def post(self, *args, **kwargs):
        # Selects correct form class based on POST data.
        # NOTE: lifted from swingtime.views.event_view
        if '_update' in self.request.POST:
            return super().post(*args, **kwargs)
        elif '_add' in self.request.POST:
            self.form_class = self.recurrence_form_class
            return super().post(*args, **kwargs)
        else:
            return HttpResponseBadRequest('Bad Request')


# Indy-related views 

def handle_wallet_login(request):
    if request.method=='POST':
        form = WalletLoginForm(request.POST)
        if form.is_valid():
            indy_wallet_logout(None, None, request)
    
            cd = form.cleaned_data

            #now in the object cd, you have the form as a dictionary.
            wallet_name = cd.get('wallet_name')
            raw_password = cd.get('raw_password')

            # get user or org associated with this wallet
            related_user = User.objects.filter(wallet_name=wallet_name).all()
            related_org = AtriaOrganization.objects.filter(wallet_name=wallet_name).all()
            if len(related_user) == 0 and len(related_org) == 0:
                raise Exception('Error wallet with no owner {}'.format(wallet_name))

            # now try to open the wallet
            try:
                wallet_handle = open_wallet(wallet_name, raw_password)

                if len(related_user) > 0:
                    request.session['user_wallet_handle'] = wallet_handle
                    request.session['user_wallet_owner'] = related_user[0].email
                elif len(related_org) > 0:
                    request.session['org_wallet_handle'] = wallet_handle
                    request.session['org_wallet_owner'] = related_org[0].org_name
                request.session['wallet_name'] = wallet_name

                print(" >>> Opened wallet for", wallet_name, wallet_handle)
                return render(request, 'indy/form_response.html', {'msg': 'Opened wallet for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to open wallet for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to open wallet for ' + wallet_name})

    else:
        form = WalletLoginForm()

    return render(request, 'indy/wallet_login.html', {'form': form})

def handle_wallet_logout(request):
    indy_wallet_logout(None, None, request)
    return render(request, 'indy/form_response.html', {'msg': 'Logged out of wallet(s)'})

def handle_connection_request(request):
    if request.method=='POST':
        form = SendConnectionInvitationForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, None, request)
    
            cd = form.cleaned_data

            #now in the object cd, you have the form as a dictionary.
            wallet_name = cd.get('wallet_name')
            raw_password = cd.get('raw_password')
            partner_name = cd.get('partner_name')

            # get user or org associated with this wallet
            related_user = User.objects.filter(wallet_name=wallet_name).all()
            related_org = AtriaOrganization.objects.filter(wallet_name=wallet_name).all()
            if len(related_user) == 0 and len(related_org) == 0:
                raise Exception('Error wallet with no owner {}'.format(wallet_name))

            if 0 < len(related_user):
                vcx_config = related_user[0].vcx_config
                my_name = related_user[0].email
            elif 0 < len(related_org):
                vcx_config = related_org[0].vcx_config
                my_name = related_org[0].org_name

            # get user or org associated with target partner
            target_user = User.objects.filter(email=partner_name).all()
            target_org = AtriaOrganization.objects.filter(org_name=partner_name).all()

            if len(target_user) == 0 and len(target_org) == 0:
                raise Exception('Error requested partner not found {}'.format(partner_name))

            if 0 < len(target_user):
                their_wallet_name = target_user[0].wallet_name
            elif 0 < len(target_org):
                their_wallet_name = target_org[0].wallet_name

            # set wallet password
            # TODO vcx_config['something'] = raw_password

            # build the connection and get the invitation data back
            try:
                (connection_data, invite_data) = send_connection_invitation(json.loads(vcx_config), partner_name)

                my_connection = VcxConnection(
                    wallet_name = wallet_name,
                    partner_name = partner_name,
                    connection_data = json.dumps(connection_data),
                    status = 'Sent')
                my_connection.save()

                their_connection = VcxConnection(
                    wallet_name = their_wallet_name,
                    partner_name = my_name,
                    invitation = json.dumps(invite_data),
                    status = 'Pending')
                their_connection.save()

                print(" >>> Created invite for", wallet_name, partner_name)
                return render(request, 'indy/form_response.html', {'msg': 'Updated connection for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to create request for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to create request for ' + wallet_name})

    else:
        form = SendConnectionInvitationForm()

    return render(request, 'indy/connection_request.html', {'form': form})
    
def handle_connection_response(request):
    if request.method=='POST':
        form = SendConnectionResponseForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, None, request)
    
            cd = form.cleaned_data

            #now in the object cd, you have the form as a dictionary.
            connection_id = cd.get('connection_id')
            wallet_name = cd.get('wallet_name')
            raw_password = cd.get('raw_password')
            partner_name = cd.get('partner_name')
            invitation_details = cd.get('invitation_details')

            # get user or org associated with this wallet
            related_user = User.objects.filter(wallet_name=wallet_name).all()
            related_org = AtriaOrganization.objects.filter(wallet_name=wallet_name).all()
            if len(related_user) == 0 and len(related_org) == 0:
                raise Exception('Error wallet with no owner {}'.format(wallet_name))

            if 0 < len(related_user):
                vcx_config = related_user[0].vcx_config
                my_name = related_user[0].email
            elif 0 < len(related_org):
                vcx_config = related_org[0].vcx_config
                my_name = related_org[0].org_name

            # set wallet password
            # TODO vcx_config['something'] = raw_password

            # build the connection and get the invitation data back
            try:
                connection_data = send_connection_confirmation(json.loads(vcx_config), partner_name, json.loads(invitation_details))

                connections = VcxConnection.objects.filter(id=connection_id).all()
                # TODO validate connection id
                my_connection = connections[0]
                my_connection.connection_data = json.dumps(connection_data)
                my_connection.status = 'Active'
                my_connection.save()

                print(" >>> Updated connection for", wallet_name, partner_name)
                return render(request, 'indy/form_response.html', {'msg': 'Updated connection for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to update request for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to update request for ' + wallet_name})

    else:
        # find connection request
        connection_id = request.GET.get('id', None)
        connections = VcxConnection.objects.filter(id=connection_id).all()
        # TODO validate connection id
        form = SendConnectionResponseForm(initial={ 'connection_id': connection_id,
                                                    'wallet_name': connections[0].wallet_name, 
                                                    'partner_name': connections[0].partner_name, 
                                                    'invitation_details': connections[0].invitation })

    return render(request, 'indy/connection_response.html', {'form': form})
    
def poll_connection_status(request):
    if request.method=='POST':
        form = PollConnectionStatusForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, None, request)
    
            cd = form.cleaned_data

            #now in the object cd, you have the form as a dictionary.
            connection_id = cd.get('connection_id')
            wallet_name = cd.get('wallet_name')
            raw_password = cd.get('raw_password')

            # get user or org associated with this wallet
            related_user = User.objects.filter(wallet_name=wallet_name).all()
            related_org = AtriaOrganization.objects.filter(wallet_name=wallet_name).all()
            if len(related_user) == 0 and len(related_org) == 0:
                raise Exception('Error wallet with no owner {}'.format(wallet_name))

            if 0 < len(related_user):
                vcx_config = related_user[0].vcx_config
            elif 0 < len(related_org):
                vcx_config = related_org[0].vcx_config

            # set wallet password
            # TODO vcx_config['something'] = raw_password

            connections = VcxConnection.objects.filter(id=connection_id).all()
            # TODO validate connection id
            my_connection = connections[0]
            connection_data = my_connection.connection_data

            # validate connection and get the updated status
            try:
                (connection_data, new_status) = check_connection_status(json.loads(vcx_config), json.loads(connection_data))

                connections = VcxConnection.objects.filter(id=connection_id).all()
                # TODO validate connection id
                my_connection = connections[0]
                my_connection.connection_data = json.dumps(connection_data)
                my_connection.status = new_status
                my_connection.save()

                print(" >>> Updated connection for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Updated connection for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to update request for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to update request for ' + wallet_name})

    else:
        # find connection request
        connection_id = request.GET.get('id', None)
        connections = VcxConnection.objects.filter(id=connection_id).all()
        # TODO validate connection id
        form = PollConnectionStatusForm(initial={ 'connection_id': connection_id,
                                                  'wallet_name': connections[0].wallet_name })

    return render(request, 'indy/connection_status.html', {'form': form})

def list_connections(request):
    # expects a wallet to be opened in the current session
    if 'wallet_name' in request.session:
        wallet_name = request.session['wallet_name']
        connections = VcxConnection.objects.filter(wallet_name=wallet_name).all()
        return render(request, 'indy/list_connections.html', {'wallet_name': wallet_name, 'connections': connections})

    return render(request, 'indy/list_connections.html', {'wallet_name': 'No wallet selected', 'connections': []})

def form_response(request):
    msg = request.GET.get('msg', None)
    return render(request, 'indy/form_response.html', {'msg': msg})

