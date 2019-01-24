from background_task import background

from atriacalendar.models import UserSession, User


@background(schedule=15)
def demo_task(message, user_id, session_key, org_id=None):
    print('demo_task. message={0}'.format(message))

    # check if user/wallet has a valid session
    user = User.objects.filter(id=user_id).first()
    session = UserSession.objects.get(user=user, session_id=session_key)

    print("Found session {}  for user {} wallet {}".format(session.id, user.email, session.wallet_name))
