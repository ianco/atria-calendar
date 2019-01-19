from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.signals import user_logged_in, user_logged_out

from indy.error import ErrorCode, IndyError

from .indyutils import open_wallet, close_wallet, get_wallet_name


class IndyBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):
        # Check the username/password and return a user.
        user = super(IndyBackend, self).authenticate(request, username, password)
        if user:
            print(" >>> Authenticated", username, user)
            wallet_handle = None
            if user.wallet_name is not None and user.wallet_name != '':
                try:
                    wallet_handle = open_wallet(user.wallet_name, password)
                    request.session['user_wallet_handle'] = wallet_handle
                    request.session['user_wallet_owner'] = user.email
                    request.session['wallet_name'] = user.wallet_name
                    print(" >>> Opened wallet for", username, wallet_handle)
                except IndyError:
                    # ignore errors for now
                    print(" >>> Failed to open wallet for", username)
                    pass
        else:
            print(" >>> Not authenticated", username)
        return user

    def get_user(self, user_id):
        user = super(IndyBackend, self).get_user(user_id)
        if user:
            print(" >>> Fetched", user_id, user)
        else:
            print(" >>> Not fetched", user_id)
        return user



def indy_wallet_logout(sender, user, request, **kwargs):
    wallet_types = {'user_wallet_handle': 'user_wallet_owner', 'org_wallet_handle': 'org_wallet_owner'}
    for wallet_type in wallet_types:
        if wallet_type in request.session:
            wallet_handle = request.session[wallet_type]
            try:
                close_wallet(wallet_handle)
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

user_logged_out.connect(indy_wallet_logout)


