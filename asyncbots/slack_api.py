"""Module for handling interaction with Slack"""
import asyncio
from collections import ChainMap, defaultdict, namedtuple
from itertools import chain
import json
import logging
import os

from pyparsing import ParseException
import requests
import websockets

from asyncbots.command import Command, MessageCommand
from asyncbots.constants import BASE_URL
import asyncbots.events as events
from asyncbots.history import HistoryDoc
from asyncbots.ids import SlackIds
from asyncbots.parsing import SlackParser
from asyncbots.util import handle_async_exception, make_request


logger = logging.getLogger(__name__)

Handler = namedtuple('Handler', ['name', 'func', 'doc', 'channels', 'admin', 'include_timestamp'])


UnfilteredHandler = namedtuple(
    'UnfilteredHandler', ['name', 'func', 'doc', 'channels', 'include_timestamp'])


Handlers = namedtuple('Handlers', ['filtered', 'unfiltered'])


SlackConfig = namedtuple('SlackConfig',
                         ['token', 'name', 'admin_token', 'alert', 'load_history', 'clear_commands', 'admins',  'db'])

DEFAULT_CONFIG = SlackConfig(
    token=None,
    name=None,
    admin_token=None,
    alert='!',
    load_history=False,
    clear_commands=False,
    admins=None,
    db=False)

RTM_START = 'rtm.start'
CHANNEL_HISTORY = 'channels.history'
GROUP_HISTORY = 'groups.history'
IM_HISTORY = 'im.history'
ADD_REACTION = 'reactions.add'
DELETE_CHAT = 'chat.delete'
UPLOAD_FILE = 'files.upload'

TOKEN_ENV = 'SLACK_TOKEN'
NAME_ENV = 'SLACK_BOT_NAME'

