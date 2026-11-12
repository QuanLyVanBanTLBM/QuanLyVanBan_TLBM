"""Bounded, exact-match cache for answers grounded in shared AI knowledge."""
import hashlib
import json
import logging
import re
import threading
import time
import unicodedata
from collections import OrderedDict

from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)

CACHE_ALIAS = "ai_faq"
KEY_PREFIX = "ai:cache:faq:"
TTL_SECONDS = 12 * 60 * 60
MAX_ENTRIES = 1000
MAX_ENTRY_BYTES = 10 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024

_INDEX_KEY = f"{KEY_PREFIX}__lru"
_SIZES_KEY = f"{KEY_PREFIX}__sizes"
_TOTAL_KEY = f"{KEY_PREFIX}__bytes"
_LOCAL_LOCK = threading.RLock()
_LOCAL_ENTRIES = OrderedDict()
_LOCAL_SIZES = {}
_REDIS_LOCK = threading.Lock()
_REDIS_URL = None
_REDIS_CLIENT = None

_TRACK_ENTRY_SCRIPT = """
local index_key, sizes_key, total_key = KEYS[1], KEYS[2], KEYS[3]
local member, score = ARGV[1], tonumber(ARGV[2])
local size, max_entries, max_bytes = tonumber(ARGV[3]), tonumber(ARGV[4]), tonumber(ARGV[5])
local old_size = tonumber(redis.call('HGET', sizes_key, member) or '0')
redis.call('ZADD', index_key, score, member)
redis.call('HSET', sizes_key, member, size)
redis.call('INCRBY', total_key, size - old_size)
while redis.call('ZCARD', index_key) > max_entries
   or tonumber(redis.call('GET', total_key) or '0') > max_bytes do
    local oldest = redis.call('ZRANGE', index_key, 0, 0)
    if #oldest == 0 then break end
    local victim = oldest[1]
    local victim_size = tonumber(redis.call('HGET', sizes_key, victim) or '0')
    redis.call('DEL', victim)
    redis.call('ZREM', index_key, victim)
    redis.call('HDEL', sizes_key, victim)
    redis.call('INCRBY', total_key, -victim_size)
end
redis.call('EXPIRE', index_key, 46800)
redis.call('EXPIRE', sizes_key, 46800)
redis.call('EXPIRE', total_key, 46800)
return 1
"""

_REMOVE_ENTRY_SCRIPT = """
local member, sizes_key, total_key = ARGV[1], KEYS[2], KEYS[3]
local old_size = tonumber(redis.call('HGET', sizes_key, member) or '0')
redis.call('ZREM', KEYS[1], member)
redis.call('HDEL', sizes_key, member)
if old_size > 0 then redis.call('INCRBY', total_key, -old_size) end
return 1
"""

_CLEAR_SCRIPT = """
local members = redis.call('ZRANGE', KEYS[1], 0, -1)
for _, member in ipairs(members) do redis.call('DEL', member) end
redis.call('DEL', KEYS[1], KEYS[2], KEYS[3])
return #members
"""


def normalize_question(question):
    text = unicodedata.normalize("NFKC", str(question or "")).casefold()
    return re.sub(r"\s+", " ", text).strip()


def cache_key(question, language="vi"):
    normalized = normalize_question(question)
    language = str(language or "vi").lower().split("-", 1)[0]
    digest = hashlib.sha256(f"{language}\0{normalized}".encode("utf-8")).hexdigest()
    return f"{KEY_PREFIX}{digest}"


def request_is_cacheable(question, history=None, filename=None, category=None,
                         conversational=False, inappropriate=False):
    return bool(
        normalize_question(question)
        and not history
        and not filename
        and not (category and str(category).strip())
        and not conversational
        and not inappropriate
    )


def sources_are_shareable(sources):
    """Only shared AI knowledge and static business notes can seed cross-user hits."""
    if not sources:
        return False
    for source in sources:
        if source.get("source_type") == "business_spec":
            continue
        if source.get("source_class") != "ai_knowledge_base":
            return False
        category = unicodedata.normalize("NFKD", str(source.get("category") or "")).casefold()
        category = "".join(char for char in category if not unicodedata.combining(char))
        category = f" {re.sub(r'[^a-z0-9]+', ' ', category).strip()} "
        if any(
            f" {term} " in category
            for term in (
                "han che", "hanche", "mat", "bao mat", "bi mat", "nhay cam",
                "restricted", "confidential", "sensitive", "secret", "personal", "private", "ca nhan",
            )
        ):
            return False
    return True


def _scope_sources_are_current(scope_sources):
    if not isinstance(scope_sources, list):
        return False
    if not scope_sources:
        return True
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            for source in scope_sources:
                filename = source.get("file_name")
                if not filename:
                    return False
                cursor.execute(
                    """SELECT DISTINCT metadata ->> 'source_class', metadata ->> 'category'
                       FROM ai_document_embedding WHERE metadata ->> 'file_name' = %s""",
                    [filename],
                )
                rows = cursor.fetchall()
                if not rows or any(
                    source_class != "ai_knowledge_base"
                    or category != source.get("category")
                    or not sources_are_shareable([{"source_class": source_class, "category": category}])
                    for source_class, category in rows
                ):
                    return False
        return True
    except Exception as error:
        logger.warning("FAQ answer cache scope validation failed (%s)", type(error).__name__)
        return False


