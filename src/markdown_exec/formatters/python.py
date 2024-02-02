"""Formatter for executing Python code."""

from __future__ import annotations

import traceback
from collections import defaultdict
from functools import partial
from io import StringIO
from typing import Any

from markdown_exec.formatters.base import ExecutionError, base_format
from markdown_exec.rendering import code_block
from markdown_exec.formatters.pyodide import _format_pyodide

_sessions_globals: dict[str, dict] = defaultdict(dict)
_sessions_counter: dict[str | None, int] = defaultdict(int)
_code_blocks: dict[str, list[str]] = {}


def _buffer_print(buffer: StringIO, *texts: str, end: str = "\n", **kwargs: Any) -> None:  # noqa: ARG001
    buffer.write(" ".join(str(text) for text in texts) + end)


def _code_block_id(
    id: str | None = None,  # noqa: A002
    session: str | None = None,
    title: str | None = None,
) -> str:
    _sessions_counter[session] += 1
    if id:
        code_block_id = f"id {id}"
    elif session:
        code_block_id = f"session {session}; n{_sessions_counter[session]}"
        if title:
            code_block_id = f"{code_block_id}; title {title}"
    else:
        code_block_id = f"n{_sessions_counter[session]}"
        if title:
            code_block_id = f"{code_block_id}; title {title}"
    return f"<code block: {code_block_id}>"


def _run_python(
    code: str,
    returncode: int | None = None,  # noqa: ARG001
    session: str | None = None,
    id: str | None = None,  # noqa: A002
    **extra: str,
) -> str:
    title = extra.get("title", None)
    code_block_id = _code_block_id(id, session, title)
    _code_blocks[code_block_id] = code.split("\n")
    exec_globals = _sessions_globals[session] if session else {}

    buffer = StringIO()
    exec_globals["print"] = partial(_buffer_print, buffer)

    try:
        compiled = compile(code, filename=code_block_id, mode="exec")
        exec(compiled, exec_globals)  # noqa: S102
    except Exception as error:  # noqa: BLE001
        trace = traceback.TracebackException.from_exception(error)
        for frame in trace.stack:
            if frame.filename.startswith("<code block: "):
                frame._line = _code_blocks[frame.filename][frame.lineno - 1]  # type: ignore[attr-defined,operator]
        raise ExecutionError(code_block("python", "".join(trace.format()), **extra)) from error
    return buffer.getvalue()


def _format_python(**kwargs: Any) -> str:
    if "extra" in kwargs and "pyodide" in kwargs["extra"]:
        if kwargs["extra"]["pyodide"] == "true":
            return _format_pyodide(**kwargs)
    return base_format(language="python", run=_run_python, **kwargs)
