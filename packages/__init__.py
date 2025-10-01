"""Mavik shared packages namespace.

Keep this file intentionally lightweight to avoid side effects when importing
subpackages like ``packages.common`` in tests or tools. Heavy modules (e.g.,
configuration loaders, AWS clients) should be imported explicitly from their
own subpackages by consumers instead of being auto-imported here.
"""

# Expose only the lightweight "common" subpackage by default.
__all__ = [
    "common",
]
