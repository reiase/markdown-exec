"""Formatter and utils for executing Python code."""

from __future__ import annotations

import traceback
from functools import partial
from io import StringIO
from typing import Any

from markdown.core import Markdown

from markdown_exec.rendering import code_block, markdown, tabbed


def buffer_print(buffer: StringIO, *text: str, end: str = "\n", **kwargs: Any) -> None:
    """Print Markdown.

    Parameters:
        buffer: A string buffer to write into.
        *text: The text to write into the buffer. Multiple strings accepted.
        end: The string to write at the end.
        **kwargs: Other keyword arguments passed to `print` are ignored.
    """
    buffer.write(" ".join(text) + end)


def exec_python(  # noqa: WPS231
    code: str,
    md: Markdown,
    html: bool,
    source: str,
    tabs: tuple[str, str],
    **options: Any,
) -> str:
    """Execute code and return HTML.

    Parameters:
        code: The code to execute.
        md: The Markdown instance.
        html: Whether to inject output as HTML directly, without rendering.
        source: Whether to show source as well, and where.
        tabs: Titles of tabs (if used).
        **options: Additional options passed from the formatter.

    Returns:
        HTML contents.
    """
    markdown.mimic(md)

    source_tab_title, result_tab_title = tabs
    extra = options.get("extra", {})

    buffer = StringIO()
    exec_globals = {"print": partial(buffer_print, buffer)}

    try:
        exec(code, {}, exec_globals)  # noqa: S102
    except Exception as error:
        trace = traceback.TracebackException.from_exception(error)
        for frame in trace.stack:
            if frame.filename == "<string>":
                frame.filename = "<executed code block>"
                frame._line = code.split("\n")[frame.lineno - 1]  # type: ignore[attr-defined,operator]  # noqa: WPS437
        output = code_block("python", "".join(trace.format()), **extra)
    else:
        output = buffer.getvalue()
        if html:
            output = f'<div markdown="0">{str(output)}</div>'

    if source:
        source_block = code_block("python", code, **extra)
    if source == "above":
        output = source_block + "\n\n" + output
    elif source == "below":
        output = output + "\n\n" + source_block
    elif source == "tabbed-left":
        output = tabbed((source_tab_title, source_block), (result_tab_title, output))
    elif source == "tabbed-right":
        output = tabbed((result_tab_title, output), (source_tab_title, source_block))

    return markdown.convert(output)
