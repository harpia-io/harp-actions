import logging
import requests
from actions.settings import USERS_HOST

logger = logging.getLogger('default')


def create_initials(user_info):
    if user_info['first_name'] and user_info['second_name']:
        first_name = user_info['first_name'][0].upper()
        second_name = user_info['second_name'][0].upper()

        return f"{first_name}{second_name}"
    else:
        username = user_info['username'][0:2].upper()

        return username


def get_user_info(username):
    user_info = requests.get(
        f'http://{USERS_HOST}/api/v1/users/user-info/{username}'
    ).json()

    action_by = {
        'id': user_info['user_id'],
        'full_name': f"{user_info['first_name']} {user_info['second_name']}",
        'username': user_info['username'],
        'initials': create_initials(user_info)
    }

    return action_by


def get_user_info_by_id(user_id):
    user_info = requests.get(
        f'http://{USERS_HOST}/api/v1/users/user-info-by-id/{user_id}'
    ).json()

    action_by = {
        'id': user_info['user_id'],
        'full_name': f"{user_info['first_name']} {user_info['second_name']}",
        'username': user_info['username'],
        'initials': create_initials(user_info)
    }

    return action_by
