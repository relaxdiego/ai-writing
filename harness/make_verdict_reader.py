#!/usr/bin/env python3
"""Build a collation galley: three states of the same answer, for a human verdict.

The paragraph galley asked one question about length and got a better answer
back: the rejections were about where the answer sits and what structure had
been dissolved. R02 then gained clauses for both, and the scorecard says they
worked. Nobody has read the result, which is backwards for a project where the
copyeditor is ground truth and the numbers are only evidence.

So this sets the same answer in its three states -- the frozen control, the
rules as they shipped, and the rules with the clauses -- and asks the two
questions the metrics cannot settle:

  Openings   does the answer arrive before the reasoning? K3 says it now does,
             at 36.7 words against a control of 28.4 and a shipped set of 64.9.
  Structure  the lists, tables and code blocks came back by the numbers. Are
             they real structure, or prose wearing bullets?

Markdown is rendered rather than stripped, unlike the paragraph galley, because
inline bold is one of the open questions: R06 forbids it and it returned to 2.07
against a control of 3.97, almost certainly to mark the new opening verdict.

Usage: make_verdict_reader.py <new-run> <shipped-run> <control-run> <out.html>
"""

import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "harness"))
from detectors import FENCE, LIST_ITEM, Doc  # noqa: E402

RULE_ROW = re.compile(r"^\|[\s:\-|]+\|$")


def blocks(raw: str) -> list[tuple[str, str]]:
    """Every block of a sample in document order, fences kept whole."""
    parts, last = [], 0
    for m in FENCE.finditer(raw):
        parts.append(("prose", raw[last:m.start()]))
        parts.append(("code", m.group(0)))
        last = m.end()
    parts.append(("prose", raw[last:]))

    out: list[tuple[str, str]] = []
    for kind, chunk in parts:
        if kind == "code":
            out.append(("code", chunk))
            continue
        for b in re.split(r"\n\s*\n", chunk):
            b = b.strip()
            if not b:
                continue
            if b.startswith("#"):
                out.append(("header", b))
            elif b.startswith("|"):
                out.append(("table", b))
            elif LIST_ITEM.match(b):
                out.append(("list", b))
            elif b.startswith(">"):
                out.append(("quote", b))
            else:
                out.append(("prose", b))
    return out


INLINE = [
    (re.compile(r"`([^`\n]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*([^*\n]+)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<![\w*])\*([^*\n]+)\*(?!\w)"), r"<i>\1</i>"),
]


def inline(text: str) -> str:
    """Escape first, then re-introduce only the three marks that matter.

    Bold survives on purpose. S5 is a ratified defect that partly returned, and
    the reader cannot judge whether the verdict line needs it while looking at
    text with the bold taken out.
    """
    out = html.escape(text)
    for pat, rep in INLINE:
        out = pat.sub(rep, out)
    return out


def render(kind: str, body: str) -> str:
    if kind == "code":
        inner = body.strip()
        inner = re.sub(r"^```[^\n]*\n?", "", inner)
        inner = re.sub(r"\n?```$", "", inner)
        return f'<pre class="code">{html.escape(inner)}</pre>'
    if kind == "list":
        items = [inline(re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", ln))
                 for ln in body.split("\n") if ln.strip()]
        tag = "ol" if re.match(r"^\s*\d+[.)]\s", body) else "ul"
        return f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>"
    if kind == "table":
        rows = [r for r in body.split("\n") if r.strip() and not RULE_ROW.match(r.strip())]
        cells = [[inline(c.strip()) for c in r.strip().strip("|").split("|")] for r in rows]
        if not cells:
            return ""
        head = "".join(f"<th>{c}</th>" for c in cells[0])
        rest = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                       for r in cells[1:])
        return (f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
                f"<tbody>{rest}</tbody></table></div>")
    if kind == "header":
        return f'<p class="mdh">{inline(body.lstrip("# ").strip())}</p>'
    if kind == "quote":
        return f'<blockquote>{inline(body.lstrip("> ").strip())}</blockquote>'
    return f"<p>{inline(body)}</p>"