class Slack:

    """
    Main class which manages bots and communication with Slack.
    Args:
        config (optional): A SlackConfig object with fields:
            token: A string containing the API key to use for communication with
                Slack.  If not set, it is assumed to be in the SLACK_TOKEN
                environment variable.
            name: The name of the bot user on Slack. This is used to ignore the
                bot as a user.If set incorrectly, unexpected behavior may occur.
            admin_token: A string containing an API key of an admin user account
                on Slack. This is used for deleting messages. If not set,
                deleting messages will be disabled.
            alert: A prefix for filtered commands. Command parsing will only be
                attempted on messages beginning with this prefix, or direct
                messages to the bot user. (Default: '!')
            load_history: If True, bot will dump history database and use the
                web API to load all accessible history. (Default: False)
            clear_commands: If True, on startup bot will delete all of its own
                messages and commands sent it by users in order to unclutter
                chat. (Default: False)
            db: If True, assumes that a connection to MongoDB through mongoengine
                has been established, and will be used to log message history.
                (Default: False)
    """

    def __init__(self, config=None):
        self._config = config if config is not None else DEFAULT_CONFIG

        if self._config.token is None:
            # Try to get token from environment
            if TOKEN_ENV  not in os.environ:
                raise ValueError('Must either provide an API token or set the environment variable {}.'.format(TOKEN_ENV))
            self._config = self._config._replace(token=os.environ[TOKEN_ENV])

        if self._config.name is None:
            if NAME_ENV not in os.environ:
                raise ValueError('Must either provide the name of the bot or set the environment variable {}.'.format(NAME_ENV))
            self._config = self._config._replace(name=os.environ[NAME_ENV])

        self._handlers = Handlers(filtered={}, unfiltered=[])
        self._parser = SlackParser(self._config.alert)
        self._loaded_commands = []
        self._message_id = 0
        self._response_callbacks = {}

        self.ids = None
        self.admins = set()
        self.socket = None

    def preload_commands(self, commands):
        """
        Use this to register commands which will run once Slack connects,
        before the connection exists.
        """
        self._loaded_commands.extend(commands)

    async def connect(self):
        """Connects to Slack, loads IDs, runs preloaded commands and returns the websocket URL."""
        response = requests.get(
            BASE_URL + RTM_START, params={'token': self._config.token})
        try:
            body = response.json()
        except json.decoder.JSONDecodeError as e:
            logger.error('Bad response when connecting to slack. Body:\n%s.', body)
            raise ValueError from e

        self.ids = SlackIds(
            self._config.token, body['channels'], body['users'], body['groups'])

        if self._config.admins is not None:
            for admin_name in self._config.admins:
                self.admins.add(self.ids.uid(admin_name))

        if self._config.load_history and self._config.db:
            await self._load_history()
            self._config = SlackConfig(
                **ChainMap({'load_history': False}, self._config._asdict()))
        if self._config.clear_commands:
            loop = asyncio.get_event_loop()
            loop.create_task(handle_async_exception(self._clear_commands))
            self._config = SlackConfig(
                **ChainMap({'clear_commands': False}, self._config._asdict()))

        return body['url']

    async def run(self):
        """Main loop connects to websocket and listens indefinitely."""
        while True:
            logger.info('Connecting to websocket')
            websocket_url = await self.connect()
            try:
                async with websockets.connect(websocket_url) as self.socket:
                    logger.info('Running %d preloaded commands', len(self._loaded_commands))

                    for command in self._loaded_commands:
                        await self._exhaust_command(command, None)
                    self._loaded_commands = []

                    while True:
                        command = None
                        event = await self._get_event()
                        if 'subtype' not in event or event['subtype'] != 'message_deleted':
                            logger.info('Got event %s', event)
                        if events.is_message(event):
                            await self._handle_message(event)
                        elif events.is_response(event):
                            await self._handle_response(event)
                        elif events.is_group_join(event):
                            cname = event['channel']['name']
                            cid = event['channel']['id']
                            self.ids.add_channel(cname=cname, cid=cid)
                        elif events.is_team_join(event):
                            uname = event['user']['name']
                            uid = event['user']['id']
                            self.ids.add_user(uname=uname, uid=uid)
            except websockets.exceptions.ConnectionClosed:
                logger.info('Websocket closed')

    async def react(self, emoji, event):
        """React to an event"""
        channel = event['channel']
        timestamp = event['ts']
        params = {
            'token': self._config.token,
            'name': emoji,
            'channel': channel,
            'timestamp': timestamp}
        await make_request(BASE_URL + ADD_REACTION, params)

    async def send(self, message, channel, success_callback=None):
        """Send a message to a channel"""
        logger.info('[%s] Sending message: %s', channel, message)
        await self.socket.send(self._make_message(message, channel, success_callback))

    async def store_message(self, user, channel, text, timestamp):
        """Store a message into the history DB"""
        bot_id = self.ids.uid(self._config.name)

        c_name = self.ids.cname(channel)
        if user != bot_id and text and text[0] != self._config.alert:
            HistoryDoc(
                uid=user, channel=c_name, text=text, time=timestamp).save()

    async def upload_file(self, f_name, channel, user):
        """Upload a file to the specified channel or DM"""
        channel = channel if channel else self.ids.dmid(user)
        with open(f_name, 'rb') as f:
            url = BASE_URL + UPLOAD_FILE
            params = {'token': self._config.token,
                      'filetype': f_name.split('.')[-1],
                      'channels': channel,
                      'filename': self._config.name + ' upload'
                     }
            await make_request(url, params, request_type='POST', files={'file': f})

    async def delete_message(self, channel, user, timestamp, admin_key=True):
        """Delete a message."""
        channel = channel if channel else self.ids.dmid(user)
        token = self._config.admin_token if admin_key else self._config.token
        if token is None:
            return
        url = BASE_URL + DELETE_CHAT
        params = {'token': token,
                  'ts': str(timestamp),
                  'channel': channel,
                  'as_user': True}
        await make_request(url, params, request_type='POST')

    def register_handler(self, func, data):
        """
        Registers a function with Slack to be called when certain conditions are
        matched.
        Prefer using asyncbots.bot.register to directly calling this.
        Args:
            func: The function to call
            data: A HandlerData (namedtuple) containing:
                expr: A pyparsing expression.
                      func will be called when it is matched.
                      If expr is None, all messages will be passed to func.
                name: The name of this handler. This is used as the key to store
                    the handler.
                doc: Help text
                priority: Handlers are checked in order of descending priority.
                admin: Whether or not this handler is only accessible to admins
                include_timestamp: Whether the command receives message
                    timestamps
        """
        name, expr, channels, doc, priority, admin, include_ts, unfiltered = data
        if unfiltered:
            uhandler = UnfilteredHandler(name=name,
                                         func=func,
                                         channels=channels,
                                         doc=doc,
                                         include_timestamp=include_ts)
            self._handlers.unfiltered.append(uhandler)
        else:
            self._parser.add_command(expr, name, priority)
            handler = Handler(name=name,
                              func=func,
                              channels=channels,
                              doc=doc,
                              admin=admin,
                              include_timestamp=include_ts)
            self._handlers.filtered[name] = handler

    async def _handle_message(self, event):
        """
        Main logic for dispatching events to bots. Messages in channels are only
        parsed if they begin with self._alert. Messages in DMs are always
        parsed. All unfiltered handlers are applied to messages which are not
        successfully parsed, and are not DMs.
        """
        user = event['user']
        channel = event['channel']
        is_dm = channel[0] == 'D'
        channel_name = None if is_dm else self.ids.cname(channel)

        if is_dm or event['text'][0] == self._config.alert:
            try:
                parsed = self._parser.parse(event['text'], dm=is_dm)
                name, = parsed.keys()
                handler = self._handlers.filtered[name]
            except ParseException:
                parsed = None
            # Only logger.info help message for DMs
            if is_dm and not (parsed and name in self._handlers.filtered):
                command = (MessageCommand(channel=None,
                                          user=user,
                                          text=self._help_message(user))
                           if is_dm else None)
            elif (parsed and
                  (is_dm or handler.channels is None or channel_name in handler.channels)):
                kwargs = {'timestamp': event['ts']} if handler.include_timestamp else {}
                if not handler.admin or user in self.admins:
                    command = await handler.func(user=user,
                                                 in_channel=channel_name,
                                                 parsed=parsed[name], **kwargs)
                else:
                    command = MessageCommand(
                        channel=channel_name, user=user, text='That command is admin only.')
            else:
                command = None

            await self._exhaust_command(command, event)
        else:
            parsed = None

        if not is_dm and parsed is None:
            for handler in self._handlers.unfiltered:
                if (handler.channels is None
                        or channel_name in handler.channels):
                    kwargs = {'timestamp': event['ts']} if handler.include_timestamp else {}
                    command = await handler.func(
                        user=user,
                        in_channel=channel_name,
                        message=event['text'],
                        **kwargs)
                    await self._exhaust_command(command, event)

            if self._config.db:
                await self.store_message(
                    user=user,
                    channel=channel,
                    text=event['text'],
                    timestamp=event['ts'])

    async def _handle_response(self, event):
        """
        Handles responses from Slack server to sent messages.  Executes any
        callbacks with the corresponding message ID then removes them from the
        _response_callback map.
        """
        rt = event["reply_to"]
        if rt in self._response_callbacks:
            cb, ch = self._response_callbacks[rt]
            event["channel"] = ch
            await self._exhaust_command(cb(), event)
            del self._response_callbacks[rt]

    async def _exhaust_command(self, command, event):
        """Run a command, any commands that generates and so on until None is
        returned. Commands are executed depth first."""
        # Command may either be a single Command or list[Command]
        if not command:
            return
        stack = [command] if isinstance(command, Command) else [c for c in command]
        while stack:
            next_command = stack.pop()
            new_command = await next_command.execute(self, event)
            if isinstance(new_command, Command):
                stack.append(new_command)
            elif isinstance(new_command, list):
                stack.extend(new_command)

    async def _get_event(self):
        """Get a JSON event from the websocket and convert it to a dict"""
        event = await self.socket.recv()
        return json.loads(event)

    async def _get_history(self, include_dms=False):
        """
        Helper for iterating over all messages in Slack's history via the web
        API.
        """
        found_messages = 0
        channels = chain(
            self.ids.channel_ids, self.ids.dm_ids if include_dms else [])
        past_events = defaultdict(list)
        for channel in channels:
            channel_name = (self.ids.cname if channel[0] in ('C', 'G') else
                            self.ids.dmname)(channel)
            logger.info('Getting history for channel: %s', channel_name)

            url = BASE_URL +\
                (CHANNEL_HISTORY if channel[0] == 'C' else
                 GROUP_HISTORY if channel[0] == 'G' else IM_HISTORY)

            latest = float('inf')
            has_more = True
            params = {'token': self._config.token,
                      'channel': channel,
                      'inclusive': False}
            seen_timestamps = set() # Inclusive flag seems to be ignored
            while has_more:
                await asyncio.sleep(1)
                data = await make_request(
                    url,
                    params=params
                )
                if 'has_more' not in data:
                    logger.info('has_more not in data')
                    logger.info(data)
                    logger.info(channel)
                    logger.info(self.ids.cname(channel))
                    exit()
                has_more = data['has_more']
                messages = data['messages']
                for message in messages:
                    if events.is_message(message, no_channel=True) and message['ts'] not in seen_timestamps:
                        past_events[channel].append(message)
                        seen_timestamps.add(message['ts'])
                        latest = min(float(message['ts']), latest)
                params['latest'] = latest
                found_messages += len(messages)
                logger.info('Found %d messages', found_messages)
        return past_events

    async def _load_history(self):
        """
        Wipe the existing history and load the Slack message archive into the
        database
        """
        HistoryDoc.objects().delete()
        logger.info('History Cleared')
        past_events = await self._get_history()
        for channel, messages in past_events.items():
            for message in messages:
                try:
                    await self.store_message(
                        channel=channel,
                        user=message['user'],
                        text=message['text'],
                        timestamp=message['ts'])
                except KeyError:
                    logger.info([k for k in message])
                    exit()

    async def _clear_commands(self):
        """
        Loop over all messages in Slack and delete them if they are a valid
        command, or send by the bot user. Requires admin_key to be set.
        """
        to_delete = []
        bot_id = self.ids.uid(self._config.name)
        past_events = await self._get_history(include_dms=True)
        for channel, messages in past_events.items():
            for message in messages:
                admin_key = True
                if message['user'] == bot_id:
                    admin_key = False
                elif channel[0] != 'D':
                    try:
                        self._parser.parse(
                            message['text'], dm=channel[0] == 'D')
                    except ParseException:
                        continue
                else:
                    continue
                to_delete.append(
                    ((channel, message['user'], message['ts']), admin_key))

        logger.info('Found %d messages to delete', len(to_delete))
        for i, (args, admin_key) in enumerate(to_delete, 1):
            await asyncio.sleep(1)
            await self.delete_message(*args, admin_key=admin_key)
            if i % 100 == 0:
                logger.info('Deleted %d messages so far', i)

    def _make_message(self, text, channel_id, response_callback):
        """
        Build a JSON message & register callback if provided. The callback will
        be executed on the event corresponding to this message."""
        m_id, self._message_id = self._message_id, self._message_id + 1
        # register callback for when response is received indicating successful message post
        # need to save channel as well, since that isn't provided in response
        # event
        if response_callback:
            self._response_callbacks[m_id] = (response_callback, channel_id)
        return json.dumps({'id': m_id,
                           'type': 'message',
                           'channel': channel_id,
                           'text': text})

    def _help_message(self, uid):
        """Iterate over all handlers and join their help texts into one message."""
        res = []
        for handler in self._handlers.filtered.values():
            if handler.doc and (not handler.admin or uid in self.admins):
                res.append('{}:'.format(handler.name))
                res.append('\t{}'.format(handler.doc))
                res.append('\tAllowed channels: {}'.format(
                    'All' if handler.channels is None else handler.channels))

        return '\n'.join(res)
