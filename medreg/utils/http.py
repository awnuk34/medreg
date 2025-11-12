from __future__ import annotations
import requests

_session = None

def get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.max_redirects = 5
        _session = s
    return _session