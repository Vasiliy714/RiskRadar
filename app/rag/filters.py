from __future__ import annotations

from qdrant_client.http import models as qmodels


def build_payload_filter(
    *,
    issuer: str | None,
    doc_type: str | None,
    is_current: bool | None,
) -> qmodels.Filter | None:
    conditions: list[qmodels.Condition] = []
    if issuer is not None:
        conditions.append(
            qmodels.FieldCondition(
                key="issuer",
                match=qmodels.MatchValue(value=issuer),
            )
        )
    if doc_type is not None:
        conditions.append(
            qmodels.FieldCondition(
                key="doc_type",
                match=qmodels.MatchValue(value=doc_type),
            )
        )
    if is_current is not None:
        conditions.append(
            qmodels.FieldCondition(
                key="is_current",
                match=qmodels.MatchValue(value=is_current),
            )
        )
    if not conditions:
        return None
    return qmodels.Filter(must=conditions)
