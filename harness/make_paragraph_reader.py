#!/usr/bin/env python3
"""Build a galley of a run's longest prose paragraphs, for a human verdict.

C2, mean paragraph length, is filed in TAXONOMY.md as context rather than as a
defect. The shipped rules move it from 37 words to 81 on substrate A, and a
second reader called the result "wall paragraphs". DESIGN.md 4.2b forbids
promoting that into a detector on a number alone: a taxonomy entry needs a
quoted passage a person has read and judged.

So this emits the passages. Paragraphs are extracted with the same Doc used by
the detectors, so what the copyeditor reads is exactly what C2 counts, and each
is shown beside the control's longest paragraph on the same prompt, because a
word count means nothing without the thing it replaced.

Usage: make_paragraph_reader.py <run-dir> <control-dir> <out.html> [--top N]
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detectors import Doc  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def harvest(run_dir: Path, substrate: str = "a") -> tuple[list[dict], dict]:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    out = []
    for s in manifest["samples"]:
        if not s["ok"] or s["substrate"] != substrate:
            continue
        doc = Doc((run_dir / "samples" / f"{s['key']}.md").read_text(encoding="utf-8"))
        for idx, (para, sents) in enumerate(zip(doc.paragraphs, doc.para_sents)):
            lens = [len(x.split()) for x in sents]
            out.append({
                "words": len(para.split()), "sents": len(sents),
                "longest_sent": max(lens) if lens else 0,
                "pid": s["prompt_id"], "register": s["register"],
                "key": s["key"], "index": idx, "text": para.strip(),
            })
    return out, manifest


def spread(paras: list[dict]) -> dict:
    w = [p["words"] for p in paras]
    over = sum(1 for x in w if x > 100)
    return {"n": len(w), "mean": round(st.mean(w), 1), "median": round(st.median(w)),
            "longest": max(w), "over100": over, "over100pct": round(100 * over / len(w), 1)}


def build(run_dir: Path, ctrl_dir: Path, out: Path, top: int) -> None:
    paras, manifest = harvest(run_dir)
    ctrl_paras, ctrl_manifest = harvest(ctrl_dir)

    # The control's longest paragraph on each prompt is the anchor: the entry
    # answers "longer than what?" instead of leaving the reader to remember.
    anchor = {}
    for p in sorted(ctrl_paras, key=lambda x: -x["words"]):
        anchor.setdefault(p["pid"], p)

    prompts = {}
    for p in manifest["corpus_prompts"]:
        body = (REPO / p["path"]).read_text(encoding="utf-8")
        prompts[p["id"]] = {
            "register": p["register"],
            "name": next((l.split(":", 1)[1].strip() for l in body.splitlines()
                          if l.startswith("name:")), p["id"]),
            "body": body.split("---", 2)[2].strip(),
        }

    entries = []
    for rank, p in enumerate(sorted(paras, key=lambda x: -x["words"])[:top], 1):
        a = anchor.get(p["pid"])
        entries.append({**p, "rank": rank, "prompt_name": prompts[p["pid"]]["name"],
                        "control": {"words": a["words"], "key": a["key"],
                                    "text": a["text"]} if a else None})

    data = {
        "run": run_dir.name, "control_run": ctrl_dir.name,
        "meta": {
            "model": manifest["model_requested"], "corpus": manifest["corpus_version"],
            "style_sha": (manifest.get("style_sha256") or "")[:16],
            "cli": manifest["cli_version"], "substrate": "A",
        },
        "spread": {"run": spread(paras), "control": spread(ctrl_paras)},
        "prompts": prompts, "entries": entries, "top": top,
    }
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size // 1024} KB, {len(entries)} paragraphs "
          f"of {len(paras)}, longest {entries[0]['words']}w)")


TEMPLATE = r"""<title>The Wall Paragraph Galley</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --paper:#f3f2ee; --raised:#fbfaf8; --sunk:#eae8e1;
  --ink:#191b19; --ink-soft:#5c5f5b; --ink-faint:#8b8e88;
  --rule:#d9d7d0; --rule-soft:#e6e4dd;
  --mark:#b4342a; --mark-wash:#b4342a12;
  --keep:#2f5d62; --keep-wash:#2f5d6212;
  --focus:#3f5bd1;
  --sans:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
  --serif:"Newsreader",Georgia,"Times New Roman",serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#15171a; --raised:#1d2024; --sunk:#101214;
  --ink:#e7e6e0; --ink-soft:#9b9e99; --ink-faint:#6e726d;
  --rule:#2c3036; --rule-soft:#23272c;
  --mark:#e0685c; --mark-wash:#e0685c1c;
  --keep:#79aeb3; --keep-wash:#79aeb31c;
  --focus:#8ba0ee;
}}
:root[data-theme="dark"]{
  --paper:#15171a; --raised:#1d2024; --sunk:#101214;
  --ink:#e7e6e0; --ink-soft:#9b9e99; --ink-faint:#6e726d;
  --rule:#2c3036; --rule-soft:#23272c;
  --mark:#e0685c; --mark-wash:#e0685c1c;
  --keep:#79aeb3; --keep-wash:#79aeb31c;
  --focus:#8ba0ee;
}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);
  line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:940px;margin:0 auto;padding:0 24px 96px}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:2px}

