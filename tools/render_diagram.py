"""Render docs/architecture.svg as a committed, self-contained SVG.

GitHub does not reliably render a Mermaid fence (ci-and-rendering-traps.md trap 7),
so the architecture diagram is authored directly as valid SVG and committed. It
follows traps 8 to 10: labels are real <text> (no foreignObject), the root element
has intrinsic width and height taken from the viewBox, and a light background
rectangle is painted so edge labels stay legible in a dark theme. The diagram
source in plain words is kept in README under a non-mermaid fence.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "docs" / "architecture.svg"

WIDTH, HEIGHT = 900, 460

_BOX = (
    '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
    'fill="{fill}" stroke="#334155" stroke-width="1.5"/>'
)
_TITLE = (
    '<text x="{cx}" y="{ty}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
    'font-size="15" font-weight="bold" fill="#0f172a">{text}</text>'
)
_SUB = (
    '<text x="{cx}" y="{sy}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
    'font-size="12" fill="#334155">{text}</text>'
)
_ARROW = '<path d="{d}" fill="none" stroke="#475569" stroke-width="2" marker-end="url(#a)"/>'
_EDGE_LABEL = (
    '<text x="{x}" y="{y}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
    'font-size="11" fill="#475569">{text}</text>'
)


def _box(x, y, w, h, title, sub, fill):
    cx = x + w / 2
    parts = [_BOX.format(x=x, y=y, w=w, h=h, fill=fill)]
    parts.append(_TITLE.format(cx=cx, ty=y + 26, text=title))
    parts.append(_SUB.format(cx=cx, sy=y + 45, text=sub))
    return "\n".join(parts)


def build_svg() -> str:
    boxes = [
        _box(30, 60, 180, 70, "program.csv", "seeded fixture, 16 tasks", "#e0f2fe"),
        _box(30, 300, 180, 70, "generator", "cost on calendar,", "#e0f2fe"),
        _box(360, 60, 190, 70, "EVM engine", "PV / EV / AC -> CPI, SPI", "#dcfce7"),
        _box(360, 300, 190, 70, "illusion detector", "burn-healthy vs EV-late", "#fef9c3"),
        _box(690, 60, 180, 70, "report / gate", "exit 0 / 1 / 2", "#ede9fe"),
        _box(690, 300, 180, 70, "experiments", "docs/experiments/*.json", "#ede9fe"),
    ]
    arrows = [
        _ARROW.format(d="M210 95 L360 95"),            # csv -> engine
        _ARROW.format(d="M120 300 L120 130"),          # generator -> csv
        _ARROW.format(d="M550 95 L690 95"),            # engine -> report
        _ARROW.format(d="M455 130 L455 300"),          # engine -> illusion
        _ARROW.format(d="M550 335 L690 335"),          # illusion -> experiments
        _ARROW.format(d="M780 130 L780 300"),          # report -> experiments
    ]
    labels = [
        _EDGE_LABEL.format(x=285, y=88, text="cumulative curves"),
        _EDGE_LABEL.format(x=120, y=220, text="writes"),
        _EDGE_LABEL.format(x=620, y=88, text="per week"),
        _EDGE_LABEL.format(x=520, y=220, text="SV in dollars"),
        _EDGE_LABEL.format(x=620, y=328, text="weekly verdicts"),
    ]
    defs = (
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0 L10 5 L0 10 z" fill="#475569"/></marker></defs>'
    )
    heading = (
        '<text x="450" y="36" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
        'font-size="18" font-weight="bold" fill="#0f172a">'
        'earned-value: one spend gap, split into cost and schedule</text>'
    )
    body = "\n".join([defs, heading, *boxes, *arrows, *labels])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">\n'
        f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="#f8fafc"/>\n'
        f"{body}\n</svg>\n"
    )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg())
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
