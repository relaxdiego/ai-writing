#!/usr/bin/env python3
"""Build a blind read: two whole answers to the same question, no numbers.

Every galley in this repo so far has cut the samples into pieces the size of a
detector -- opening paragraphs, single paragraphs, the lines that introduce a
list. A person cannot feel a prose change from fragments, and the whole project
rests on a felt change. So this shows the thing itself: one question, the answer
the model gives with no rules, and the answer it gives under style/rules.md,
complete, from first word to last.

Nothing on the page is measured. No word counts, no detector names, no rates, no
scorecard. The only question is which one reads better.

It is blind. Which answer is on the left is decided by a hash of the sample key,
so it is stable across rebuilds but not guessable from the page, and the labels
stay hidden until the pair is marked. The copyeditor has been told what the rules
say, and a labelled pair invites them to find the rules rather than read the
prose. Reveal is per pair and comes after the verdict.

Usage: make_plain_reader.py <run-dir> <control-dir> <out.html> [--repeat N]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "harness"))
from make_verdict_reader import blocks, render  # noqa: E402
from make_paragraph_reader import load_glosses  # noqa: E402


def answers(run_dir: Path, repeat: int) -> dict[str, dict]:
    """Every substrate-A answer at the given repeat, rendered whole."""
    man = json.loads((run_dir / "manifest.json").read_text())
    out = {}
    for s in man["samples"]:
        if not s["ok"] or s["substrate"] != "a" or s["repeat"] != repeat:
            continue
        raw = (run_dir / "samples" / f"{s['key']}.md").read_text(encoding="utf-8")
        out[s["prompt_id"]] = {
            "key": s["key"],
            "html": "".join(render(k, b) for k, b in blocks(raw)),
        }
    return out, man


def side(key: str) -> int:
    """Which column the ruled answer takes. Stable, and not guessable."""
    return hashlib.sha256(key.encode()).digest()[0] & 1


def build(run: Path, ctrl: Path, out: Path, repeat: int) -> None:
    ruled, man = answers(run, repeat)
    plain, _ = answers(ctrl, repeat)

    glosses = load_glosses(man["corpus_version"])
    pairs = []
    for p in man["corpus_prompts"]:
        pid = p["id"]
        if pid not in ruled or pid not in plain:
            continue
        body = (REPO / p["path"]).read_text(encoding="utf-8")
        g = glosses.get(pid)
        flip = side(ruled[pid]["key"])
        cols = [plain[pid], ruled[pid]] if flip else [ruled[pid], plain[pid]]
        pairs.append({
            "pid": pid,
            "register": p["register"],
            "name": next((l.split(":", 1)[1].strip() for l in body.splitlines()
                          if l.startswith("name:")), pid),
            "asked": body.split("---", 2)[2].strip(),
            "gloss": g,
            # "ruled" names the column the rules produced, and the page does not
            # read it until the pair carries a verdict.
            "ruled": "B" if flip else "A",
            "cols": [{"label": "A", "html": cols[0]["html"]},
                     {"label": "B", "html": cols[1]["html"]}],
        })

    data = {"run": run.name, "control_run": ctrl.name, "repeat": repeat,
            "corpus": man["corpus_version"], "pairs": pairs}
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size // 1024} KB, {len(pairs)} pairs, repeat {repeat})")


TEMPLATE = r"""<title>The Blind Read</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,400;7..72,500;7..72,600&family=Archivo:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root{
  --paper:#eef0f2; --leaf:#fbfcfc; --sunk:#e3e6e9;
  --ink:#14181d; --ink-soft:#535d68; --ink-faint:#828c96;
  --rule:#cfd5da; --hair:#e0e4e8;
  --pick:#1f6b6b; --pick-wash:#1f6b6b12;
  --focus:#1f6b6b;
  --ui:"Archivo",ui-sans-serif,system-ui,-apple-system,sans-serif;
  --read:"Literata",Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#121519; --leaf:#191d22; --sunk:#0d1013;
  --ink:#e8eaec; --ink-soft:#9aa4ae; --ink-faint:#6b7681;
  --rule:#2a3038; --hair:#22272e;
  --pick:#6cbdb6; --pick-wash:#6cbdb61a;
  --focus:#6cbdb6;
}}
:root[data-theme="dark"]{
  --paper:#121519; --leaf:#191d22; --sunk:#0d1013;
  --ink:#e8eaec; --ink-soft:#9aa4ae; --ink-faint:#6b7681;
  --rule:#2a3038; --hair:#22272e;
  --pick:#6cbdb6; --pick-wash:#6cbdb61a;
  --focus:#6cbdb6;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{background:var(--paper);color:var(--ink);font-family:var(--ui);
  line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:0 24px 120px}