/* masthead ------------------------------------------------------------- */
.masthead{padding:56px 0 28px;border-bottom:1px solid var(--rule)}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-faint);display:flex;flex-wrap:wrap;gap:14px}
h1{font-family:var(--serif);font-weight:500;font-size:clamp(34px,5.6vw,52px);
  line-height:1.06;letter-spacing:-.015em;margin:16px 0 0;text-wrap:balance}
.standfirst{font-family:var(--serif);font-size:19px;line-height:1.6;
  color:var(--ink-soft);max-width:60ch;margin:16px 0 0}
.standfirst b{color:var(--ink);font-weight:600}

/* the numbers ---------------------------------------------------------- */
.spread{margin:28px 0 0;border:1px solid var(--rule);background:var(--raised)}
.spread table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
.spread th,.spread td{padding:11px 16px;text-align:right;font-size:13px;
  border-bottom:1px solid var(--rule-soft)}
.spread tr:last-child td{border-bottom:0}
.spread th{font-family:var(--mono);font-size:10px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ink-faint);font-weight:500}
.spread th:first-child,.spread td:first-child{text-align:left}
.spread td:first-child{font-family:var(--mono);font-size:12px;color:var(--ink-soft)}
.spread .hot{color:var(--mark);font-weight:600}
.caption{font-size:13px;color:var(--ink-soft);margin:12px 0 0;max-width:66ch}

/* rail ----------------------------------------------------------------- */
.rail{position:sticky;top:0;z-index:5;background:var(--paper);
  border-bottom:1px solid var(--rule);margin:32px 0 0;padding:12px 0;
  display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.seg{display:flex;border:1px solid var(--rule);background:var(--raised)}
.seg button{font-family:var(--mono);font-size:11px;letter-spacing:.05em;
  text-transform:uppercase;padding:7px 12px;border:0;background:transparent;
  color:var(--ink-soft);cursor:pointer;border-right:1px solid var(--rule-soft)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.tally{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--ink-soft);
  font-variant-numeric:tabular-nums;display:flex;gap:14px}
.tally .n-long{color:var(--mark)} .tally .n-fine{color:var(--keep)}
.copy{font-family:var(--mono);font-size:11px;letter-spacing:.05em;
  text-transform:uppercase;padding:7px 12px;border:1px solid var(--rule);
  background:var(--raised);color:var(--ink-soft);cursor:pointer}
.copy:hover{color:var(--ink);border-color:var(--ink-faint)}

/* slips ---------------------------------------------------------------- */
.galley{display:flex;flex-direction:column;gap:0}
.slip{display:grid;grid-template-columns:84px minmax(0,1fr);gap:24px;
  padding:26px 0 26px 12px;border-bottom:1px solid var(--rule-soft);
  border-left:3px solid transparent}
.slip.v-long{border-left-color:var(--mark);background:var(--mark-wash)}
.slip.v-fine{border-left-color:var(--keep);background:var(--keep-wash)}
.gutter{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;
  padding-top:2px}
.gutter .rank{display:block;font-size:11px;color:var(--ink-faint)}
.gutter .count{display:block;font-size:27px;font-weight:500;line-height:1.15;
  letter-spacing:-.02em;margin-top:5px}
.gutter .unit{display:block;font-size:10px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ink-faint)}
.meta{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;
  font-family:var(--mono);font-size:11px;color:var(--ink-faint);margin-bottom:12px}
