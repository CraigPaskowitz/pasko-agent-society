"""Gate 2 bounded model-mediated peer-exposure experiment.

The package contains deterministic protocol, parsing, storage, replay, and
analysis code only. The operator-owned network transport lives in ``scripts``.
"""

from .protocol import PROTOCOL_ID, PROTOCOL_NAMESPACE

__all__ = ["PROTOCOL_ID", "PROTOCOL_NAMESPACE"]
