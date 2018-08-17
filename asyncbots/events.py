"""Module with helper functions for working with raw Slack API events""" 
from functools import partial

def is_message(event, no_channel=False):
    """Check whether an event is a regular message."""
    return ('type' in event and event['type'] == 'message'
            and (no_channel or ('channel' in event and event['channel']))
            and 'text' in event
            and not ('reply_to' in event)
            and 'subtype' not in event
            and 'bot_id' not in event
            and event['text'])  # Zero length messages are possible via /giphy command on slack

def _type_is(e_type, event):
    """Helper function for checking event types"""
    return 'type' in event and event['type'] == e_type

is_group_join = partial(_type_is, 'group_joined') # bot joins new group

is_team_join = partial(_type_is, 'team_join') # New user joins team

is_goodbye = partial(_type_is, 'goodbye') # Server wants to close websocket

def is_response(event):
    """Check whether an event is a response indicating a message was successfully sent"""
    return 'reply_to' in event and 'ok' in event and event['ok']
