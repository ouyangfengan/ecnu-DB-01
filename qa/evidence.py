import json
import re
from datetime import datetime, timezone
from threading import Lock
from time import perf_counter


SECRET_KEYS = {"password", "password_hash", "token", "token_hash", "authorization", "cookie"}


def sanitize(value):
    if isinstance(value, dict):
        return {
            str(key): "<已隐藏>" if str(key).lower() in SECRET_KEYS else sanitize(child)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize(child) for child in value]
    if isinstance(value, str):
        value = re.sub(r"(mongodb(?:\+srv)?://)[^/\s@]+@", r"\1<已隐藏>@", value)
        value = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/\-=]+", "Bearer <已隐藏>", value)
        return re.sub(
            r"""(?i)(['"](?:password|password_hash|token|token_hash|authorization|cookie)['"]\s*:\s*)(['"])(.*?)(\2)""",
            lambda match: match[1] + match[2] + "<已隐藏>" + match[2], value,
        )
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat()


class Evidence:
    def __init__(self):
        self.events = []
        self.lock = Lock()
        self.started = perf_counter()

    def record(self, kind, **fields):
        with self.lock:
            event = {
                "sequence": len(self.events) + 1,
                "kind": kind,
                "at": utc_timestamp(),
                "elapsed_seconds": round(perf_counter() - self.started, 6),
                **sanitize(fields),
            }
            self.events.append(event)
            return event

    def finish_request(self, event, **fields):
        with self.lock:
            event.update(sanitize(fields))
            event["finished_at"] = utc_timestamp()

    def check(self, label, actual, expected, *, source="断言", query=None, contains=False):
        passed = expected in actual if contains else actual == expected
        self.record(
            "check", label=label, source=source, query=query,
            comparison="contains" if contains else "equals",
            expected=expected, actual=actual, passed=passed,
        )
        assert passed, f"{label}: expected={sanitize(expected)!r}, actual={sanitize(actual)!r}"
        return actual

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.events, ensure_ascii=True))
