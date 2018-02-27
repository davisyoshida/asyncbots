"""
AsyncBots
==========

This library provides a simple ``asyncio`` based interface for writing ``RTM <https://api.slack.com/rtm>`` bots for Slack. Many distinct functions can be run through a single Slack bot plugin, triggered by user defined commands (e.g. ``!myCommand``).

Example
```````
A bot which can be triggered by the message ``!greet Guido`` looks like this:

.. code:: python

    from asyncbots.bot import SlackBot, register
    from asyncbots.command import MessageCommand
    from pyparsing import alphas, Word

    class MyBot(SlackBot)
        def __init__(self):
            self.name = 'My Bot'

            # Match 'greet' followed by any word
            self.expr = 'greet' + Word(alphas).setResultsName('user')

        @register()
        async def handler(self, sender, channel, parsed_message):
            return MessageCommand('Hello ' + parsed_message['user'])
"""
from setuptools import setup,find_packages

setup(
    name='asyncbots',
    version='0.1.2',
    packages=find_packages(),
    license='MIT',
    long_description=__doc__,
    description='A framework for Slack RTM bots.',
    url='https://github.com/davisyoshida/asyncbots',
    author='Davis Yoshida',
    author_email='dyoshida@ttic.edu',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    install_requires=['mongoengine', 'pyparsing', 'requests', 'websockets'],
    keywords='slack chatbot rtm bot',
    python_requires='>=3.5'
)
