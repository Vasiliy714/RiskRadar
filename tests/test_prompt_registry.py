from __future__ import annotations

from pathlib import Path

import pytest

from app.llm.prompts.registry import PromptRegistry


def test_prompt_registry_loads_frontmatter_and_body() -> None:
    registry = PromptRegistry(prompts_dir=Path("prompts"))
    spec = registry.get("risk_summary", version="v1")

    assert spec.name == "risk_summary"
    assert spec.version == "v1"
    assert spec.temperature == 0.0
    assert spec.schema_ref == "RiskSummary"
    assert "{issuer_code}" in spec.template
    assert "{context}" in spec.template


def test_prompt_registry_render_substitutes_variables() -> None:
    registry = PromptRegistry(prompts_dir=Path("prompts"))
    rendered, spec = registry.render(
        "risk_summary",
        version="v1",
        issuer_code="SBER",
        context="Revenue grew 10%.",
    )

    assert "SBER" in rendered
    assert "Revenue grew 10%." in rendered
    assert spec.schema_ref == "RiskSummary"


def test_prompt_registry_missing_file_raises() -> None:
    registry = PromptRegistry(prompts_dir=Path("prompts"))

    with pytest.raises(FileNotFoundError):
        registry.get("missing_prompt", version="v1")