:focus-visible{outline:2px solid var(--focus);outline-offset:3px;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}

.mast{padding:56px 0 26px;max-width:66ch}
h1{font-family:var(--read);font-weight:600;font-size:clamp(32px,5vw,46px);
  line-height:1.08;letter-spacing:-.02em;margin:0;text-wrap:balance}
.stand{font-family:var(--read);font-size:18.5px;line-height:1.68;
  color:var(--ink-soft);margin:18px 0 0}
.stand b{color:var(--ink);font-weight:600}
.stand+.stand{margin-top:13px}

.rail{position:sticky;top:0;z-index:9;background:var(--paper);padding:12px 0;
  margin:24px 0 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);
  display:flex;flex-wrap:wrap;gap:9px;align-items:center}
.seg{display:flex;border:1px solid var(--rule);background:var(--leaf)}
.seg button{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;
  text-transform:uppercase;padding:7px 11px;border:0;background:none;cursor:pointer;
  color:var(--ink-soft);border-right:1px solid var(--rule)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.grow{flex:1}
.act{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;
  padding:7px 12px;border:1px solid var(--rule);background:var(--leaf);
  color:var(--ink-soft);cursor:pointer}
.act:hover{color:var(--ink);border-color:var(--ink-faint)}
.count{font-family:var(--mono);font-size:11px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums}

/* one question */
.pair{margin:64px 0 0;padding-top:26px;border-top:1px solid var(--rule)}
.pair:first-child{border-top:0}
.qhd{display:flex;flex-wrap:wrap;gap:11px;align-items:baseline}
.qname{font-family:var(--read);font-weight:600;font-size:23px;letter-spacing:-.01em}
.qtag{font-family:var(--mono);font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--ink-faint);border:1px solid var(--hair);padding:2px 7px}

.asked{margin:16px 0 0;background:var(--sunk);border-left:3px solid var(--rule);
  padding:16px 20px;max-width:78ch}
.asked h4{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-faint);margin:0 0 9px;font-weight:500}
.asked .qbody{font-family:var(--read);font-size:15.5px;line-height:1.62;
  color:var(--ink-soft);white-space:pre-wrap}
.asked .gloss{margin:14px 0 0;padding-top:13px;border-top:1px dashed var(--hair);
  font-family:var(--read);font-size:15px;line-height:1.62;color:var(--ink-soft)}
.asked .gloss b{font-family:var(--mono);font-size:9.5px;letter-spacing:.11em;
  text-transform:uppercase;color:var(--ink-faint);font-weight:500;display:block;
  margin-bottom:3px}
.asked .gloss p{margin:0 0 9px}
.asked .gloss p:last-child{margin:0}

/* the two answers */
.cols{display:grid;gap:22px;margin:24px 0 0;grid-template-columns:1fr 1fr;
  align-items:start}
.cols.one{grid-template-columns:1fr;max-width:72ch}
.leaf{background:var(--leaf);border:1px solid var(--hair);padding:26px 30px 30px;
  min-width:0}
.leaf.chosen{border-color:var(--pick);box-shadow:inset 3px 0 0 var(--pick)}
.leafhd{display:flex;gap:10px;align-items:baseline;margin:0 0 18px;
  padding-bottom:11px;border-bottom:1px solid var(--hair)}
.leafhd .ab{font-family:var(--mono);font-size:13px;font-weight:500;color:var(--ink);
  letter-spacing:.08em}
.leafhd .said{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--pick)}

/* the prose itself, which is the whole point */
.leaf p{font-family:var(--read);font-size:16.5px;line-height:1.72;margin:0 0 17px}
.leaf p:last-child{margin-bottom:0}
.leaf b{font-weight:600}
.leaf i{font-style:italic}
.leaf .mdh{font-family:var(--ui);font-weight:700;font-size:14.5px;letter-spacing:.005em;
  margin:26px 0 12px;color:var(--ink)}
.leaf ul,.leaf ol{font-family:var(--read);font-size:16px;line-height:1.68;
  margin:0 0 17px;padding-left:23px}
.leaf li{margin:0 0 8px}
.leaf code{font-family:var(--mono);font-size:.82em;background:var(--sunk);padding:1px 4px}
.leaf pre.code{font-family:var(--mono);font-size:12.5px;line-height:1.55;
  background:var(--sunk);padding:14px 16px;overflow-x:auto;margin:0 0 17px;
  white-space:pre}