.meta .pid{color:var(--ink);font-weight:600}
.meta .name{font-family:var(--sans);font-size:12px;color:var(--ink-soft)}
.chip{border:1px solid var(--rule);padding:1px 7px;letter-spacing:.06em;
  text-transform:uppercase;font-size:9.5px;color:var(--ink-soft)}
.para{font-family:var(--serif);font-size:17.5px;line-height:1.68;margin:0;
  max-width:66ch;white-space:pre-wrap;overflow-wrap:break-word}
details.anchor{margin-top:14px;max-width:66ch}
details.anchor summary{font-family:var(--mono);font-size:11px;color:var(--keep);
  cursor:pointer;letter-spacing:.03em}
details.anchor summary::marker{color:var(--ink-faint)}
details.anchor .inner{margin-top:10px;padding:14px 16px;background:var(--sunk);
  border-left:2px solid var(--keep)}
details.anchor .inner p{font-family:var(--serif);font-size:15.5px;line-height:1.62;
  margin:8px 0 0;white-space:pre-wrap}
details.anchor .inner .who{font-family:var(--mono);font-size:10.5px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--ink-faint)}
.verdict{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;align-items:center}
.verdict button{font-family:var(--mono);font-size:11px;letter-spacing:.05em;
  text-transform:uppercase;padding:6px 13px;border:1px solid var(--rule);
  background:var(--raised);color:var(--ink-soft);cursor:pointer}
