"""Bounded, per-process cache with single-flight loading for external API reads.

The Cloud Run image runs one worker. Multiple instances do not share this cache;
use a shared cache before scaling the service beyond a single instance.
"""

from concurrent.futures import Future
from copy import deepcopy
from threading import Lock
from time import monotonic


class RequestCache:
    def __init__(self, max_entries=512):
        self.max_entries = max_entries
        self.entries = {}
        self.pending = {}
        self.lock = Lock()

    def clear(self):
        with self.lock:
            self.entries.clear()

    def get(self, key, loader, ttl=30, empty_ttl=120, error_ttl=30):
        # Only the first caller performs I/O; concurrent callers share its result.
        with self.lock:
            cached = self.entries.get(key)
            if cached and cached[0] > monotonic():
                if cached[2]:
                    raise cached[1]
                return deepcopy(cached[1])
            future = self.pending.get(key)
            owner = future is None
            if owner:
                future = self.pending[key] = Future()
        if not owner:
            return deepcopy(future.result())

        try:
            value = loader()
        except Exception as exc:
            with self.lock:
                self._save(key, exc, error_ttl, True)
                self.pending.pop(key, None)
            future.set_exception(exc)
            raise
        else:
            with self.lock:
                lifetime = ttl(value) if callable(ttl) else ttl
                self._save(key, value, lifetime if value else empty_ttl, False)
                self.pending.pop(key, None)
            future.set_result(value)
            return deepcopy(value)

    def _save(self, key, value, ttl, is_error):
        now = monotonic()
        for expired in [k for k, entry in self.entries.items() if entry[0] <= now]:
            self.entries.pop(expired, None)
        while len(self.entries) >= self.max_entries:
            self.entries.pop(next(iter(self.entries)))
        self.entries[key] = (now + ttl, value, is_error)
