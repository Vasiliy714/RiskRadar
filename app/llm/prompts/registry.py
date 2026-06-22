from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PromptSpec:
    name: str
    version: str
    template: str
    temperature: float = 0.0
    model: str | None = None
    schema_ref: str | None = None


class PromptRegistry:
    """Читает markdown-файлы prompt-шаблонов и их YAML-метаданные."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._prompts_dir = prompts_dir or Path("prompts")
        self._cache: dict[tuple[str, str], PromptSpec] = {}

    def get(self, name: str, *, version: str = "v1") -> PromptSpec:
        cache_key = (name, version)
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._prompts_dir / f"{name}.{version}.md"
        if not path.is_file():
            msg = f"prompt not found: {path}"
            raise FileNotFoundError(msg)

        spec = _parse_prompt_file(path, name=name, version=version)
        self._cache[cache_key] = spec
        return spec

    def render(self, name: str, *, version: str = "v1", **variables: str) -> tuple[str, PromptSpec]:
        spec = self.get(name, version=version)
        return spec.template.format(**variables), spec


def _parse_prompt_file(path: Path, *, name: str, version: str) -> PromptSpec:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        msg = f"prompt file must start with frontmatter: {path}"
        raise ValueError(msg)

    _, frontmatter, body = raw.split("---", 2)
    meta = _parse_frontmatter(frontmatter)

    file_version = meta.pop("version", version)
    temperature = float(meta.pop("temperature", 0.0))
    model = meta.pop("model", None)
    schema_ref = meta.pop("schema_ref", None)

    if meta:
        unknown = ", ".join(sorted(meta))
        msg = f"unknown frontmatter keys in {path}: {unknown}"
        raise ValueError(msg)

    return PromptSpec(
        name=name,
        version=str(file_version),
        template=body.strip(),
        temperature=temperature,
        model=str(model) if model is not None else None,
        schema_ref=str(schema_ref) if schema_ref is not None else None,
    )


def _parse_frontmatter(raw: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition(":")
        if not separator:
            msg = f"invalid frontmatter line: {stripped!r}"
            raise ValueError(msg)
        meta[key.strip()] = value.strip()
    return meta
