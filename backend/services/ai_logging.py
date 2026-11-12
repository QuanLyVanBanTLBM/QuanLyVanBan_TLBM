"""Trace theo từng request của đường chat AI.

Mỗi request có một trace. Mỗi giai đoạn ghi thời gian. Giai đoạn đầu tiên ném exception ghi
error_stage và error_reason; exception được xử lý trong code (degraded) vẫn được ghi.
View ghi đúng một dòng tóm tắt khi request kết thúc. Không ghi câu hỏi, lịch sử hội thoại
hay nội dung tài liệu; chỉ ghi số lượng, cờ và mã định danh nội bộ.
"""

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

logger = logging.getLogger("qlvb.ai")

_current_trace = ContextVar("qlvb_ai_trace", default=None)


class AiTrace:
    def __init__(self, **fields):
        self.request_id = uuid.uuid4().hex[:12]
        self.fields = dict(fields)
        self.stages = {}
        self.error_stage = None
        self.error_reason = None


def start_trace(**fields):
    trace = AiTrace(**fields)
    return trace, _current_trace.set(trace)


def end_trace(token):
    _current_trace.reset(token)


def set_fields(**values):
    trace = _current_trace.get()
    if trace is not None:
        trace.fields.update(values)


def add_count(name, amount=1):
    trace = _current_trace.get()
    if trace is not None:
        trace.fields[name] = trace.fields.get(name, 0) + amount


def mark_error(stage, reason):
    """Ghi giai đoạn lỗi đầu tiên của request; các lần gọi sau bị bỏ qua."""
    trace = _current_trace.get()
    if trace is not None and trace.error_stage is None:
        trace.error_stage = stage
        trace.error_reason = reason


@contextmanager
def ai_stage(name):
    trace = _current_trace.get()
    started = time.perf_counter()
    try:
        yield
    except Exception as error:
        mark_error(name, getattr(error, "ai_reason", None) or type(error).__name__)
        raise
    finally:
        if trace is not None:
            trace.stages[name] = round((time.perf_counter() - started) * 1000)


def format_summary(trace, status):
    parts = [f"request_id={trace.request_id}", f"status={status}"]
    if trace.error_stage:
        parts.append(f"error_stage={trace.error_stage}")
        parts.append(f"error_reason={trace.error_reason}")
    parts.extend(f"{key}={value}" for key, value in trace.fields.items())
    parts.append("stage_ms=" + ",".join(f"{name}:{ms}" for name, ms in trace.stages.items()))
    return "ai_chat " + " ".join(parts)


def log_summary(trace, status):
    if status >= 500:
        level = logging.ERROR
    elif status >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    logger.log(level, format_summary(trace, status))


def log_exception():
    """Ghi traceback của exception đang xử lý, kèm request_id để khớp với dòng tóm tắt."""
    trace = _current_trace.get()
    request_id = trace.request_id if trace is not None else "-"
    logger.error("ai_chat exception request_id=%s", request_id, exc_info=True)
