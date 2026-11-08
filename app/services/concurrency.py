"""Bounded locks for short database writes in the single-worker deployment."""

from contextlib import contextmanager
from functools import wraps
from inspect import signature
from threading import RLock
from typing import get_type_hints
from weakref import WeakValueDictionary

from fastapi import HTTPException

WRITE_LOCK = RLock()
CONTENT_LOCKS = WeakValueDictionary()
CONTENT_LOCK_GUARD = RLock()
RELEASE_LOCK = RLock()


@contextmanager
def content_lock(user_id):
    with CONTENT_LOCK_GUARD:
        lock = CONTENT_LOCKS.get(user_id)
        if lock is None:
            lock = RLock()
            CONTENT_LOCKS[user_id] = lock
    with bounded_lock(lock):
        yield


@contextmanager
def bounded_lock(lock):
    if not lock.acquire(timeout=20):
        raise HTTPException(
            status_code=503,
            detail="Practice content is being prepared. Retry shortly.",
            headers={"Retry-After": "5"},
        )
    try:
        yield
    finally:
        lock.release()


def serialized_write(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with WRITE_LOCK:
            return function(*args, **kwargs)
    hints = get_type_hints(function)
    original = signature(function)
    wrapped.__signature__ = original.replace(
        parameters=[
            p.replace(annotation=hints.get(p.name, p.annotation))
            for p in original.parameters.values()
        ],
        return_annotation=hints.get("return", original.return_annotation),
    )
    return wrapped
