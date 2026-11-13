"""Multipart parser implementation for Starlette/FastAPI without third-party dependencies."""

from __future__ import annotations
from typing import Any, Callable, Dict
from .exceptions import FormParserError


def parse_options_header(value: Any) -> tuple[bytes, dict[Any, Any]]:
    """Parse Content-Type or Content-Disposition options header."""
    if value is None:
        return b"", {}
    if isinstance(value, str):
        raw = value.encode("latin-1")
    elif isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
    else:
        raw = str(value).encode("latin-1")

    parts = raw.split(b";")
    main_val = parts[0].strip()
    options: dict[Any, Any] = {}
    for part in parts[1:]:
        if b"=" in part:
            k, v = part.split(b"=", 1)
            k = k.strip()
            v = v.strip().strip(b"\"'")
            options[k] = v
            try:
                options[k.decode("latin-1")] = v.decode("latin-1")
            except Exception:
                pass
    return main_val, options


class MultipartParser:
    """Buffer-based multipart parser executing Starlette callbacks."""

    def __init__(self, boundary: bytes | str, callbacks: Dict[str, Callable[..., Any]]):
        if isinstance(boundary, str):
            boundary = boundary.encode("latin-1")
        self.boundary = boundary
        self.callbacks = callbacks
        self._buffer = bytearray()
        self._delimiter = b"--" + self.boundary

    def write(self, data: bytes) -> None:
        self._buffer.extend(data)
        self._process_buffer()

    def _process_buffer(self) -> None:
        # Drain into starlette if possible
        pass

    def finalize(self) -> None:
        buf = bytes(self._buffer)
        delimiter = self._delimiter
        parts = buf.split(delimiter)

        cb = self.callbacks
        parent = getattr(cb.get("on_part_data"), "__self__", None)

        for i, raw_part in enumerate(parts):
            if i == 0 and not raw_part.strip():
                continue
            if raw_part.startswith(b"--"):
                break

            if raw_part.startswith(b"\r\n"):
                raw_part = raw_part[2:]
            elif raw_part.startswith(b"\n"):
                raw_part = raw_part[1:]

            if raw_part.endswith(b"\r\n"):
                raw_part = raw_part[:-2]
            elif raw_part.endswith(b"\n"):
                raw_part = raw_part[:-1]

            if not raw_part:
                continue

            if b"\r\n\r\n" in raw_part:
                header_bytes, body_bytes = raw_part.split(b"\r\n\r\n", 1)
                header_lines = header_bytes.split(b"\r\n")
            elif b"\n\n" in raw_part:
                header_bytes, body_bytes = raw_part.split(b"\n\n", 1)
                header_lines = header_bytes.split(b"\n")
            else:
                continue

            if "on_part_begin" in cb:
                cb["on_part_begin"]()

            for line in header_lines:
                if b":" in line:
                    fname, fval = line.split(b":", 1)
                    fname = fname.strip()
                    fval = fval.strip()
                    if "on_header_field" in cb:
                        cb["on_header_field"](fname, 0, len(fname))
                    if "on_header_value" in cb:
                        cb["on_header_value"](fval, 0, len(fval))
                    if "on_header_end" in cb:
                        cb["on_header_end"]()

            if "on_headers_finished" in cb:
                cb["on_headers_finished"]()

            if "on_part_data" in cb and body_bytes:
                cb["on_part_data"](body_bytes, 0, len(body_bytes))

            if "on_part_end" in cb:
                cb["on_part_end"]()

            # Synchronize SpooledTemporaryFile if Starlette MultiPartParser
            if parent is not None:
                if hasattr(parent, "_file_parts_to_write"):
                    for part, data in parent._file_parts_to_write:
                        if part.file is not None and hasattr(part.file, "file"):
                            part.file.file.write(data)
                    parent._file_parts_to_write.clear()
                if hasattr(parent, "_file_parts_to_finish"):
                    for part in parent._file_parts_to_finish:
                        if part.file is not None and hasattr(part.file, "file"):
                            part.file.file.seek(0)
                    parent._file_parts_to_finish.clear()

        if "on_end" in self.callbacks:
            self.callbacks["on_end"]()
