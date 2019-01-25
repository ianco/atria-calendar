import json
from background_task import background

from indy.error import ErrorCode, IndyError

from atriacalendar.models import User

from .models import IndySession, IndyWallet, VcxConnection
from .indyutils import check_connection_status


@background(schedule=5)
def vcx_agent_background_task(message, user_id, session_key, org_id=None):
    print('demo_task. message={0}'.format(message))

    # check if user/wallet has a valid session
    user = User.objects.filter(id=user_id).first()
    session = IndySession.objects.get(user=user, session_id=session_key)

    print("Found session {}  for user {} wallet {}".format(session.id, user.email, session.wallet_name))

    if session.wallet_name is not None:
        wallet = IndyWallet.objects.get(wallet_name=session.wallet_name)

        # check for outstanding connections and poll status
        connections = VcxConnection.objects.filter(wallet_name=wallet, status='Sent').all()

        # if (anything to do) initialize VCX agent and do all our updates
        # TODO (for now each request re-initializes VCX)
        for connection in connections:
            # validate connection and get the updated status
            try:
                (connection_data, new_status) = check_connection_status(json.loads(wallet.vcx_config), json.loads(connection.connection_data))

                connection.connection_data = json.dumps(connection_data)
                connection.status = new_status
                connection.save()

                print(" >>> Updated connection for", session.wallet_name, connection.id, connection.partner_name)
            except IndyError as e:
                print(" >>> Failed to update connection request for", session.wallet_name, connection.id, connection.partner_name)
                raise e

        # TODO check for outstanding, un-received messages - add to outstanding conversations

        # TODO check status of any in-flight conversations (send/receive credential or request/provide proof)


