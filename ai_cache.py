import time


_CACHE: dict[str, tuple[float, str]] = {}


def get_cached_response(key: str, ttl_seconds: int = 30) -> str | None:
    item = _CACHE.get(key)
    if item is None:
        return None

    created_at, value = item
    if time.time() - created_at > ttl_seconds:
        _CACHE.pop(key, None)
        return None

    return value


def set_cached_response(key: str, value: str) -> None:
    _CACHE[key] = (time.time(), value)