.verdict button:hover{border-color:var(--ink-faint);color:var(--ink)}
.verdict button[aria-pressed="true"][data-v="long"]{background:var(--mark);
  border-color:var(--mark);color:#fff}
.verdict button[aria-pressed="true"][data-v="fine"]{background:var(--keep);
  border-color:var(--keep);color:#fff}
.verdict input{flex:1;min-width:190px;font-family:var(--sans);font-size:13px;
  padding:6px 10px;border:1px solid var(--rule);background:var(--raised);
  color:var(--ink)}
.verdict input::placeholder{color:var(--ink-faint)}
.empty{padding:48px 0;color:var(--ink-faint);font-family:var(--mono);font-size:13px}

/* prompt reference ------------------------------------------------------ */
.ref{margin-top:56px;border-top:1px solid var(--rule);padding-top:24px}
.ref h2{font-family:var(--mono);font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-faint);font-weight:500;margin:0 0 14px}
.ref details{border-bottom:1px solid var(--rule-soft);padding:9px 0}
.ref summary{cursor:pointer;font-size:13px;color:var(--ink-soft)}
.ref summary b{font-family:var(--mono);font-size:12px;color:var(--ink);
  margin-right:9px;font-weight:600}
.ref pre{font-family:var(--mono);font-size:12px;line-height:1.6;white-space:pre-wrap;
  background:var(--sunk);padding:14px;margin:10px 0 4px;overflow-x:auto;
  color:var(--ink-soft)}
@media (max-width:640px){
  .slip{grid-template-columns:1fr;gap:10px}
  .gutter{text-align:left;display:flex;align-items:baseline;gap:8px}
  .gutter .count{font-size:20px;margin:0}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="wrap">
<header class="masthead">
  <div class="eyebrow" id="eyebrow"></div>
  <h1>The Wall Paragraph Galley</h1>
  <p class="standfirst">The style rules moved mean paragraph length on substrate A
  from <b>37 words to 81</b>. A second reader called the result wall paragraphs.
  TAXONOMY.md files paragraph length as context, not as a defect, and
  DESIGN.md&nbsp;4.2b will not let a number promote itself. So here are the
  passages. Mark the ones that are genuinely too long, and the verdict decides
  whether the taxonomy gains an entry.</p>
</header>

<section class="spread">
  <table><thead><tr>
    <th>prose paragraphs, substrate A</th><th>count</th><th>mean</th>
    <th>median</th><th>longest</th><th>over 100 words</th>
  </tr></thead><tbody id="spread"></tbody></table>
</section>
<p class="caption" id="caption"></p>

<div class="rail">
  <div class="seg" id="regfilter">
    <button data-reg="all" aria-pressed="true">All</button>
    <button data-reg="conversational" aria-pressed="false">Conversational</button>
    <button data-reg="document" aria-pressed="false">Document</button>
  </div>
  <div class="seg" id="markfilter">
    <button data-m="all" aria-pressed="true">Every slip</button>
    <button data-m="todo" aria-pressed="false">Unmarked</button>
  </div>
  <button class="copy" id="copy">Copy verdict</button>
  <div class="tally" id="tally"></div>
</div>

<main class="galley" id="galley"></main>

<section class="ref">
  <h2>The prompts these answer</h2>
  <div id="ref"></div>
</section>
</div>

<script>
const DATA = __DATA__;
const K = "aiw-paras-" + DATA.run;
let store = {};
try{ const r = localStorage.getItem(K); if(r) store = JSON.parse(r); }catch(e){}
const save = () => { try{ localStorage.setItem(K, JSON.stringify(store)); }catch(e){} };
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const state = {reg:"all", mark:"all"};
const idOf = e => e.key + "#" + e.index;

$("eyebrow").innerHTML = [
  "substrate " + DATA.meta.substrate,
  esc(DATA.run),
  "style " + esc(DATA.meta.style_sha),
  esc(DATA.meta.model),
  "corpus " + esc(DATA.meta.corpus),
].map(x => "<span>" + x + "</span>").join("");

const S = DATA.spread;
$("spread").innerHTML = [
  ["control, no rules", S.control, ""],
  ["shipped rules", S.run, "hot"],
].map(([label, s, cls]) => `<tr><td>${esc(label)}</td><td>${s.n}</td>
  <td class="${cls}">${s.mean}</td><td class="${cls}">${s.median}</td>
  <td class="${cls}">${s.longest}</td>
  <td class="${cls}">${s.over100} &middot; ${s.over100pct}%</td></tr>`).join("");
$("caption").textContent =
  `The ${DATA.entries.length} longest paragraphs the rules produced follow, `
  + `set as prose and ranked by length. Each one folds out to the control's `
  + `longest paragraph on the same prompt, so the comparison is like for like. `
  + `Paragraphs are cut the way the detectors cut them, so what you read is `
  + `exactly what C2 counts.`;

function slip(e){
  const v = (store[idOf(e)] || {}).v || "";
  const note = (store[idOf(e)] || {}).note || "";
  const a = e.control;
  return `<article class="slip ${v ? "v-" + v : ""}" data-id="${esc(idOf(e))}"
      data-reg="${esc(e.register)}">
    <div class="gutter">
      <span class="rank">${String(e.rank).padStart(2,"0")}</span>
      <span class="count">${e.words}</span><span class="unit">words</span>
    </div>
    <div>
      <div class="meta">
        <span class="pid">${esc(e.pid)}</span>
        <span class="chip">${esc(e.register)}</span>
        <span class="name">${esc(e.prompt_name)}</span>
        <span>${e.sents} sentence${e.sents === 1 ? "" : "s"} &middot; longest ${e.longest_sent}w</span>
        <span>${esc(e.key)}</span>
      </div>
      <p class="para">${esc(e.text)}</p>
      ${a ? `<details class="anchor"><summary>The control's longest paragraph on
        ${esc(e.pid)} runs ${a.words} words &mdash; read it</summary>
        <div class="inner"><span class="who">${esc(a.key)}</span>
        <p>${esc(a.text)}</p></div></details>` : ""}
      <div class="verdict">
        <button data-v="long" aria-pressed="${v === "long"}">Too long</button>
        <button data-v="fine" aria-pressed="${v === "fine"}">Reads fine</button>
        <input class="note" value="${esc(note)}" placeholder="why, in your words (optional)">
      </div>
    </div>
  </article>`;
}

function draw(){
  const rows = DATA.entries.filter(e =>
    (state.reg === "all" || e.register === state.reg) &&
    (state.mark === "all" || !(store[idOf(e)] || {}).v));
  $("galley").innerHTML = rows.length ? rows.map(slip).join("")
    : `<p class="empty">Nothing left under this filter.</p>`;
  const vals = DATA.entries.map(e => (store[idOf(e)] || {}).v);
  const n = v => vals.filter(x => x === v).length;
  $("tally").innerHTML = `<span class="n-long">${n("long")} too long</span>
    <span class="n-fine">${n("fine")} fine</span>
    <span>${vals.filter(x => !x).length} unread</span>`;
}

$("galley").addEventListener("click", ev => {
  const b = ev.target.closest("button[data-v]"); if(!b) return;
  const id = b.closest(".slip").dataset.id;
  const rec = store[id] || (store[id] = {});
  rec.v = rec.v === b.dataset.v ? "" : b.dataset.v;
  save(); draw();
});
$("galley").addEventListener("input", ev => {
  if(!ev.target.classList.contains("note")) return;
  const id = ev.target.closest(".slip").dataset.id;
  (store[id] || (store[id] = {})).note = ev.target.value;
  save();
});
for(const [el, key, attr] of [["regfilter","reg","reg"],["markfilter","mark","m"]]){
  $(el).addEventListener("click", ev => {
    const b = ev.target.closest("button"); if(!b) return;
    state[key] = b.dataset[attr];
    for(const s of $(el).children) s.setAttribute("aria-pressed", s === b);
    draw();
  });
}

$("copy").addEventListener("click", async () => {
  const line = e => {
    const r = store[idOf(e)] || {};
    return `| ${e.rank} | ${e.pid} | ${e.register} | ${e.words} | ${r.v || "unread"} `
         + `| ${(r.note || "").replace(/\|/g, "/")} | ${e.key}#${e.index} |`;
  };
  const vals = DATA.entries.map(e => (store[idOf(e)] || {}).v);
  const n = v => vals.filter(x => x === v).length;
  const out = [
    `# Paragraph-length verdict — ${DATA.run}`, "",
    `Substrate A, ${DATA.entries.length} longest paragraphs of ${DATA.spread.run.n}.`,
    `Control mean ${DATA.spread.control.mean}w, rules mean ${DATA.spread.run.mean}w.`, "",
    `**${n("long")} too long · ${n("fine")} fine · ${vals.filter(x => !x).length} unread**`, "",
    "| # | prompt | register | words | verdict | note | source |",
    "|---|---|---|---:|---|---|---|",
    ...DATA.entries.map(line), "",
  ].join("\n");
  try{ await navigator.clipboard.writeText(out); }
  catch(e){
    const t = document.createElement("textarea");
    t.value = out; document.body.appendChild(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  $("copy").textContent = "Copied";
  setTimeout(() => { $("copy").textContent = "Copy verdict"; }, 1600);
});

$("ref").innerHTML = Object.entries(DATA.prompts).map(([id, p]) =>
  `<details><summary><b>${esc(id)}</b>${esc(p.name)}
    <span class="chip">${esc(p.register)}</span></summary>
    <pre>${esc(p.body)}</pre></details>`).join("");

draw();
</script>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("control_dir")
    ap.add_argument("out")
    ap.add_argument("--top", type=int, default=40,
                    help="how many of the longest paragraphs to show")
    args = ap.parse_args()
    build(Path(args.run_dir), Path(args.control_dir), Path(args.out), args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
