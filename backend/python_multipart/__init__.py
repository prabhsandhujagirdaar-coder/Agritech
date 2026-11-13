"""Pure Python multipart compatibility shim for AgriChain AI."""
__version__ = "0.0.20"

from .exceptions import FormParserError, MultipartError
from .multipart import MultipartParser, parse_options_header

__all__ = [
    "__version__",
    "MultipartParser",
    "parse_options_header",
    "FormParserError",
    "MultipartError",
]