def _cache():
    return caches[CACHE_ALIAS]


def _redis_client():
    global _REDIS_URL, _REDIS_CLIENT
    url = getattr(settings, "REDIS_URL", "")
    if not url:
        return None
    with _REDIS_LOCK:
        if _REDIS_CLIENT is None or _REDIS_URL != url:
            if _REDIS_CLIENT is not None:
                _REDIS_CLIENT.close()
            from redis import Redis
            _REDIS_CLIENT = Redis.from_url(
                url, decode_responses=False, socket_connect_timeout=1, socket_timeout=1,
            )
            _REDIS_URL = url
        return _REDIS_CLIENT


def _redis_tracking_keys(cache_backend):
    return tuple(cache_backend.make_key(key) for key in (_INDEX_KEY, _SIZES_KEY, _TOTAL_KEY))


def _remove_tracking(cache_backend, key):
    client = _redis_client()
    if client is not None:
        client.eval(
            _REMOVE_ENTRY_SCRIPT, 3, *_redis_tracking_keys(cache_backend), cache_backend.make_key(key),
        )
        return
    with _LOCAL_LOCK:
        _LOCAL_ENTRIES.pop(key, None)
        _LOCAL_SIZES.pop(key, None)


def _touch(cache_backend, key):
    client = _redis_client()
    if client is not None:
        index_key, _, _ = _redis_tracking_keys(cache_backend)
        client.zadd(index_key, {cache_backend.make_key(key): time.time()})
        return
    with _LOCAL_LOCK:
        if key in _LOCAL_ENTRIES:
            _LOCAL_ENTRIES.move_to_end(key)


def get_cached_answer(question, language="vi"):
    key = cache_key(question, language)
    backend = _cache()
    try:
        value = backend.get(key)
        if value is None:
            _remove_tracking(backend, key)
            return None
        _touch(backend, key)
        result = json.loads(value) if isinstance(value, str) else value
        if not isinstance(result, dict) or not isinstance(result.get("answer"), str) or not isinstance(result.get("sources"), list):
            backend.delete(key)
            _remove_tracking(backend, key)
            return None
        if not _scope_sources_are_current(result.pop("_scope_sources", None)):
            backend.delete(key)
            _remove_tracking(backend, key)
            return None
        return result
    except Exception as error:
        logger.warning("FAQ answer cache read failed (%s)", type(error).__name__)
        return None


def set_cached_answer(question, language, answer, sources, eligible_sources=None):
    eligibility_sources = sources if eligible_sources is None else eligible_sources
    if not sources_are_shareable(eligibility_sources):
        return False
    scope_sources = []
    for source in eligibility_sources:
        if source.get("source_class") == "ai_knowledge_base":
            scope_sources.append({
                "file_name": source.get("file_name"),
                "category": source.get("category"),
            })
    result = {"answer": str(answer), "sources": sources, "_scope_sources": scope_sources}
    try:
        serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        size = len(serialized.encode("utf-8"))
        if size > MAX_ENTRY_BYTES:
            return False
        key = cache_key(question, language)
        backend = _cache()
        backend.set(key, serialized, timeout=TTL_SECONDS)
        client = _redis_client()
        if client is not None:
            index_key, sizes_key, total_key = _redis_tracking_keys(backend)
            client.eval(
                _TRACK_ENTRY_SCRIPT, 3, index_key, sizes_key, total_key,
                backend.make_key(key), time.time(), size, MAX_ENTRIES, MAX_TOTAL_BYTES,
            )
        else:
            with _LOCAL_LOCK:
                _LOCAL_ENTRIES[key] = None
                _LOCAL_ENTRIES.move_to_end(key)
                _LOCAL_SIZES[key] = size
                total = sum(_LOCAL_SIZES.values())
                while len(_LOCAL_ENTRIES) > MAX_ENTRIES or total > MAX_TOTAL_BYTES:
                    victim, _ = _LOCAL_ENTRIES.popitem(last=False)
                    total -= _LOCAL_SIZES.pop(victim, 0)
                    if victim != key:
                        backend.delete(victim)
        return True
    except Exception as error:
        logger.warning("FAQ answer cache write failed (%s)", type(error).__name__)
        try:
            _cache().delete(cache_key(question, language))
        except Exception:
            pass
        return False


def clear_faq_cache():
    """Invalidate the bounded answer namespace without flushing Redis/Celery."""
    try:
        backend = _cache()
        client = _redis_client()
        if client is not None:
            client.eval(_CLEAR_SCRIPT, 3, *_redis_tracking_keys(backend))
        else:
            backend.clear()
            with _LOCAL_LOCK:
                _LOCAL_ENTRIES.clear()
                _LOCAL_SIZES.clear()
    except Exception as error:
        logger.warning("FAQ answer cache invalidation failed (%s)", type(error).__name__)
