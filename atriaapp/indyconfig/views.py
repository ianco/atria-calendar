from django.shortcuts import render, redirect
from django.urls import reverse

from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

import asyncio
import json

from .indyutils import create_wallet, open_wallet, get_wallet_name, initialize_and_provision_vcx, send_connection_invitation, send_connection_confirmation, check_connection_status, send_credential_offer, send_credential_request
from .indyauth import indy_wallet_logout, user_wallet_logged_in_handler, user_wallet_logged_out_handler, IndyRestAuthentication
from indy.error import ErrorCode, IndyError

from .forms import *
from .models import *
from .serializers import VcxConnectionSerializer
from atriacalendar.models import User, AtriaOrganization


###########################################
# UI views to support Django web interface
###########################################
def handle_wallet_login(request):
    if request.method=='POST':
        form = WalletLoginForm(request.POST)
        if form.is_valid():
            indy_wallet_logout(None, request.user, request)
    
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

                user_wallet_logged_in_handler(request, request.user, wallet_name)

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
    indy_wallet_logout(None, request.user, request)
    return render(request, 'indy/form_response.html', {'msg': 'Logged out of wallet(s)'})


def handle_connection_request(request):
    if request.method=='POST':
        form = SendConnectionInvitationForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, request.user, request)
    
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
            wallet = IndyWallet.objects.filter(wallet_name=wallet_name).first()

            if 0 < len(related_user):
                vcx_config = wallet.vcx_config
                my_name = related_user[0].email
            elif 0 < len(related_org):
                vcx_config = wallet.vcx_config
                my_name = related_org[0].org_name

            # get user or org associated with target partner
            target_user = User.objects.filter(email=partner_name).all()
            target_org = AtriaOrganization.objects.filter(org_name=partner_name).all()

            #if len(target_user) == 0 and len(target_org) == 0:
            #    raise Exception('Error requested partner not found {}'.format(partner_name))

            if 0 < len(target_user):
                their_wallet_name = target_user[0].wallet_name
            elif 0 < len(target_org):
                their_wallet_name = target_org[0].wallet_name
            else:
                their_wallet_name = None
            if their_wallet_name is not None:
                their_wallet = IndyWallet.objects.filter(wallet_name=their_wallet_name).first()

            # set wallet password
            # TODO vcx_config['something'] = raw_password

            # build the connection and get the invitation data back
            try:
                (connection_data, invite_data) = send_connection_invitation(json.loads(vcx_config), partner_name)

                my_connection = VcxConnection(
                    wallet_name = wallet,
                    partner_name = partner_name,
                    connection_data = json.dumps(connection_data),
                    status = 'Sent')
                my_connection.save()

                if their_wallet_name is not None:
                    their_connection = VcxConnection(
                        wallet_name = their_wallet,
                        partner_name = my_name,
                        invitation = json.dumps(invite_data),
                        status = 'Pending')
                    their_connection.save()

                print(" >>> Created invite for", wallet_name, partner_name)

                handle_wallet_login(request)

                return render(request, 'indy/form_response.html', {'msg': 'Updated connection for ' + wallet_name, 'msg_txt': json.dumps(invite_data)})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to create request for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to create request for ' + wallet_name})

    else:
        if 'wallet_name' in request.session:
            wallet_name = request.session['wallet_name']
        else:
            wallet_name = ''
        form = SendConnectionInvitationForm(initial={'wallet_name': wallet_name})

    return render(request, 'indy/connection_request.html', {'form': form})
    

def handle_connection_response(request):
    if request.method=='POST':
        form = SendConnectionResponseForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, request.user, request)
    
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
            wallet = IndyWallet.objects.filter(wallet_name=wallet_name).first()

            if 0 < len(related_user):
                vcx_config = wallet.vcx_config
                my_name = related_user[0].email
            elif 0 < len(related_org):
                vcx_config = wallet.vcx_config
                my_name = related_org[0].org_name

            # set wallet password
            # TODO vcx_config['something'] = raw_password

            # build the connection and get the invitation data back
            try:
                connection_data = send_connection_confirmation(json.loads(vcx_config), partner_name, json.loads(invitation_details))

                if connection_id is not None and 0 < connection_id:
                    connections = VcxConnection.objects.filter(id=connection_id).all()
                    my_connection = connections[0]
                    my_connection.connection_data = json.dumps(connection_data)
                    my_connection.status = 'Active'
                    my_connection.save()
                else:
                    # external party? build a new VCXConnection pointing to whoever sent this
                    my_connection = VcxConnection(
                        wallet_name = wallet,
                        partner_name = partner_name,
                        invitation = invitation_details,
                        connection_data = json.dumps(connection_data),
                        status = 'Active')
                    my_connection.save()

                print(" >>> Updated connection for", wallet_name, partner_name)

                handle_wallet_login(request)

                return render(request, 'indy/form_response.html', {'msg': 'Updated connection for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to update request for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to update request for ' + wallet_name})

    else:
        # find connection request
        connection_id = request.GET.get('id', None)
        connections = VcxConnection.objects.filter(id=connection_id).all()
        if len(connections) > 0:
            form = SendConnectionResponseForm(initial={ 'connection_id': connection_id,
                                                        'wallet_name': connections[0].wallet_name, 
                                                        'partner_name': connections[0].partner_name, 
                                                        'invitation_details': connections[0].invitation })
        else:
            if 'wallet_name' in request.session:
                wallet_name = request.session['wallet_name']
            else:
                wallet_name = ''
            form = SendConnectionResponseForm(initial={'wallet_name': wallet_name})

    return render(request, 'indy/connection_response.html', {'form': form})
    

