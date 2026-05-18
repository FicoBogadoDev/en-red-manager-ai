from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_SERVICE_CATALOG_PATH = "config/service-catalog.md"


class CatalogBullet(BaseModel):
    text: str
    response: str | None = None

    @property
    def label(self) -> str:
        return self.text.strip(" .")

    @property
    def aliases(self) -> list[str]:
        normalized_parts = [
            part.strip(" .")
            for part in re.split(r"[,;/]|\s+o\s+", self.text)
            if part.strip(" .")
        ]
        return list(dict.fromkeys([self.label, *normalized_parts]))


class ServiceCatalog(BaseModel):
    raw_markdown: str
    offered: list[CatalogBullet] = Field(default_factory=list)
    adjacent_unsupported: list[CatalogBullet] = Field(default_factory=list)
    clearly_not_service: list[CatalogBullet] = Field(default_factory=list)
    ambiguous: list[CatalogBullet] = Field(default_factory=list)


def load_service_catalog(path: str | Path) -> ServiceCatalog:
    catalog_path = Path(path)
    return parse_service_catalog(catalog_path.read_text(encoding="utf-8"))


def parse_service_catalog(markdown: str) -> ServiceCatalog:
    sections: dict[str, list[CatalogBullet]] = {
        "offered": [],
        "adjacent_unsupported": [],
        "clearly_not_service": [],
        "ambiguous": [],
    }
    current_section: str | None = None
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_section = _section_key(line.removeprefix("## ").strip())
            continue
        if current_section is None or not line.startswith("- "):
            continue
        sections[current_section].append(_parse_bullet(line.removeprefix("- ").strip()))

    return ServiceCatalog(
        raw_markdown=markdown,
        offered=sections["offered"],
        adjacent_unsupported=sections["adjacent_unsupported"],
        clearly_not_service=sections["clearly_not_service"],
        ambiguous=sections["ambiguous"],
    )


def normalized_text(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def searchable_terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalized_text(text))
    return {
        _singularize(word)
        for word in words
        if len(word) >= 4 and word not in _STOPWORDS
    }


def _parse_bullet(text: str) -> CatalogBullet:
    parts = re.split(r"\bRespuesta:\s*", text, maxsplit=1)
    if len(parts) == 1:
        return CatalogBullet(text=text)
    return CatalogBullet(text=parts[0].strip(" ."), response=parts[1].strip(" ."))


def _section_key(title: str) -> str | None:
    normalized = normalized_text(title)
    if normalized.startswith("si ofrecemos"):
        return "offered"
    if normalized.startswith("no ofrecemos"):
        return "adjacent_unsupported"
    if normalized.startswith("claramente fuera"):
        return "clearly_not_service"
    if normalized.startswith("dudoso"):
        return "ambiguous"
    return None


def _singularize(word: str) -> str:
    if word.endswith("es") and len(word) > 5:
        return word[:-2]
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


_STOPWORDS = {
    "para",
    "como",
    "otro",
    "otra",
    "otros",
    "otras",
    "red",
    "redes",
    "seguridad",
    "proteccion",
    "trabajos",
    "mencionar",
    "aclarar",
    "busca",
    "hacer",
    "hacemos",
    "instalamos",
    "trabajamos",
}