.leaf blockquote{border-left:2px solid var(--rule);margin:0 0 17px;padding-left:16px;
  font-family:var(--read);color:var(--ink-soft)}
.leaf .scroll{overflow-x:auto;margin:0 0 17px}
.leaf table{border-collapse:collapse;font-size:14px;width:100%}
.leaf th,.leaf td{border:1px solid var(--hair);padding:7px 11px;text-align:left;
  vertical-align:top}
.leaf th{font-family:var(--mono);font-size:10px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink-faint);font-weight:500;background:var(--sunk)}
.leaf td{font-family:var(--read)}

/* the only question the page asks */
.ask{margin:26px 0 0;padding:18px 20px;background:var(--leaf);
  border:1px solid var(--rule)}
.ask .q{font-family:var(--read);font-size:16.5px;margin:0 0 13px}
.vd{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.vd button{font-family:var(--ui);font-weight:500;font-size:14px;padding:9px 15px;
  border:1px solid var(--rule);background:var(--paper);color:var(--ink-soft);
  cursor:pointer}
.vd button:hover{border-color:var(--ink-faint);color:var(--ink)}
.vd button[aria-pressed="true"]{background:var(--pick);border-color:var(--pick);color:#fff}
.vd input{flex:1;min-width:240px;font-family:var(--read);font-size:15.5px;
  padding:9px 13px;border:1px solid var(--rule);background:var(--paper);color:var(--ink)}
.vd input::placeholder{color:var(--ink-faint);font-family:var(--ui);font-size:13.5px}
.reveal{margin:13px 0 0;display:flex;gap:11px;align-items:center;flex-wrap:wrap}
.reveal .msg{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint)}
.reveal .msg b{color:var(--pick);font-weight:500}

.foot{margin:72px 0 0;padding-top:20px;border-top:1px solid var(--rule);
  font-size:13px;color:var(--ink-faint);max-width:70ch;line-height:1.6}
.foot code{color:var(--ink-soft)}
@media(max-width:900px){.cols{grid-template-columns:1fr}}
</style>

<div class="wrap">
<header class="mast">
  <h1>The blind read</h1>
  <p class="stand">Twelve questions. Each one answered twice by the same model: once with no
  instructions, once under the four style rules. <b>Both answers are here whole, from the first
  word to the last.</b></p>
  <p class="stand">There are no numbers on this page. Nothing is counted, nothing is scored, and
  no detector is named. <b>You are not told which answer is which</b> until you have said which
  one reads better &mdash; you know what the rules say, and a label would have you hunting for
  them instead of reading.</p>
  <p class="stand">Read both. Pick one. If neither is better, say that: it is the answer that
  matters most, and it is the one the measurements cannot give.</p>
</header>

<div class="rail">
  <div class="seg" role="group" aria-label="Which questions">
    <button data-f="all" aria-pressed="true">all twelve</button>
    <button data-f="conversational" aria-pressed="false">replies</button>
    <button data-f="document" aria-pressed="false">documents</button>
  </div>
  <div class="seg" role="group" aria-label="Layout">
    <button data-l="two" aria-pressed="true">side by side</button>
    <button data-l="one" aria-pressed="false">one above the other</button>
  </div>
  <span class="grow"></span>
  <span class="count" id="count"></span>
  <button class="act" id="copy">Copy verdict</button>
</div>

<div id="pairs"></div>

<p class="foot" id="foot"></p>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const K = "blindread:" + DATA.run + ":r" + DATA.repeat;
let store = {};
try { const r = localStorage.getItem(K); if (r) store = JSON.parse(r); } catch (e) {}
const save = () => { try { localStorage.setItem(K, JSON.stringify(store)); } catch (e) {} };

let filter = "all", layout = "two";
const VERDICT = {A: "A reads better", B: "B reads better", none: "No difference"};

$("foot").innerHTML =
  "Twelve questions from corpus " + esc(DATA.corpus) + ", answered at repeat " + DATA.repeat +
  ". One arm has no instructions; the other runs under <code>style/rules.md</code>. Which " +
  "arm takes which column is fixed per question and does not follow a pattern. Verdicts are " +
  "kept in this browser and in the copied table. Built by " +
  "<code>harness/make_plain_reader.py</code>.";

function gloss(p) {
  if (!p.gloss) return "";
  return '<div class="gloss"><b>what the person asking wanted</b><p>' + esc(p.gloss.wants) +
    '</p><b>what a good answer owes them</b><p>' + esc(p.gloss.owes) + "</p></div>";
}

function pair(p) {
  const v = store[p.pid] || {};
  const done = !!v.v;
  const cols = p.cols.map(c => {
    const chosen = done && v.v === c.label;
    // The label is only ever attached after a verdict exists, so the first read
    // cannot be steered by it.
    const said = done
      ? '<span class="said">' + (p.ruled === c.label ? "under the rules" : "no instructions") +
        "</span>"
      : "";
    return '<article class="leaf' + (chosen ? " chosen" : "") + '">' +
      '<div class="leafhd"><span class="ab">' + c.label + "</span>" + said + "</div>" +
      c.html + "</article>";
  }).join("");

  const btns = ["A", "B", "none"].map(k =>
    '<button data-v="' + k + '" aria-pressed="' + (v.v === k) + '">' + VERDICT[k] +
    "</button>").join("");

  return '<section class="pair" data-r="' + p.register + '">' +
    '<div class="qhd"><span class="qname">' + esc(p.name) + '</span>' +
    '<span class="qtag">' + esc(p.register) + "</span></div>" +
    '<div class="asked"><h4>what was asked</h4><div class="qbody">' + esc(p.asked) +
    "</div>" + gloss(p) + "</div>" +
    '<div class="cols ' + (layout === "one" ? "one" : "") + '">' + cols + "</div>" +
    '<div class="ask"><p class="q">Which of these reads better?</p>' +
    '<div class="vd" data-id="' + p.pid + '">' + btns +
    '<input type="text" placeholder="what made the difference, in your words" value="' +
    esc(v.n || "") + '"></div>' +
    (done
      ? '<div class="reveal"><span class="msg">You picked ' +
        (v.v === "none" ? "neither" : v.v) + ". " + p.ruled + " is the one <b>under the rules</b>." +
        "</span></div>"
      : "") +
    "</div></section>";
}

function draw() {
  const rows = DATA.pairs.filter(p => filter === "all" || p.register === filter);
  $("pairs").innerHTML = rows.map(pair).join("");
  const done = DATA.pairs.filter(p => (store[p.pid] || {}).v).length;
  $("count").textContent = done + " of " + DATA.pairs.length + " read";
}

document.addEventListener("click", e => {
  const f = e.target.closest("[data-f]");
  if (f) {
    filter = f.dataset.f;
    document.querySelectorAll("[data-f]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.f === filter)));
    draw(); return;
  }
  const l = e.target.closest("[data-l]");
  if (l) {
    layout = l.dataset.l;
    document.querySelectorAll("[data-l]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.l === layout)));
    draw(); return;
  }
  const v = e.target.closest(".vd button");
  if (v) {
    const id = v.closest(".vd").dataset.id;
    const cur = store[id] || {};
    cur.v = cur.v === v.dataset.v ? "" : v.dataset.v;
    store[id] = cur; save();
    const y = v.getBoundingClientRect().top;
    draw();
    const again = document.querySelector('.vd[data-id="' + id + '"] button[data-v="' +
      v.dataset.v + '"]');
    if (again) window.scrollBy(0, again.getBoundingClientRect().top - y);
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
  const L = ["# The blind read — repeat " + DATA.repeat, "",
    "No instructions `" + DATA.control_run + "`, under the rules `" + DATA.run + "`.", "",
    "| question | register | picked | which arm | what made the difference |",
    "|---|---|---|---|---|"];
  let ruled = 0, plain = 0, none = 0;
  DATA.pairs.forEach(p => {
    const v = store[p.pid];
    if (!v || !v.v) return;
    const arm = v.v === "none" ? "—" : (v.v === p.ruled ? "under the rules" : "no instructions");
    if (v.v === "none") none++; else if (v.v === p.ruled) ruled++; else plain++;
    L.push("| " + p.name + " | " + p.register + " | " + v.v + " | " + arm + " | " +
      (v.n || "") + " |");
  });
  if (L.length === 6) L.push("| _nothing read yet_ | | | | |");
  else L.push("", "**" + ruled + " under the rules · " + plain + " no instructions · " +
    none + " no difference**");
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
    ap = argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("control"); ap.add_argument("out")
    ap.add_argument("--repeat", type=int, default=1)
    a = ap.parse_args()
    build(Path(a.run).resolve(), Path(a.control).resolve(), Path(a.out), a.repeat)