def opening(bs: list[tuple[str, str]]) -> dict:
    """The first prose block and whatever follows it.

    K3 is measured on the first prose block, so that block is what carries the
    number. The next block is shown because "states it first and by itself" is a
    claim about two blocks, not one: an opening verdict that is immediately
    swallowed by its own reasoning has not been stated by itself.
    """
    idx = next((i for i, (k, _) in enumerate(bs) if k == "prose"), None)
    if idx is None:
        return {"words": 0, "sents": 0, "html": "", "lead": ""}
    kind, body = bs[idx]
    words = len(body.split())
    doc_sents = Doc._split(re.sub(r"\*\*|\*|`|_", "", body))
    tail = "".join(render(k, b) for k, b in bs[idx + 1:idx + 3])
    return {"words": words, "sents": len(doc_sents),
            "html": render(kind, body), "lead": tail,
            "pre": "".join(render(k, b) for k, b in bs[:idx] if k == "header")}


def structure(bs: list[tuple[str, str]]) -> list[dict]:
    """Every list, table and code block, with the prose line that introduces it."""
    out = []
    for i, (kind, body) in enumerate(bs):
        if kind not in ("list", "table", "code"):
            continue
        lead = ""
        for k, b in reversed(bs[:i]):
            if k == "prose":
                lead = b
                break
            if k in ("list", "table", "code"):
                break
        n = (len([l for l in body.split("\n") if l.strip()]) if kind != "code"
             else len(body.strip().split("\n")) - 2)
        out.append({"kind": kind, "n": max(n, 0),
                    "lead": inline(lead) if lead else "",
                    "html": render(kind, body)})
    return out


GLOSS = re.compile(
    r"^## (\w+) — (.+?)\n\n\*\*Wants\.\*\* (.*?)\n\n\*\*Owes\.\*\* (.*?)(?=\n\n## |\Z)",
    re.S | re.M)


def load_glosses(version: str) -> dict:
    path = REPO / "corpus" / f"{version}-glosses.md"
    if not path.is_file():
        return {}
    return {gid: {"name": name.strip(), "wants": " ".join(w.split()),
                  "owes": " ".join(o.split())}
            for gid, name, w, o in GLOSS.findall(path.read_text(encoding="utf-8"))}


# The prompts that produced a rejection in the paragraph galley, and what the
# copyeditor said. The galley opens filtered to these because they are the ones
# the clauses were written to fix; everything else is here to be checked, not
# read.
REJECTED = {
    "c02": "the alternative explanations should have been a list",
    "c04": "the control is directly saying it's a bad idea",
    "c07": "it's beating around the bush; the reader could miss it",
    "d04": "jumping too far ahead instead of explaining the sequence first",
    "d05": "too much prose here without examples",
}

STATES = [("control", "control", "no rules at all"),
          ("shipped", "shipped", "rules as they were"),
          ("now", "now", "rules with the clauses")]


def harvest(run_dir: Path) -> tuple[dict, dict]:
    man = json.loads((run_dir / "manifest.json").read_text())
    out = {}
    for s in man["samples"]:
        if not s["ok"] or s["substrate"] != "a":
            continue
        bs = blocks((run_dir / "samples" / f"{s['key']}.md").read_text(encoding="utf-8"))
        out[(s["prompt_id"], s["key"][-2:])] = {
            "key": s["key"], "register": s["register"],
            "opening": opening(bs), "structure": structure(bs),
        }
    return out, man


def build(new: Path, shipped: Path, control: Path, out: Path) -> None:
    N, man = harvest(new)
    S, _ = harvest(shipped)
    C, _ = harvest(control)

    glosses = load_glosses(man["corpus_version"])
    prompts = {}
    for p in man["corpus_prompts"]:
        body = (REPO / p["path"]).read_text(encoding="utf-8")
        prompts[p["id"]] = {
            "id": p["id"], "register": p["register"],
            "name": next((l.split(":", 1)[1].strip() for l in body.splitlines()
                          if l.startswith("name:")), p["id"]),
            "gloss": glosses.get(p["id"]),
            "rejected": REJECTED.get(p["id"], ""),
        }

    openings, structures = [], []
    for (pid, rep) in sorted(N, key=lambda k: (k[0] not in REJECTED, k[0], k[1])):
        row = {"pid": pid, "rep": rep, "key": N[(pid, rep)]["key"],
               "register": N[(pid, rep)]["register"], "states": []}
        for sid, _, _ in STATES:
            src = {"control": C, "shipped": S, "now": N}[sid].get((pid, rep))
            row["states"].append({"id": sid, **(src["opening"] if src else
                                                {"words": 0, "sents": 0,
                                                 "html": "", "lead": "", "pre": ""}),
                                  "key": src["key"] if src else ""})
        openings.append(row)

        got = N[(pid, rep)]["structure"]
        if got:
            ctl = C.get((pid, rep), {}).get("structure", [])
            structures.append({"pid": pid, "rep": rep, "key": N[(pid, rep)]["key"],
                               "register": N[(pid, rep)]["register"],
                               "items": got,
                               "control_n": {k: sum(1 for x in ctl if x["kind"] == k)
                                             for k in ("list", "table", "code")},
                               "control": ctl[:3]})

    data = {
        "run": new.name, "shipped_run": shipped.name, "control_run": control.name,
        "meta": {"model": man["model_requested"], "corpus": man["corpus_version"],
                 "style_sha": (man.get("style_sha256") or "")[:16],
                 "cli": man["cli_version"]},
        "prompts": prompts, "openings": openings, "structures": structures,
        "rejected": sorted(REJECTED),
    }
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size // 1024} KB, {len(openings)} openings, "
          f"{sum(len(s['items']) for s in structures)} structural blocks)")


