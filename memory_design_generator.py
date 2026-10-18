#!/usr/bin/env python3
"""Memory-design mechanism explainer — house minimal schematic.
Every box/arrow/number traces to MEMORY_DESIGN.md. TextAudit mandatory."""
import sys
sys.path.insert(0, "/opt/data/scripts")
from svg_text_audit import TextAudit

W, H = 1500, 1000
M = 165
INK, GRAY, FAINT = "#272a29", "#58605e", "#e3e6df"
BLUE, SLATE, WARM = "#2251ff", "#6e7e8e", "#d9481f"

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="DejaVu Sans">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
audit = TextAudit(W, H)

def text(x, y, s, size, fill, bold=False, anchor="start", ls=0):
    audit.add(x, y, s, size, bold, anchor)
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                f'{"font-weight=\"bold\" " if bold else ""}text-anchor="{anchor}"'
                + (f' letter-spacing="{ls}"' if ls else "") + f'>{s}</text>')

def box(x, y, w, h, title, subs, accent):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#ffffff" stroke="{FAINT}" stroke-width="1.5"/>')
    svg.append(f'<rect x="{x}" y="{y}" width="4" height="{h}" rx="2" fill="{accent}"/>')
    text(x + 18, y + 30, title, 15, accent, bold=True, ls=1)
    yy = y + 52
    for s in subs:
        text(x + 18, yy, s, 12.5, GRAY)
        yy += 20

def arrow(x0, y, x1, label=None, lab_dy=14):
    svg.append(f'<line x1="{x0}" y1="{y}" x2="{x1 - 9}" y2="{y}" stroke="{INK}" stroke-width="2"/>')
    svg.append(f'<polygon points="{x1},{y} {x1 - 12},{y - 6} {x1 - 12},{y + 6}" fill="{INK}"/>')
    if label:
        text((x0 + x1) / 2, y - lab_dy, label, 12, GRAY, anchor="middle")

def hairline(y):
    svg.append(f'<line x1="{M}" y1="{y}" x2="{W - M}" y2="{y}" stroke="{FAINT}" stroke-width="1"/>')

# ---- title ----
text(M, 112, "THE MEMORY DESIGN BEHIND THE 70%", 14, BLUE, bold=True, ls=3)
text(M, 156, "One deliberate pass, three boring layers", 33, INK, bold=True)
text(M, 186, "how the winning arm's memory system actually works - full design notes: MEMORY_DESIGN.md in the repo", 14.5, GRAY)
hairline(218)

# ---- flow: sessions -> curation pass -> three stores ----
box(M, 330, 235, 100, "SESSIONS", ["we just... talk", "no capture machinery"], GRAY)
arrow(M + 235 + 12, 380, 500, "when it matters", 12)
box(500, 310, 300, 140, "ONE CURATION PASS", ["write down what matters", "cite the source - prune the stale"], BLUE)
arrow(800 + 12, 380, 872)

stores_x, stores_w = 872, 380
box(stores_x, 260, stores_w, 90, "HOT MEMORY", ["~2k chars, curated profile - every session"], BLUE)
box(stores_x, 360, stores_w, 90, "COLD STORAGE", ["markdown + git vault - searched on demand"], SLATE)
box(stores_x, 460, stores_w, 90, "PROCEDURAL SKILLS", ["how-to docs - load only when a task matches"], GRAY)

# next-session strip
text(M, 583, "NEXT SESSION: the hot layer rides along (~1.3k tokens) - cold + skills load only when needed.", 13, INK, bold=True)
text(M, 605, "no vectors anywhere. plain text, end to end.", 13, GRAY)

# ---- contrast strip ----
hairline(630)
text(M, 678, "THE PIPELINE WAY", 13.5, WARM, bold=True, ls=2)
text(M, 704, "~26 automatic LLM passes per persona to build the store", 13.5, GRAY)
text(M, 724, "opaque layers - if recall is wrong you are guessing", 13.5, GRAY)
text(M, 744, "benchmark result: 40%", 14.5, WARM, bold=True)

text(M + 560, 678, "THE DELIBERATE WAY", 13.5, BLUE, bold=True, ls=2)
text(M + 560, 704, "1 curation pass, then plain text you can actually read", 13.5, GRAY)
text(M + 560, 724, "every fact traces to a source - auditable by construction", 13.5, GRAY)
text(M + 560, 744, "benchmark result: 70%", 14.5, BLUE, bold=True)

# ---- footer ----
hairline(800)
text(M, 830, "Illustrative schematic of the deployed design - benchmark arm B models the curation pass, not the full stack", 11.5, GRAY)
text(M, 852, "No data plotted here beyond the cited benchmark results (n=50, PersonaMem-v2, Wilson 95% CIs)", 11.5, GRAY)
text(M, 874, "Source: MEMORY_DESIGN.md - github.com/Devvor/agent-memory-benchmark - run 2026-10-17/18", 11.5, GRAY)

assert "ehwangah" not in "".join(svg)
audit.assert_clean()
svg.append("</svg>")
open("/opt/data/projects/tdai-bench/chart_memory_design.svg", "w").write("\n".join(svg))
print("SVG written, audit clean")
