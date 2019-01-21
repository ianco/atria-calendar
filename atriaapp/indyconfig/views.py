from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import VcxConnection
from .serializers import VcxConnectionSerializer
from .indyauth import IndyRestAuthentication


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
