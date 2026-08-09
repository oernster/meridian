"""The MMSP protocol version this implementation speaks.

Meridian is publicly the reference implementation of MMSP, so the version it
claims has to be stated once and checked against the specification rather than
repeated. It previously existed only inside the `MMSP/1.0` User-Agent literal
in `http_fetcher`: nowhere near the specification that defines it, and nowhere
near the parser that has to honour it.

`tests/infrastructure/test_mmsp_conformance.py` holds this to the `$id` of the
published feed schema whenever the MMSP-Spec repository is checked out beside
this one, so a protocol revision cannot land here unnoticed. The dependency is
one-directional: this implementation reads the specification's artefacts and
the specification depends on nothing here.
"""

from __future__ import annotations

PROTOCOL_VERSION = "1.0"
PROTOCOL_MAJOR = PROTOCOL_VERSION.split(".", 1)[0]


def accepts_document_version(declared: object) -> bool:
    """Whether a document's declared `mmsp` version is one this client reads.

    Specification Section 5.7: a 1.x client MUST accept any 1.MINOR and MUST
    reject anything else. Forward compatibility runs across minors only, so a
    future 2.x document is refused rather than parsed on the assumption that
    the parts this parser understands still mean what they did.

    A missing or malformed version is refused for the same reason: the
    document has not said what it is, so nothing can be assumed about it.
    """
    if not isinstance(declared, str):
        return False
    major, dot, minor = declared.partition(".")
    return bool(dot) and major == PROTOCOL_MAJOR and minor.isdigit()
