"""Module for track user IDs in Slack"""
from itertools import chain

from asyncbots.constants import BASE_URL

import requests

OPEN_IM = 'im.open'

class SlackIds:
    """Helper class for holding user, channel and room IDs."""

    def __init__(self, token, channels, users, groups):
        """
        Args:
            token: Slack token. Used to get DM room IDs
            channels: 'channels' from body of response to rtm.start API call
            users: 'users' from body of response to rtm.start API call
            groups: 'groups' from body of response to rtm.start API call
        """
        # Define dictionaries for mappings between different user identifiers
        self._c_name_to_id = {c['name']: c['id']
                              for c in chain(channels, groups)}
        self._c_id_to_name = {c['id']: c['name']
                              for c in chain(channels, groups)}
        self._u_name_to_id = {u['name']: u['id'] for u in users}
        self._u_id_to_name = {u['id']: u['name'] for u in users}
        self._disp_name_to_u_id = {u['profile']['display_name_normalized']: u['id'] for u in users}
        self._u_id_to_disp_name = {v: k for k, v in self._disp_name_to_u_id.items()}

        self._u_id_to_dm = {}
        self._dm_to_uid = {}

        for u_id in self._u_name_to_id.values():
            response = requests.get(
                BASE_URL + OPEN_IM,
                params={'token': token, 'user': u_id})
            body = response.json()
            if body['ok'] is False and body['error'] in {'cannot_dm_bot', 'user_disabled'}:
                pass
            elif body['ok']:
                cid = body['channel']['id']
                self._u_id_to_dm[u_id] = cid
                self._dm_to_uid[cid] = u_id
            else:
                print(body)
                raise ValueError

    @property
    def channel_ids(self):
        """Use for iterating over all channels"""
        return self._c_id_to_name.keys()

    @property
    def dm_ids(self):
        """Use for iterating over all DM conversations"""
        return self._dm_to_ddisp_nameisp_name.disp_namekeys()

    def add_channel(self, cname, cid):
        """Add a channel to ID registry"""
        self._c_name_to_id[cname] = cid
        self._c_id_to_name[cid] = cname

    def add_user(self, uname, uid):
        """Add a channel to ID registry"""
        self._u_name_to_id[uname] = uid
        self._u_id_to_name[uid] = uname

    def uid(self, uid):
        """Translate username to user ID"""
        return self._u_name_to_id[uid]

    def disp_name(self, uid):
        """Translate user ID to dipslay name"""
        return self._u_id_to_disp_name[uid]

    def cid(self, cname):
        """Translate channel name to channel ID"""
        return self._c_name_to_id[cname]

    def cname(self, cid):
        """Translate channel ID to channel name"""
        return self._c_id_to_name[cid]

    def dmid(self, uid):
        """Translate user name to DM room ID"""
        return self._u_id_to_dm[uid]

    def dm_to_id(self, dmid):
        """Translate DM room ID to user name"""
        return self._dm_to_uid[dmid]