TEMPLATE = r"""<title>Three States of an Answer</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Spectral:ital,wght@0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
:root{
  --paper:#eef0f2; --raised:#f8f9fa; --sunk:#e3e6e9;
  --ink:#14181d; --ink-soft:#535d68; --ink-faint:#828c96;
  --rule:#cfd5da; --hair:#e0e4e8;
  --src:#4a5568;  --src-wash:#4a556814;
  --was:#9c3b2e;  --was-wash:#9c3b2e14;
  --now:#2b4a8f;  --now-wash:#2b4a8f14;
  --focus:#2b4a8f;
  --ui:"Archivo",ui-sans-serif,system-ui,-apple-system,sans-serif;
  --prose:"Spectral",Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#121519; --raised:#191d23; --sunk:#0d1013;
  --ink:#e6e9ec; --ink-soft:#98a3ae; --ink-faint:#6b7681;
  --rule:#2a3038; --hair:#22272e;
  --src:#94a3b8; --src-wash:#94a3b81c;
  --was:#d9776a; --was-wash:#d9776a1c;
  --now:#7f9ce0; --now-wash:#7f9ce01c;
  --focus:#7f9ce0;
}}
:root[data-theme="dark"]{
  --paper:#121519; --raised:#191d23; --sunk:#0d1013;
  --ink:#e6e9ec; --ink-soft:#98a3ae; --ink-faint:#6b7681;
  --rule:#2a3038; --hair:#22272e;
  --src:#94a3b8; --src-wash:#94a3b81c;
  --was:#d9776a; --was-wash:#d9776a1c;
  --now:#7f9ce0; --now-wash:#7f9ce01c;
  --focus:#7f9ce0;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{background:var(--paper);color:var(--ink);font-family:var(--ui);
  line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:900px;margin:0 auto;padding:0 22px 110px}
:focus-visible{outline:2px solid var(--focus);outline-offset:3px;border-radius:1px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* masthead */
.mast{padding:52px 0 26px;border-bottom:2px solid var(--ink)}
.kicker{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-faint);display:flex;flex-wrap:wrap;gap:16px}
h1{font-family:var(--ui);font-weight:700;font-size:clamp(30px,4.8vw,44px);
  line-height:1.04;letter-spacing:-.02em;margin:14px 0 0;text-wrap:balance}
.stand{font-family:var(--prose);font-size:18px;line-height:1.62;color:var(--ink-soft);
  max-width:64ch;margin:14px 0 0}
.stand b{color:var(--ink);font-weight:600}

/* the two questions */
.asks{display:grid;gap:1px;background:var(--rule);border:1px solid var(--rule);
  margin:26px 0 0;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.ask{background:var(--raised);padding:16px 18px}
.ask h3{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-faint);margin:0 0 8px;font-weight:500}
.ask p{margin:0;font-size:14px;line-height:1.55;color:var(--ink)}
.ask .fig{font-family:var(--mono);font-size:12px;color:var(--ink-soft);
  margin-top:9px;font-variant-numeric:tabular-nums}
.ask .fig b{color:var(--now);font-weight:700}

/* rail */
.rail{position:sticky;top:0;z-index:9;background:var(--paper);padding:11px 0;
  margin:26px 0 0;border-bottom:1px solid var(--rule);
  display:flex;flex-wrap:wrap;gap:9px;align-items:center}
.seg{display:flex;border:1px solid var(--rule);background:var(--raised)}
.seg button{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;
  text-transform:uppercase;padding:7px 11px;border:0;background:none;cursor:pointer;
  color:var(--ink-soft);border-right:1px solid var(--rule)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.grow{flex:1}
.act{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  padding:7px 12px;border:1px solid var(--rule);background:var(--raised);
  color:var(--ink-soft);cursor:pointer}
.act:hover{color:var(--ink);border-color:var(--ink-faint)}
.tally{font-family:var(--mono);font-size:11px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums}

/* section heads */
h2{font-family:var(--ui);font-weight:700;font-size:24px;letter-spacing:-.015em;
  margin:54px 0 0;padding-bottom:9px;border-bottom:1px solid var(--ink)}
.sublede{font-size:14px;color:var(--ink-soft);margin:11px 0 0;max-width:66ch}

/* one answer, three states */
.item{margin:36px 0 0;border-top:1px solid var(--rule);padding-top:18px}
.item.rejected{border-top:2px solid var(--was)}
.hd{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline}
.pid{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--ink)}
.pname{font-family:var(--ui);font-weight:600;font-size:15px}
.tag{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-faint);border:1px solid var(--hair);padding:2px 6px}
.said{font-family:var(--prose);font-style:italic;font-size:14.5px;color:var(--was);
  margin:9px 0 0;max-width:64ch}
.said::before{content:"rejected: "}
.gloss{background:var(--sunk);padding:12px 15px;margin:12px 0 0;max-width:68ch;
  font-size:13.5px;line-height:1.55;color:var(--ink-soft)}
.gloss b{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-faint);font-weight:500;display:block;margin-bottom:3px}
.gloss p{margin:0 0 8px}
.gloss p:last-child{margin:0}

/* the pull: a proof rule in the gutter carries the state and its number */
.pulls{margin:16px 0 0;display:flex;flex-direction:column;gap:14px}
.pull{display:grid;grid-template-columns:82px 1fr;gap:0;align-items:stretch}
.gut{border-left:3px solid var(--c);padding:2px 12px 2px 10px;background:var(--w)}
.gut .st{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--c);font-weight:700}
.gut .n{font-family:var(--mono);font-size:20px;font-weight:700;color:var(--ink);
  font-variant-numeric:tabular-nums;line-height:1.2;margin-top:5px}
.gut .u{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);line-height:1.35}
.pull[data-s="control"]{--c:var(--src);--w:var(--src-wash)}
.pull[data-s="shipped"]{--c:var(--was);--w:var(--was-wash)}
.pull[data-s="now"]{--c:var(--now);--w:var(--now-wash)}
.body{padding:0 0 2px 18px;min-width:0}
.body>*:first-child{margin-top:0}
.body p{font-family:var(--prose);font-size:16.5px;line-height:1.62;margin:0 0 12px;
  max-width:66ch}
.body p:last-child{margin-bottom:0}
.body b{font-weight:600}
.body .mdh{font-family:var(--ui);font-weight:700;font-size:13px;letter-spacing:.01em;
  text-transform:none;color:var(--ink);margin:0 0 9px}
.body .mdh::before{content:"§ ";color:var(--ink-faint)}
.after{border-top:1px dashed var(--hair);margin-top:12px;padding-top:12px;opacity:.72}
.after::before{content:"what follows";font-family:var(--mono);font-size:9.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint);
  display:block;margin-bottom:7px}
ul,ol{font-family:var(--prose);font-size:16px;line-height:1.6;margin:0 0 12px;
  padding-left:22px;max-width:64ch}
li{margin:0 0 5px}
code{font-family:var(--mono);font-size:.85em;background:var(--sunk);padding:1px 4px}
pre.code{font-family:var(--mono);font-size:12.5px;line-height:1.5;background:var(--sunk);
  padding:12px 14px;overflow-x:auto;margin:0 0 12px;white-space:pre}
blockquote{border-left:2px solid var(--rule);margin:0 0 12px;padding-left:14px;
  font-family:var(--prose);font-size:16px;color:var(--ink-soft)}
.scroll{overflow-x:auto;margin:0 0 12px}
table{border-collapse:collapse;font-size:13.5px;width:100%;
  font-variant-numeric:tabular-nums}
th,td{border:1px solid var(--hair);padding:6px 10px;text-align:left;vertical-align:top}
th{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-faint);font-weight:500;background:var(--sunk)}
td{font-family:var(--prose);font-size:15px}

/* structure block */
.blk{margin:14px 0 0;border:1px solid var(--rule);background:var(--raised)}
.blk .cap{display:flex;flex-wrap:wrap;gap:9px;align-items:center;padding:9px 14px;
  border-bottom:1px solid var(--hair);background:var(--sunk)}
.blk .cap .k{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;font-weight:700;color:var(--now)}
.blk .cap .m{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint)}
.blk .in{padding:14px}
.lead{font-family:var(--prose);font-size:15px;color:var(--ink-soft);margin:0 0 11px;
  padding-left:11px;border-left:2px solid var(--hair);max-width:64ch}
.lead::before{content:"introduced by: ";font-family:var(--mono);font-size:9.5px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint)}
.cmp{font-family:var(--mono);font-size:11px;color:var(--ink-faint);margin:11px 0 0;
  padding-top:9px;border-top:1px dashed var(--hair)}

/* verdict */
.vd{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 0;align-items:center}
.vd button{font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;padding:7px 12px;border:1px solid var(--rule);
  background:var(--raised);color:var(--ink-soft);cursor:pointer}
.vd button:hover{border-color:var(--ink-faint);color:var(--ink)}
.vd button[aria-pressed="true"][data-v="pass"]{background:var(--now);border-color:var(--now);
  color:#fff}
.vd button[aria-pressed="true"][data-v="fail"]{background:var(--was);border-color:var(--was);
  color:#fff}
.vd input{flex:1;min-width:210px;font-family:var(--prose);font-size:15px;
  padding:7px 11px;border:1px solid var(--rule);background:var(--raised);color:var(--ink)}
.vd input::placeholder{color:var(--ink-faint);font-family:var(--ui);font-size:13px}

.foot{margin:64px 0 0;padding-top:18px;border-top:1px solid var(--rule);
  font-size:13px;color:var(--ink-faint);max-width:70ch}
.foot code{background:none;padding:0;color:var(--ink-soft)}
.empty{padding:34px 0;color:var(--ink-faint);font-size:14px}
@media(max-width:640px){
  .pull{grid-template-columns:1fr}
  .gut{border-left:0;border-top:3px solid var(--c);display:flex;gap:10px;
    align-items:baseline;padding:7px 10px}
  .gut .n{margin-top:0;font-size:16px}
  .body{padding:12px 0 0 0}
}
</style>

<div class="wrap">
<header class="mast">
  <div class="kicker">
    <span id="k-run"></span><span id="k-model"></span><span id="k-sha"></span>
    <span>substrate A</span>
  </div>
  <h1>Three states of an answer</h1>
  <p class="stand">The paragraph galley asked whether these answers were too long. They were
  not. <b>Ten were rejected for where the answer sat and what structure had been dissolved</b>,
  R02 gained a clause for each, and the scorecard says both worked. The scorecard cannot read.
  Here is the same answer three times: with no rules, with the rules as they shipped, and with
  the clauses.</p>

  <div class="asks">
    <div class="ask">
      <h3>Question one · openings</h3>
      <p>Does the answer arrive before the reasoning, or do you still have to go looking for it?</p>
      <p class="fig">opening paragraph &nbsp;28.4 control · 64.9 shipped · <b>36.7 now</b></p>
    </div>
    <div class="ask">
      <h3>Question two · structure</h3>
      <p>The lists, tables and code blocks came back by the numbers. Are they real structure, or
      prose wearing bullets?</p>
      <p class="fig">lists 0.80 → <b>4.63</b> · tables 0.00 → <b>0.27</b> · code 0.86 → <b>1.29</b></p>
    </div>
  </div>
</header>

<div class="rail">
  <div class="seg" role="group" aria-label="Which prompts">
    <button data-f="rejected" aria-pressed="true">the five you rejected</button>
    <button data-f="all" aria-pressed="false">all twelve</button>
  </div>
  <div class="seg" role="group" aria-label="Which section">
    <button data-sec="open" aria-pressed="true">openings</button>
    <button data-sec="struct" aria-pressed="false">structure</button>
  </div>
  <span class="grow"></span>
  <span class="tally" id="tally"></span>
  <button class="act" id="copy">Copy verdict</button>
</div>

<section id="sec-open">
  <h2>The openings</h2>
  <p class="sublede">The first paragraph of the answer, with whatever follows it, because
  &ldquo;states it first and by itself&rdquo; is a claim about two blocks and not one. The number in
  the gutter is that first paragraph&rsquo;s word count. Bold is left in: R06 forbids it, and it
  came back to mark these verdicts.</p>
  <div id="openings"></div>
</section>

<section id="sec-struct" hidden>
  <h2>What came back</h2>
  <p class="sublede">Every list, table and code block the rules now produce, with the prose line
  that introduces it, and what the control put on the same prompt. A list that is really a
  paragraph in bullets is the failure mode this clause could produce.</p>
  <div id="structures"></div>
</section>

<p class="foot" id="foot"></p>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const K = "verdict:" + DATA.run;
let store = {};
try { const r = localStorage.getItem(K); if (r) store = JSON.parse(r); } catch (e) {}
const save = () => { try { localStorage.setItem(K, JSON.stringify(store)); } catch (e) {} };

let filter = "rejected", section = "open";
const STATE_NAME = {control: "control", shipped: "shipped", now: "now"};
const STATE_SUB  = {control: "no rules", shipped: "rules as\nshipped", now: "with the\nclauses"};

$("k-run").textContent = DATA.run;
$("k-model").textContent = DATA.meta.model;
$("k-sha").textContent = "style " + DATA.meta.style_sha;
$("foot").innerHTML =
  "Control <code>" + esc(DATA.control_run) + "</code>. Shipped <code>" + esc(DATA.shipped_run) +
  "</code>. Now <code>" + esc(DATA.run) + "</code>, corpus " + esc(DATA.meta.corpus) +
  ", CLI " + esc(DATA.meta.cli) + ". Verdicts are kept in this browser only. " +
  "Built by <code>harness/make_verdict_reader.py</code>.";

const keep = pid => filter === "all" || DATA.rejected.includes(pid);

function gloss(p) {
  if (!p.gloss) return "";
  return '<div class="gloss"><b>what the person asking wanted</b><p>' + esc(p.gloss.wants) +
         '</p><b>what a good answer owes them</b><p>' + esc(p.gloss.owes) + "</p></div>";
}

function head(pid, rep, p, extra) {
  return '<div class="hd"><span class="pid">' + esc(pid) + "&thinsp;·&thinsp;" + esc(rep) +
    '</span><span class="pname">' + esc(p.name) + '</span><span class="tag">' +
    esc(p.register) + "</span>" + (extra || "") + "</div>" +
    (p.rejected ? '<p class="said">' + esc(p.rejected) + "</p>" : "");
}

function verdict(id, pass, fail, ph) {
  const v = store[id] || {};
  return '<div class="vd" data-id="' + id + '">' +
    '<button data-v="pass" aria-pressed="' + (v.v === "pass") + '">' + pass + "</button>" +
    '<button data-v="fail" aria-pressed="' + (v.v === "fail") + '">' + fail + "</button>" +
    '<input type="text" placeholder="' + ph + '" value="' + esc(v.n || "") + '"></div>';
}

function renderOpenings() {
  const rows = DATA.openings.filter(o => keep(o.pid));
  if (!rows.length) { $("openings").innerHTML = '<p class="empty">Nothing here.</p>'; return; }
  $("openings").innerHTML = rows.map(o => {
    const p = DATA.prompts[o.pid];
    const pulls = o.states.map(s =>
      '<div class="pull" data-s="' + s.id + '"><div class="gut">' +
        '<div class="st">' + STATE_NAME[s.id] + "</div>" +
        '<div class="n">' + s.words + "</div>" +
        '<div class="u">words<br>' + s.sents + (s.sents === 1 ? " sentence" : " sentences") +
      "</div></div>" +
      '<div class="body">' + (s.pre || "") + s.html +
        (s.lead ? '<div class="after">' + s.lead + "</div>" : "") +
      "</div></div>").join("");
    return '<article class="item' + (p.rejected ? " rejected" : "") + '">' +
      head(o.pid, o.rep, p) + gloss(p) +
      '<div class="pulls">' + pulls + "</div>" +
      verdict("open:" + o.key, "arrives first", "still buried",
              "what is wrong with it, in your words") + "</article>";
  }).join("");
}

function renderStructures() {
  const rows = DATA.structures.filter(s => keep(s.pid));
  if (!rows.length) { $("structures").innerHTML = '<p class="empty">Nothing here.</p>'; return; }
  $("structures").innerHTML = rows.map(s => {
    const p = DATA.prompts[s.pid];
    const cn = s.control_n;
    const blocks = s.items.map((it, i) =>
      '<div class="blk"><div class="cap"><span class="k">' + it.kind + "</span>" +
        '<span class="m">' + it.n + (it.kind === "table" ? " rows" :
          it.kind === "list" ? " items" : " lines") + "</span></div>" +
        '<div class="in">' + (it.lead ? '<p class="lead">' + it.lead + "</p>" : "") +
        it.html +
        verdict("blk:" + s.key + ":" + i, "real structure", "prose in bullets",
                "note") + "</div></div>").join("");
    return '<article class="item' + (p.rejected ? " rejected" : "") + '">' +
      head(s.pid, s.rep, p) + blocks +
      '<p class="cmp">on this prompt the control used ' + cn.list + " lists, " + cn.table +
      " tables, " + cn.code + " code blocks</p></article>";
  }).join("");
}

function tally() {
  const ids = Object.keys(store).filter(k => store[k] && store[k].v);
  const pass = ids.filter(k => store[k].v === "pass").length;
  $("tally").textContent = ids.length ? pass + " pass · " + (ids.length - pass) + " fail" : "";
}

function draw() { renderOpenings(); renderStructures(); tally(); }

document.addEventListener("click", e => {
  const f = e.target.closest("[data-f]");
  if (f) {
    filter = f.dataset.f;
    document.querySelectorAll("[data-f]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.f === filter)));
    draw(); return;
  }
  const sec = e.target.closest("[data-sec]");
  if (sec) {
    section = sec.dataset.sec;
    document.querySelectorAll("[data-sec]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.sec === section)));
    $("sec-open").hidden = section !== "open";
    $("sec-struct").hidden = section !== "struct";
    return;
  }
  const v = e.target.closest(".vd button");
  if (v) {
    const id = v.closest(".vd").dataset.id;
    const cur = store[id] || {};
    cur.v = cur.v === v.dataset.v ? "" : v.dataset.v;
    store[id] = cur; save();
    v.closest(".vd").querySelectorAll("button").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.v === cur.v)));
    tally();
  }
});

document.addEventListener("input", e => {
  if (e.target.matches(".vd input")) {
    const id = e.target.closest(".vd").dataset.id;
    store[id] = Object.assign({}, store[id], {n: e.target.value});
    save();
  }
});

$("copy").addEventListener("click", async () => {
  const L = ["# Collation verdict — " + DATA.run, "",
    "Control `" + DATA.control_run + "`, shipped `" + DATA.shipped_run + "`.", ""];
  const oc = DATA.openings.filter(o => store["open:" + o.key] && store["open:" + o.key].v);
  if (oc.length) {
    L.push("## Openings", "", "| prompt | register | control | shipped | now | verdict | note |",
           "|---|---|---:|---:|---:|---|---|");
    oc.forEach(o => {
      const v = store["open:" + o.key], w = {};
      o.states.forEach(s => w[s.id] = s.words);
      L.push("| " + o.pid + "·" + o.rep + " | " + o.register + " | " + w.control + " | " +
             w.shipped + " | " + w.now + " | " +
             (v.v === "pass" ? "arrives first" : "still buried") + " | " + (v.n || "") + " |");
    });
    L.push("");
  }
  const sc = [];
  DATA.structures.forEach(s => s.items.forEach((it, i) => {
    const v = store["blk:" + s.key + ":" + i];
    if (v && v.v) sc.push([s, it, v]);
  }));
  if (sc.length) {
    L.push("## Structure", "", "| prompt | kind | size | verdict | note |",
           "|---|---|---:|---|---|");
    sc.forEach(([s, it, v]) => L.push("| " + s.pid + "·" + s.rep + " | " + it.kind + " | " +
      it.n + " | " + (v.v === "pass" ? "real" : "prose in bullets") + " | " + (v.n || "") + " |"));
  }
  if (L.length === 4) L.push("_Nothing marked yet._");
  const out = L.join("\n");
  try { await navigator.clipboard.writeText(out); }
  catch (e) {
    const t = document.createElement("textarea");
    t.value = out; document.body.appendChild(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  $("copy").textContent = "Copied";
  setTimeout(() => { $("copy").textContent = "Copy verdict"; }, 1600);
});

draw();
</script>
"""


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__.strip().splitlines()[-1])
    build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(),
          Path(sys.argv[3]).resolve(), Path(sys.argv[4]))
