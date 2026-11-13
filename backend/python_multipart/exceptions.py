"""Exceptions for multipart compatibility shim."""

class MultipartError(Exception):
    pass

class FormParserError(MultipartError):
    pass
