from asyncio import Queue
from re import compile as rc

AudioQ = Queue[bytes]
persian_match = rc('[\u0600-\u06ff]').search
