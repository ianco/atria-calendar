import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.signals import user_logged_in, user_logged_out
from rest_framework.authentication import BasicAuthentication
from rest_framework import exceptions
from rest_framework import authentication

from indy.error import ErrorCode, IndyError

from .indyutils import open_wallet, close_wallet, get_wallet_name
from .models import IndyWallet, IndySession
from .tasks import vcx_agent_background_task


class IndyBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):
        # Check the username/password and return a user.
        print(" >>> Test auth for", username)
        user = super(IndyBackend, self).authenticate(request, username, password)
        if user:
            print(" >>> Authenticated", username, user)
            wallet_handle = None
            if user.wallet_name is not None and user.wallet_name != '':
                try:
                    wallet_handle = open_wallet(user.wallet_name.wallet_name, password)
                    request.session['user_wallet_handle'] = wallet_handle
                    request.session['user_wallet_owner'] = user.email
                    request.session['wallet_name'] = user.wallet_name.wallet_name

                    #user_wallet_logged_in_handler(request, user, user.wallet_name.wallet_name)

                    print(" >>> Opened wallet for", username, wallet_handle)
                except IndyError:
                    # ignore errors for now
                    print(" >>> Failed to open wallet for", username)
                    pass
        else:
            print(" >>> Not authenticated", username)
        return user

    def get_user(self, user_id):
        print(" >>> Fetch user for", user_id)
        user = super(IndyBackend, self).get_user(user_id)
        if user:
            print(" >>> Fetched", user_id, user)
        else:
            print(" >>> Not fetched", user_id)
        return user


class IndyRestAuthentication(BasicAuthentication):

    def authenticate(self, request):
        try:
            # Check for valid basic auth header
            if 'HTTP_AUTHORIZATION' in request.META:
                (authmeth, auth) = request.META['HTTP_AUTHORIZATION'].split(' ',1)
                if authmeth.lower() == "basic":
                    print(auth)
                    auth = base64.b64decode(auth).decode('utf-8')
                    (username, password) = auth.split(':',1)
                    print(username, password)
                    wallet = wallet_authenticate(username=username, password=password)
                    if wallet is not None:
                        user = get_user_model()(wallet_name=wallet, is_active=True)
                        request.user = user
                        return (user, None)  # authentication successful
        except:
            # if we get any exceptions, treat as auth failure
            pass

        raise exceptions.AuthenticationFailed('No credentials provided.')


def wallet_authenticate(username, password):
    # open wallet to validate password
    wallet = IndyWallet.objects.filter(wallet_name=username).first()
    if wallet is not None:
        # this will throw an exception if it fails
        wallet_handle = open_wallet(username, password)
        close_wallet(wallet_handle)

    return wallet


def indy_wallet_logout(sender, user, request, **kwargs):
    wallet_types = {'user_wallet_handle': 'user_wallet_owner', 'org_wallet_handle': 'org_wallet_owner'}
    for wallet_type in wallet_types:
        if wallet_type in request.session:
            wallet_handle = request.session[wallet_type]
            try:
                close_wallet(wallet_handle)
                user_wallet_logged_out_handler(request, user)
                print(" >>> Closed wallet for", wallet_type, wallet_handle)
            except IndyError:
                # ignore errors for now
                print(" >>> Failed to close wallet for", wallet_type, wallet_handle)
                pass
            finally:
                del request.session[wallet_type]
                if wallet_types[wallet_type] in request.session:
                    del request.session[wallet_types[wallet_type]]
                if 'wallet_name' in request.session:
                    del request.session['wallet_name']


def user_wallet_logged_in_handler(request, user, wallet_name):
    print("Login wallet, {} {} {}".format(user.email, request.session.session_key, wallet_name))
    (session, session_created) = IndySession.objects.get_or_create(user=user, session_id=request.session.session_key)
    session.wallet_name = wallet_name
    session.save()

def user_wallet_logged_out_handler(request, user):
    print("Logout wallet, {} {}".format(user.email, request.session.session_key))
    session = IndySession.objects.get(user=user, session_id=request.session.session_key)
    session.wallet_name = None
    session.save()

def user_logged_in_handler(sender, request, user, **kwargs):
    if 'wallet_name' in request.session:
        wallet_name = request.session['wallet_name']
    else:
        wallet_name = None
    print("Login user {} {} {}".format(user.email, request.session.session_key, wallet_name))
    (session, session_created) = IndySession.objects.get_or_create(user=user, session_id=request.session.session_key, wallet_name=wallet_name)
    vcx_agent_background_task("Started by user login", user.id, request.session.session_key, repeat=20)


def user_logged_out_handler(sender, user, request, **kwargs):
    print("Logout user {} {}".format(user.email, request.session.session_key))
    indy_wallet_logout(sender, user, request, **kwargs)
    IndySession.objects.get(user=user, session_id=request.session.session_key).delete()


user_logged_in.connect(user_logged_in_handler)

user_logged_out.connect(user_logged_out_handler)



