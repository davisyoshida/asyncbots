"""Module with helper functions for working with raw Slack API events""" 

def is_message(event, no_channel=False):
    """Check whether an event is a regular message."""
    return ('type' in event and event['type'] == 'message'
            and (no_channel or ('channel' in event and event['channel']))
            and 'text' in event
            and not ('reply_to' in event)
            and 'subtype' not in event
            and event['text'])  # Zero length messages are possible via /giphy command on slack


def is_group_join(event):
    """Check whether an event is the bot joining a group"""
    return 'type' in event and event['type'] == 'group_joined'


def is_team_join(event):
    """Check whether an event is a new user joining the team"""
    return 'type' in event and event['type'] == 'team_join'


def is_response(event):
    """Check whether an event is a response indicating a message was successfully sent"""
    return 'reply_to' in event and 'ok' in event and event['ok']