def poll_connection_status(request):
    if request.method=='POST':
        form = PollConnectionStatusForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, request.user, request)
    
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
            wallet = IndyWallet.objects.filter(wallet_name=wallet_name).first()

            if 0 < len(related_user):
                vcx_config = wallet.vcx_config
            elif 0 < len(related_org):
                vcx_config = wallet.vcx_config

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

                handle_wallet_login(request)

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


def list_conversations(request):
    # expects a wallet to be opened in the current session
    if 'wallet_name' in request.session:
        wallet_name = request.session['wallet_name']
        conversations = VcxConversation.objects.filter(wallet_name=wallet_name).all()
        return render(request, 'indy/list_conversations.html', {'wallet_name': wallet_name, 'conversations': conversations})

    return render(request, 'indy/list_conversations.html', {'wallet_name': 'No wallet selected', 'conversations': []})


def handle_credential_offer(request):
    if request.method=='POST':
        form = SendCredentialOfferForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, request.user, request)
    
            cd = form.cleaned_data

            #now in the object cd, you have the form as a dictionary.
            connection_id = cd.get('connection_id')
            wallet_name = cd.get('wallet_name')
            raw_password = cd.get('raw_password')
            credential_tag = cd.get('credential_tag')
            cred_def = cd.get('cred_def')
            schema_attrs = cd.get('schema_attrs')
            credential_name = cd.get('credential_name')

            # get user or org associated with this wallet
            related_user = User.objects.filter(wallet_name=wallet_name).all()
            related_org = AtriaOrganization.objects.filter(wallet_name=wallet_name).all()
            if len(related_user) == 0 and len(related_org) == 0:
                raise Exception('Error wallet with no owner {}'.format(wallet_name))
            wallet = IndyWallet.objects.filter(wallet_name=wallet_name).first()

            if 0 < len(related_user):
                vcx_config = wallet.vcx_config
                my_name = related_user[0].email
            elif 0 < len(related_org):
                vcx_config = wallet.vcx_config
                my_name = related_org[0].org_name

            connections = VcxConnection.objects.filter(id=connection_id).all()
            # TODO validate connection id
            my_connection = connections[0]
            connection_data = my_connection.connection_data

            # set wallet password
            # TODO vcx_config['something'] = raw_password

            # build the credential offer and send
            try:
                credential_data = send_credential_offer(wallet, json.loads(vcx_config), json.loads(connection_data), my_connection.partner_name, credential_tag, schema_attrs, cred_def, credential_name)

                my_conversation = VcxConversation(
                    wallet_name = wallet,
                    connection_partner_name = my_connection.partner_name,
                    conversation_type = 'CredentialOffer',
                    message_id = 'N/A',
                    status = 'Sent',
                    conversation_data = json.dumps(credential_data))
                my_conversation.save()

                print(" >>> Updated conversation for", wallet_name, )

                handle_wallet_login(request)

                return render(request, 'indy/form_response.html', {'msg': 'Updated conversation for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to update conversation for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to update conversation for ' + wallet_name})

    else:
        # find conversation request
        connection_id = request.GET.get('connection_id', None)
        connections = VcxConnection.objects.filter(id=connection_id).all()
        schema_attrs = {
            'name': 'alice',
            'date': '05-2018',
            'degree': 'maths',
        }
        # TODO validate connection id
        form = SendCredentialOfferForm(initial={ 'connection_id': connection_id,
                                                 'wallet_name': connections[0].wallet_name,
                                                 'schema_attrs': json.dumps(schema_attrs) })

    return render(request, 'indy/credential_offer.html', {'form': form})


