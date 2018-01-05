# AsyncBots
[![PyPI version](https://badge.fury.io/py/asyncbots.svg)](https://badge.fury.io/py/asyncbots)
## Features
`AsyncBots` provides an `asyncio` based interface for writing Slack Real Time Messaging (![RTM](https://api.slack.com/rtm)) chat bots with almost no code other than the core functionality. All user defined bots run through a single bot user on Slack, with `AsyncBots` directing messages to the appropriate bots.

Bots consist of a user defined trigger (e.g. `!mycommand` or `!simulate <user>`) and a function which will be called when a user says the trigger in chat. When activated, the bot can then send messages, add reactions, upload files, and more. Commands are defined using ![pyparsing](http://pyparsing.wikispaces.com/), which allows for filtering of messages without adding complexity.

In channels the bot is present in, channel history is (optionally) saved, including beyond the 10k message limit imposed on free teams.

## Examples

### Defining a simple bot
The simplest bot consists of a class with a constructor and one method.
```python
from asyncbots.bot import SlackBot, register
from asyncbots.command import MessageCommand
from pyparsing import alphas, Word

class MyBot(SlackBot)
    def __init__(self, slack=None):
        # Call parent's constructor
        super(MyBot, self).__init__(self, slack=slack)
        self.name = 'My Bot'
        self.expr = 'greet' + Word(alphas).setResultsName('user')

    @register()
    async def handler(self, sender, channel, parsed_message):
        # Send a reply in the channel this command was received in
        return MessageCommand('Hello ' + parsed_message['user'])
```
The fields `self.name` and `self.expr` are used to register the command with the Slack core. To use other field names (for instance if you want multiple commands on one class), simply pass them to `@register`:

```python
...
class MyBot(SlackBot)
    def __init__(self, slack=None):
        ...
        self.another_name = 'Airspeed measurement'

        self.another_expr = 'airspeed'

    @register(name='another_name', expr='another_expr')
    async def get_airspeed(self, sender, channel, parsed_message):
        return MessageCommand('African or European?')
```

### Connecting to Slack
In order to connect to Slack, construct an instance of `asyncbots.slack_api.Slack`:
```python
import asyncio
from asyncbots.slack_api import Slack
...
def main():
    slack = Slack()
    MyBot(slack=slack)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(slack.run())
```
The above method of constructing the `Slack` object assumes that the `SLACK_TOKEN` and `SLACK_BOT_NAME` environment variables are set to the Slack API token and bot's name in Slack respectively.

### Enabling logging
To enable message logging, create a connection to a mongoDB server using `mongoengine`.
```python
from mongoengine import connect
from asyncbots.slack_api import Slack, SlackConfig
...
def main():
    connect('mydbname')
    config = SlackConfig(db=True)
    slack = Slack(config)
    ...
```
