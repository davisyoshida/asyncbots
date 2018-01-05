# AsyncBots

## Features
`AsyncBots` provides an interface for writing Slack chat bots which respond to user defined commands. This allows users to run many different functionalities through a single RTM chat bot, which is convenient for unpaid Slack teams which only allow 5 bots.

Bots consist of a user defined command, and a function which will be called when the command is triggered. This function can then send messages, add reactions, upload files and more. This, in combination with the use of pyparsing to define commands makes `AyncBots` powerful and flexible.

In channels the bot is added to, channel history is saved, which can be helpful as Slack only allows access to the last 10,000 messages a free team has sent.

## Examples

### Defining a simple bot
The simplest bot consists of a class with a constructor and one method.
```python
from asyncbots.bot import SlackBot, register
from asyncbots.command import MessageCommand
from pyparsing import alphas, Word

class MyBot(SlackBot)
    def __init__(self, slack=None):
        # Call SlackBot's constructor
        super(SlackBot, self).__init__(self, slack=slack)
        self.name = 'My Bot'
        self.expr = 'greet' + Word(alphas).setResultsName('user')

    @register()
    async def handler(self, sender, channel, parsed):
        return MessageCommand('Hello ' + parsed['user'])
```
The fields `self.name` and `self.expr` are used to register the command with the Slack core. To use other field names, simply pass them to `@register`:

```python
...
class MyBot(SlackBot)
    def __init__(self, slack=None):
        ...
        self.another_name = 'Airspeed measurement'

        self.another_expr = 'airspeed'

    @register(name='another_name', expr='another_expr')
    def get_airspeed(self, sender, channel, parsed):
        return MessageCommand('African or European?')
```
