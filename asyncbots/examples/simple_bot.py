"""A minimal example of using the asyncbots API."""
import asyncio
import os

from asyncbots.bot import register, SlackBot
from asyncbots.command import MessageCommand
from asyncbots.slack_api import Slack, SlackConfig
import mongoengine
from pyparsing import alphanums, CaselessLiteral, Optional, StringEnd, Word


class SimpleBot(SlackBot):
    def __init__(self, slack=None):
        super(SimpleBot, self).__init__(slack=slack)
        self.name = 'Hello World'
        self.expr = CaselessLiteral('mycommand') # Bot will trigger on messages starting with !mycommand

        # Bot will trigger on messages of the form !othercommand [alphanumeric argument]
        self.other_name = 'Greeter'
        self.second_expr = CaselessLiteral('othercommand') + Optional(Word(alphanums).setResultsName('username')) + StringEnd()
        self.second_doc = 'Greet a user\n\tothercommand [name]'

    # These areguments are used to find the appropriate class members when the bot is run
    @register()
    async def hello_function(self, user, in_channel, parsed):
        """
        user: The user ID of the user that sent the message
        in_channel: The channel in which the message was sent, or None if it was a DM
        parsed: The result of calling self.some_expr.parseString() on the text of the message
        """
        return MessageCommand(text='Hello World')

    @register(name='other_name', expr='second_expr', doc='second_doc')
    async def second_function(self, user, in_channel, parsed):
        # Check whether the Optional part of the expression was triggered
        if 'username' in parsed:
            greeting = 'Hello {}'.format(parsed['username'])
        else:
            greeting = 'Hello'

        return MessageCommand(text=greeting)


def main():
    slack = Slack()
    # No need to do anything other than construct the bot
    SimpleBot(slack=slack)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(slack.run())

if __name__ == '__main__':
    main()
