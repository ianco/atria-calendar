from django.shortcuts import render
from django.http import JsonResponse

from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

import asyncio
import json
import uuid

from indyconfig.models import *
from indyconfig.indyauth import IndyRestAuthentication
from atriacalendar.models import User, AtriaOrganization

from .serializers import VcxConnectionSerializer


###########################################
# API views to support REST services
###########################################
def get_invitation_text(request, token):
    connection = VcxConnection.objects.filter(token=token).first()

    # find owner of the wallet that issued this invitation
    wallet = connection.wallet_name
    related_user = User.objects.filter(wallet_name=wallet.wallet_name).all()
    related_org = AtriaOrganization.objects.filter(wallet_name=wallet.wallet_name).all()
    if len(related_user) == 0 and len(related_org) == 0:
        raise Exception('Error wallet with no owner {}'.format(wallet.wallet_name))

    # TODO for now, fill in proper values later
    if 0 < len(related_user):
        institution_name = related_user[0].email
        name = related_user[0].email
        institution_logo_url = 'http://some.user/logo.url'
    elif 0 < len(related_org):
        institution_name = related_org[0].org_name
        name = related_org[0].org_name
        institution_logo_url = 'http://some.org/logo.url'

    cm_invitation = convertInvite(json.loads(connection.invitation), institution_name, name, institution_logo_url)
    
    return JsonResponse(cm_invitation)

# script from @burdettadam, map to the invite format expected by Connect.Me
def convertInvite(invite, institution_name, name, institution_logo_url):
    cm_invite = { "id": invite["connReqId"],
            "s" :{"d" :invite["senderDetail"]["DID"],
                    "dp":{"d":invite["senderDetail"]["agentKeyDlgProof"]["agentDID"],
                          "k":invite["senderDetail"]["agentKeyDlgProof"]["agentDelegatedKey"],
                          "s":invite["senderDetail"]["agentKeyDlgProof"]["signature"]
                        },
                    "l" :invite["senderDetail"]["logoUrl"],
                    "n" :invite["senderDetail"]["name"],
                    "v" :invite["senderDetail"]["verKey"]
                    },
            "sa":{"d":invite["senderAgencyDetail"]["DID"],
                    "e":invite["senderAgencyDetail"]["endpoint"],
                    "v":invite["senderAgencyDetail"]["verKey"]
                },
            "sc":invite["statusCode"],
            "sm":invite["statusMsg"],
            "t" :invite["targetName"]
            }
    cm_invite["s"]["n"] = institution_name
    cm_invite["t"]      = name
    cm_invite["s"]["l"] = institution_logo_url
    return cm_invite


class VcxConnectionView(APIView):
    authentication_classes = (IndyRestAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # filter by wallet_name, which will be in the basic auth header
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

