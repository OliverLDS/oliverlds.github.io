#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RESEARCH_HTML = ROOT / "research.html"
START_MARKER = "<!-- PAPER_BLOCKS_START -->"
END_MARKER = "<!-- PAPER_BLOCKS_END -->"

PAPERS = [
    {
        "source_dir": Path(
            "/Users/oliver/Documents/2026/_2026-02-22_agentr_paper/AI_papers/decision_rights_allocation_concept/manuscript/current"
        ),
        "site_pdf": "decision_rights_allocation_concept.pdf",
    },
    {
        "source_dir": Path(
            "/Users/oliver/Documents/2026/_2026-02-22_agentr_paper/AI_papers/reducing_llm_rights/manuscript/current"
        ),
        "site_pdf": "reducing_llm_rights.pdf",
    },
    {
        "source_dir": Path(
            "/Users/oliver/Documents/2026/_2026-02-22_agentr_paper/AI_papers/agentr_intro/manuscript/current"
        ),
        "site_pdf": "agentr_intro.pdf",
    },
]


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].strip()
    return value


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    front_matter: dict[str, str] = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            body = "\n".join(lines[i + 1 :])
            return front_matter, body

        if not line or line.startswith(" ") or ":" not in line:
            i += 1
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()

        if value == "|":
            block: list[str] = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip() == "---":
                    break
                if next_line.startswith("  ") or next_line.startswith("\t"):
                    block.append(next_line.strip())
                    i += 1
                    continue
                if next_line.startswith(" ") and next_line.strip():
                    block.append(next_line.strip())
                    i += 1
                    continue
                break
            front_matter[key] = " ".join(block).strip()
            continue

        front_matter[key] = strip_quotes(value)
        i += 1

    return front_matter, text


def extract_abstract(front_matter: dict[str, str], body: str) -> str:
    if front_matter.get("abstract"):
        return front_matter["abstract"].strip()

    match = re.search(r"^# Abstract\s*$\n+(.*?)(?=\n# |\Z)", body, re.M | re.S)
    if match:
        return match.group(1).strip()

    raise ValueError("Could not find abstract in manuscript")


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\[@[^\]]+\]", "", text)
    return text


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def code_span_to_html(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    rendered: list[str] = []
    for part in parts:
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            rendered.append(f"<code>{html.escape(part[1:-1])}</code>")
        else:
            rendered.append(html.escape(part))
    return "".join(rendered)


def render_summary_paragraphs(abstract: str) -> list[str]:
    sentences = split_sentences(normalize_text(abstract))
    if not sentences:
        return []

    first = " ".join(sentences[:2]).strip()
    second = " ".join(sentences[2:4]).strip()

    paragraphs = [code_span_to_html(first)]
    if second:
        paragraphs.append(code_span_to_html(second))
    return paragraphs


def render_paper_block(title: str, paragraphs: list[str], pdf_name: str) -> str:
    lines = [
        '    <section class="paper-highlight reveal">',
        '      <p class="paper-status">Working Paper</p>',
        f"      <h2>{html.escape(title)}</h2>",
    ]
    for paragraph in paragraphs:
        lines.extend(
            [
                "      <p>",
                f"        {paragraph}",
                "      </p>",
            ]
        )
    lines.extend(
        [
            '      <div class="link-row">',
            f'        <a class="button button-primary" href="files/{html.escape(pdf_name)}">Open PDF</a>',
            "      </div>",
            "    </section>",
        ]
    )
    return "\n".join(lines)


def sync_papers() -> None:
    rendered_blocks: list[str] = []

    for paper in PAPERS:
        source_dir = paper["source_dir"]
        qmd_path = source_dir / "paper.qmd"
        pdf_path = source_dir / "paper.pdf"
        site_pdf_path = ROOT / "files" / paper["site_pdf"]

        front_matter, body = parse_front_matter(qmd_path.read_text())
        title = strip_quotes(front_matter["title"]).replace("**", "").strip()
        abstract = extract_abstract(front_matter, body)
        paragraphs = render_summary_paragraphs(abstract)

        shutil.copy2(pdf_path, site_pdf_path)
        rendered_blocks.append(render_paper_block(title, paragraphs, paper["site_pdf"]))

    html_text = RESEARCH_HTML.read_text()
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.S,
    )
    replacement = START_MARKER + "\n\n" + '\n\n    <div class="paper-gap" aria-hidden="true"></div>\n\n'.join(rendered_blocks) + "\n\n    " + END_MARKER
    updated = pattern.sub(replacement, html_text)
    RESEARCH_HTML.write_text(updated)


if __name__ == "__main__":
    sync_papers()
