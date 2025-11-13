from re import compile as rc

_fa_search = rc('[\u0600-\u06ff]').search


def detect_lang(text: str) -> str:
    return 'fa' if _fa_search(text) else 'en'
