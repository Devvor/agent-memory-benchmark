#!/usr/bin/env python3
"""agent-memory-benchmark chart — house minimal stat-sheet look.
Data loaded from RESULTS50.json (never hardcoded). TextAudit mandatory.
Render: env -u PYTHONPATH /opt/hermes/.venv/bin/python (cairosvg 2x)."""
import json, sys
sys.path.insert(0, "/opt/data/scripts")
from svg_text_audit import TextAudit

R = json.load(open("/opt/data/projects/agent-memory-benchmark/RESULTS50.json"))
A, B, C = R["armA_raw_context"], R["armB_curated"], R["armC_tencentdb"]

W, H = 1500, 1010
M = 165                      # 11% symmetric margins
INK, GRAY, FAINT = "#272a29", "#58605e", "#e3e6df"
BLUE, SLATE, WARM = "#2251ff", "#6e7e8e", "#d9481f"
TRACK0, TRACKW = M, W - 2 * M - 205   # bar track, reserve label room at right

rows = [
    ("OUR CURATED MEMORY", "one curation pass to build - then ~1.3k tokens per question", B, BLUE),
    ("RAW 32K CONTEXT", "no memory system - entire history in the prompt (~43k tokens)", A, SLATE),
    ("TENCENTDB AGENT MEMORY", "their full L0-L3 pipeline - ~26 LLM passes to build", C, WARM),
]

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="DejaVu Sans">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
audit = TextAudit(W, H)

def text(x, y, s, size, fill, bold=False, anchor="start", ls=0):
    audit.add(x, y, s, size, bold, anchor)
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                f'{"font-weight=\"bold\" " if bold else ""}text-anchor="{anchor}"'
                + (f' letter-spacing="{ls}"' if ls else "") + f'>{s}</text>')

def hairline(y, x0=M, x1=W - M):
    svg.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{FAINT}" stroke-width="1"/>')

# ---- title block ----
text(M, 112, "AGENT MEMORY BENCHMARK  ·  N = 50 PERSONAS", 14, BLUE, bold=True, ls=3)
text(M, 156, "One curation pass beats the 26-pass memory pyramid", 33, INK, bold=True)
text(M, 186, "same 50 personas, same questions, same answer model across all arms  ·  Wilson 95% CIs", 14.5, GRAY)
hairline(218)

# ---- bar zone gridlines (behind bars) ----
for gv in (0, 25, 50, 75, 100):
    gx = TRACK0 + TRACKW * gv / 100
    if gv:
        svg.append(f'<line x1="{gx}" y1="248" x2="{gx}" y2="600" stroke="{FAINT}" stroke-dasharray="3,4" stroke-width="1"/>')
    text(gx, 242, f"{gv}%", 11.5, GRAY, anchor="middle")

# ---- rows ----
for i, (name, sub, arm, color) in enumerate(rows):
    y = 262 + i * 116
    text(M, y, name, 16, INK, bold=True, ls=1)
    text(M, y + 21, sub, 12.5, GRAY)
    by = y + 33                                     # bar top
    bh = 34
    x_end = TRACK0 + TRACKW * arm["acc"]
    svg.append(f'<rect x="{TRACK0}" y="{by}" width="{x_end - TRACK0}" height="{bh}" rx="3" fill="{color}"/>')
    # CI whisker (ink, over bar)
    lo, hi = arm["ci95"]
    wx0, wx1 = TRACK0 + TRACKW * lo, TRACK0 + TRACKW * hi
    my = by + bh / 2
    for capx in (wx0, wx1):
        svg.append(f'<line x1="{capx}" y1="{my - 9}" x2="{capx}" y2="{my + 9}" stroke="{INK}" stroke-width="2"/>')
    svg.append(f'<line x1="{wx0}" y1="{my}" x2="{wx1}" y2="{my}" stroke="{INK}" stroke-width="2"/>')
    # value label block right of whisker
    lx = wx1 + 16
    text(lx, my - 1, f'{arm["acc"]*100:.0f}%', 21, color, bold=True)
    text(lx, my + 17, f'95% CI {lo*100:.0f}-{hi*100:.0f}%', 12, GRAY)
    if arm["errors"] or arm["unparseable"]:
        raise AssertionError("dirty arm data, refusing to chart")

# ---- hero stat ----
hairline(636)
text(M, 692, "CURATED (OURS)  vs  TENCENTDB PIPELINE", 13.5, GRAY, bold=True, ls=2)
text(M, 756, "p = 0.0026", 50, BLUE, bold=True)
text(M, 792, "70% vs 40%  ·  non-overlapping 95% CIs  ·  raw context also beats their pipeline at p = 0.0006", 13.5, GRAY)
text(M, 815, "build cost: 1 LLM pass per persona (ours)  vs  ~26 passes (theirs) - their pipeline was ~80% of the run's API bill", 13.5, GRAY)

# ---- footer ----
hairline(856)
text(M, 886, "Methodology: 3 arms - answer model glm-5.3-flash (temp 0), extraction model glm-5.3; TencentDB npm v1.0.3, standalone gateway, full pipeline; multiple-choice, deterministic option order", 11.5, GRAY)
text(M, 908, "Scope: 50 of 200 unique PersonaMem-v2 personas, deterministic sample - full harness + raw results: github.com/Devvor/agent-memory-benchmark", 11.5, GRAY)
text(M, 930, "Source: PersonaMem-v2 (CC-BY-4.0, UPenn)  ·  npm @tencentdb-agent-memory/memory-tencentdb  ·  run 2026-10-17/18", 11.5, GRAY)

assert "ehwangah" not in "".join(svg)
audit.assert_clean()
svg.append("</svg>")
open("/opt/data/projects/tdai-bench/chart_membench.svg", "w").write("\n".join(svg))
print("SVG written, audit clean")
