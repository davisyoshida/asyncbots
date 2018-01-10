"""Module with utility functions"""
import asyncio
from asyncio.futures import CancelledError
from functools import partial
import logging
import re
import traceback

import requests

logger = logging.getLogger(__name__)

def kill_all_tasks():
    """Kill all currently running asyncio tasks."""
    for task in asyncio.Task.all_tasks():
        task.cancel()
        print('Cancelled task')

async def handle_async_exception(coro, *args, **kwargs):
    """Wrapper for coroutines which will catch an exception and kill the entire program rather than hanging."""
    try:
        return await coro(*args, **kwargs)
    except Exception as e:
        if not isinstance(e, CancelledError):
            logger.error('Exception in %s', coro)
            logger.error(traceback.format_exc())
            kill_all_tasks()


_request_funcs = {'GET': requests.get, 'POST': requests.post}


async def make_request(url, params, request_type='GET', **kwargs):
    """Coroutine which makes request asychronously rather than blocking."""
    loop = asyncio.get_event_loop()

    func = partial(_request_funcs[request_type], params=params, **kwargs)
    res = (await loop.run_in_executor(None, func, url)).json()
    if res['ok'] is not True:
        logger.warning('Slack returned bad status: %s', res)
    return res


MENTION_RE = re.compile('<@(U[0-9A-Z]{8})>$')
def mention_to_uid(mention):
    """Converts a mention (as formatted by Slack) to a UID. Returns None if the input is not a valid mention."""
    res = MENTION_RE.match(mention)
    if res is None:
        return None
    return res.group(1)


def uid_to_mention(uid):
    """Convert a UID to a mention."""
    return '<@{}>'.format(uid)
