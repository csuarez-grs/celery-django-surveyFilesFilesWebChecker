from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone

# from django.contrib.auth import get_user_model
# User = get_user_model()
from users.models import LDAPUser as User

def get_current_users():
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_id_list = []
    for session in active_sessions:
        data = session.get_decoded()
        user_id_list.append(data.get('_auth_user_id', None))
    # Query all logged in users based on id list

    current_users = User.objects.filter(id__in=user_id_list)

    name_list_str = ', '.join(sorted([str(user.get_username()).title() for user in current_users]))

    return name_list_str