def handle_conversation_response(request):
    if request.method=='POST':
        form = SendCredentialResponseForm(request.POST)
        if form.is_valid():
            # log out of current wallet, if any
            indy_wallet_logout(None, request.user, request)
    
            cd = form.cleaned_data

            wallet_name = cd.get('wallet_name')
            raw_password = cd.get('raw_password')
            conversation_id = cd.get('conversation_id')

            # get user or org associated with this wallet
            related_user = User.objects.filter(wallet_name=wallet_name).all()
            related_org = AtriaOrganization.objects.filter(wallet_name=wallet_name).all()
            if len(related_user) == 0 and len(related_org) == 0:
                raise Exception('Error wallet with no owner {}'.format(wallet_name))
            wallet = IndyWallet.objects.filter(wallet_name=wallet_name).first()

            if 0 < len(related_user):
                vcx_config = wallet.vcx_config
                my_name = related_user[0].email
            elif 0 < len(related_org):
                vcx_config = wallet.vcx_config
                my_name = related_org[0].org_name

            # find conversation request
            conversations = VcxConversation.objects.filter(id=conversation_id).all()
            # TODO validate conversation id
            my_conversation = conversations[0]
            indy_conversation = json.loads(my_conversation.conversation_data)
            connections = VcxConnection.objects.filter(wallet_name=my_conversation.wallet_name, partner_name=my_conversation.connection_partner_name).all()
            # TODO validate connection id
            my_connection = connections[0]

            # build the credential request and send
            try:
                credential_data = send_credential_request(wallet, json.loads(vcx_config), json.loads(my_connection.connection_data), my_connection.partner_name, my_conversation)

                my_conversation.status = 'Sent'
                my_conversation.conversation_data = credential_data
                my_conversation.conversation_type = 'CredentialRequest'
                my_conversation.save()

                print(" >>> Updated conversation for", wallet_name, )

                handle_wallet_login(request)

                return render(request, 'indy/form_response.html', {'msg': 'Updated conversation for ' + wallet_name})
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to update conversation for", wallet_name)
                return render(request, 'indy/form_response.html', {'msg': 'Failed to update conversation for ' + wallet_name})

    else:
        # find conversation request, fill in form details
        conversation_id = request.GET.get('conversation_id', None)
        conversations = VcxConversation.objects.filter(id=conversation_id).all()
        # TODO validate conversation id
        conversation = conversations[0]
        indy_conversation = json.loads(conversation.conversation_data)
        connections = VcxConnection.objects.filter(wallet_name=conversation.wallet_name, partner_name=conversation.connection_partner_name).all()
        # TODO validate connection id
        connection = connections[0]
        form = SendCredentialResponseForm(initial={ 
                                                 'conversation_id': conversation_id,
                                                 'wallet_name': connection.wallet_name,
                                                 'from_partner_name': connection.partner_name,
                                                 'claim_id':indy_conversation['claim_id'],
                                                 'claim_name': indy_conversation['claim_name'],
                                                 'credential_attrs': indy_conversation['credential_attrs'],
                                                 'libindy_offer_schema_id': json.loads(indy_conversation['libindy_offer'])['schema_id']
                                                })

    return render(request, 'indy/conversation_response.html', {'form': form})


def poll_conversation_status(request):
    return render(request, 'indy/form_response.html', {'msg': 'Not yet implemented'})


def form_response(request):
    msg = request.GET.get('msg', None)
    msg_txt = request.GET.get('msg_txt', None)
    return render(request, 'indy/form_response.html', {'msg': msg, 'msg_txt': msg_txt})


###########################################
# API views to support REST services
###########################################
class VcxConnectionView(APIView):
    authentication_classes = (IndyRestAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # TODO filter by wallet_name, which will be in the basic auth header
        wallet = request.user.wallet_name
        connections = VcxConnection.objects.filter(wallet_name=wallet).all()
        # the many param informs the serializer that it will be serializing more than a single article.
        serializer = VcxConnectionSerializer(connections, many=True)
        return Response({"connections": serializer.data})

    def post(self, request):
        # TODO "post" means create an invitation
        connection = request.data.get('connection')

        # Create an article from the above data
        serializer = VcxConnectionSerializer(data=connection)
        if serializer.is_valid(raise_exception=True):
            connection_saved = serializer.save()
        return Response({"success": "Connection '{}' created successfully".format(connection_saved.title)})

    def put(self, request, pk):
        # TODO "put" means update, so either responsd to invitation or poll to get updated status
        saved_connection = get_object_or_404(VcxConnection.objects.all(), pk=pk)
        data = request.data.get('connection')
        serializer = VcxConnectionSerializer(instance=saved_connection, data=data, partial=True)
        if serializer.is_valid(raise_exception=True):
            connection_saved = serializer.save()
        return Response({"success": "Connection '{}' updated successfully".format(connection_saved.title)})

    # TODO don't support delete right now
    #def delete(self, request, pk):
    #    # Get object with this pk
    #    article = get_object_or_404(Article.objects.all(), pk=pk)
    #    article.delete()
    #    return Response({"message": "Article with id `{}` has been deleted.".format(pk)},status=204)
