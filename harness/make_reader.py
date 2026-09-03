#!/usr/bin/env python3
"""Build a browsable reader for a run's raw samples.

Step 3 of the build order is a human reading pass: the mannerism taxonomy is
named from the evidence. 96 samples is more than a terminal comfortably shows,
so this emits a single self-contained page with the raw text, the repeats
grouped for variance reading, and a margin for marking patterns.

Usage: make_reader.py <run-dir> <out.html>
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def build(run_dir: Path, out: Path) -> None:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    prompts = {p["id"]: p for p in manifest["corpus_prompts"]}

    samples = []
    for s in manifest["samples"]:
        if not s["ok"]:
            continue
        text = (run_dir / "samples" / f"{s['key']}.md").read_text(encoding="utf-8")
        samples.append({
            "key": s["key"], "substrate": s["substrate"], "prompt": s["prompt_id"],
            "register": s["register"], "repeat": s["repeat"], "text": text,
            "words": len(text.split()), "cost": round(s["cost_usd"], 4),
        })

    prompt_meta = []
    for pid, p in sorted(prompts.items()):
        body = (REPO / p["path"]).read_text(encoding="utf-8")
        name = next((l.split(":", 1)[1].strip()
                     for l in body.splitlines() if l.startswith("name:")), pid)
        prompt_meta.append({
            "id": pid, "name": name, "register": p["register"],
            "body": body.split("---", 2)[2].strip(),
        })

    data = {
        "run": run_dir.name,
        "meta": {
            "model": manifest["model_requested"],
            "cli": manifest["cli_version"],
            "corpus": manifest["corpus_version"],
            "arm": manifest["arm"],
            "git": manifest["git_sha"][:10],
            "started": manifest["started_utc"][:19].replace("T", " ") + "Z",
            "cost": manifest["totals"]["cost_usd"],
            "ok": manifest["totals"]["ok"],
            "failed": manifest["totals"]["failed"],
        },
        "prompts": prompt_meta,
        "samples": samples,
    }
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size // 1024} KB, {len(samples)} samples)")


TEMPLATE = r"""<title>Baseline Galley</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --paper:#f3f2ee; --raised:#fbfaf8; --sunk:#eceae4;
  --ink:#191b19; --ink-soft:#5c5f5b; --ink-faint:#8b8e88;
  --rule:#d9d7d0; --rule-soft:#e6e4dd;
  --mark:#b4342a; --mark-wash:#b4342a14;
  --sub-a:#2f5d62; --sub-b:#8a6d1f;
  --focus:#3f5bd1;
  --sans:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
  --serif:"Newsreader",Georgia,"Times New Roman",serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#15171a; --raised:#1d2024; --sunk:#101214;
  --ink:#e7e6e0; --ink-soft:#9b9e99; --ink-faint:#6e726d;
  --rule:#31353a; --rule-soft:#24282c;
  --mark:#e2695c; --mark-wash:#e2695c1f;
  --sub-a:#6fb6bd; --sub-b:#d3ac4d;
  --focus:#7d92e8;
}}
:root[data-theme="dark"]{
  --paper:#15171a; --raised:#1d2024; --sunk:#101214;
  --ink:#e7e6e0; --ink-soft:#9b9e99; --ink-faint:#6e726d;
  --rule:#31353a; --rule-soft:#24282c;
  --mark:#e2695c; --mark-wash:#e2695c1f;
  --sub-a:#6fb6bd; --sub-b:#d3ac4d;
  --focus:#7d92e8;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:2px}
button{font:inherit;color:inherit;background:none;border:none;cursor:pointer}

/* ---- masthead ---- */
.masthead{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 22px;
  padding:14px 22px;border-bottom:1px solid var(--rule);background:var(--raised)}
.masthead h1{font-family:var(--serif);font-size:21px;font-weight:600;margin:0;
  letter-spacing:-.01em;white-space:nowrap}
.masthead h1 em{font-style:normal;color:var(--ink-faint);font-weight:400}
.facts{display:flex;flex-wrap:wrap;gap:6px 18px;margin-left:auto;
  font-family:var(--mono);font-size:11.5px;color:var(--ink-soft);
  font-variant-numeric:tabular-nums}
.facts b{font-weight:500;color:var(--ink)}
.facts span::before{content:attr(data-k);color:var(--ink-faint);
  text-transform:uppercase;letter-spacing:.07em;margin-right:6px;font-size:10px}

/* ---- frame ---- */
.frame{display:grid;grid-template-columns:264px minmax(0,1fr) 286px;
  height:calc(100vh - 53px)}
.rail,.margin{overflow-y:auto;background:var(--sunk)}
.rail{border-right:1px solid var(--rule)}
.margin{border-left:1px solid var(--rule)}
.galley{overflow-y:auto;background:var(--paper)}

/* ---- rail ---- */
.railhead{position:sticky;top:0;background:var(--sunk);padding:13px 16px 9px;
  border-bottom:1px solid var(--rule-soft);z-index:2}
.eyebrow{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-faint);margin:0 0 8px}
.segs{display:flex;gap:0;border:1px solid var(--rule);border-radius:3px;
  overflow:hidden;background:var(--raised)}
.segs button{flex:1;padding:5px 0;font-size:11.5px;font-family:var(--mono);
  color:var(--ink-soft);border-right:1px solid var(--rule)}
.segs button:last-child{border-right:none}
.segs button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.group{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-faint);padding:16px 16px 6px}
.item{display:block;width:100%;text-align:left;padding:7px 16px;
  border-left:2px solid transparent;line-height:1.35}
.item:hover{background:var(--rule-soft)}
.item[aria-current="true"]{background:var(--raised);border-left-color:var(--mark)}
.item .pid{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
  margin-right:6px}
.item .pname{font-size:13px}
.item .marked{color:var(--mark);font-family:var(--mono);font-size:10px;
  margin-left:5px}

/* ---- galley ---- */
.sheet{max-width:720px;margin:0 auto;padding:26px 34px 90px}
.brief{background:var(--sunk);border:1px solid var(--rule-soft);border-radius:3px;
  padding:12px 15px;margin-bottom:22px}
.brief summary{font-family:var(--mono);font-size:10.5px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ink-soft);cursor:pointer}
.brief pre{margin:11px 0 0;white-space:pre-wrap;font-family:var(--mono);
  font-size:12px;line-height:1.55;color:var(--ink-soft);
  max-height:280px;overflow:auto}
.slug{display:flex;flex-wrap:wrap;align-items:center;gap:10px;
  padding-bottom:11px;border-bottom:1px solid var(--rule);margin-bottom:6px}
.slug h2{font-family:var(--serif);font-size:22px;font-weight:600;margin:0;
  text-wrap:balance;flex:1 1 240px}
.chip{font-family:var(--mono);font-size:10px;letter-spacing:.07em;
  text-transform:uppercase;padding:3px 7px;border-radius:2px;
  border:1px solid currentColor}
.chip.a{color:var(--sub-a)} .chip.b{color:var(--sub-b)}
.tabs{display:flex;align-items:center;gap:3px;flex-wrap:wrap;
  padding:9px 0 0;margin-bottom:20px}
.tabs .lbl{font-family:var(--mono);font-size:10px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ink-faint);margin-right:5px}
.tabs button{font-family:var(--mono);font-size:11.5px;padding:3px 9px;
  border-radius:2px;color:var(--ink-soft);border:1px solid transparent}
.tabs button:hover{background:var(--rule-soft)}
.tabs button[aria-pressed="true"]{background:var(--ink);color:var(--paper)}
.stats{margin-left:auto;font-family:var(--mono);font-size:11px;
  color:var(--ink-faint);font-variant-numeric:tabular-nums}
.proof{font-family:var(--serif);font-size:16.5px;line-height:1.62;
  white-space:pre-wrap;overflow-wrap:break-word;
  border-left:1px solid var(--rule-soft);padding-left:20px}
.nosel{color:var(--ink-faint);font-style:italic}

/* ---- margin ---- */
.marginhead{position:sticky;top:0;background:var(--sunk);z-index:2;
  padding:13px 16px 10px;border-bottom:1px solid var(--rule-soft)}
.marginbody{padding:0 16px 40px}
.addrow{display:flex;gap:6px}
.addrow input{flex:1;min-width:0;font:inherit;font-size:12.5px;padding:6px 8px;
  background:var(--raised);color:var(--ink);border:1px solid var(--rule);
  border-radius:3px}
.addrow button{padding:0 11px;border:1px solid var(--mark);color:var(--mark);
  border-radius:3px;font-family:var(--mono);font-size:12px}
.addrow button:hover{background:var(--mark-wash)}
.tax{list-style:none;margin:14px 0 0;padding:0;display:flex;
  flex-direction:column;gap:1px}
.tax li{display:flex;align-items:flex-start;gap:8px;padding:8px 9px;
  background:var(--raised);border-left:2px solid var(--mark);border-radius:0 2px 2px 0}
.tax .txt{flex:1;font-size:13px;line-height:1.4}
.tax .n{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
  font-variant-numeric:tabular-nums;padding-top:2px}
.tax .del{color:var(--ink-faint);font-size:15px;line-height:1;padding:0 2px}
.tax .del:hover{color:var(--mark)}
.hint{color:var(--ink-faint);font-size:12px;line-height:1.5;margin:14px 0 0}
.notes{width:100%;min-height:88px;resize:vertical;font:inherit;font-size:12.5px;
  margin-top:9px;padding:8px;background:var(--raised);color:var(--ink);
  border:1px solid var(--rule);border-radius:3px;line-height:1.45}
.wide{width:100%;margin-top:12px;padding:7px;border:1px solid var(--rule);
  border-radius:3px;font-family:var(--mono);font-size:11.5px;color:var(--ink-soft);
  background:var(--raised)}
.wide:hover{border-color:var(--ink-soft);color:var(--ink)}

@media (max-width:1080px){
  .frame{grid-template-columns:1fr;height:auto}
  .rail,.margin{border:none;border-bottom:1px solid var(--rule);max-height:none}
  .margin{order:3}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<header class="masthead">
  <h1>Baseline Galley <em>/ control arm</em></h1>
  <div class="facts" id="facts"></div>
</header>

<div class="frame">
  <nav class="rail">
    <div class="railhead">
      <p class="eyebrow">Substrate</p>
      <div class="segs" id="subseg">
        <button data-s="a" aria-pressed="true">A · default</button>
        <button data-s="b" aria-pressed="false">B · minimal</button>
      </div>
    </div>
    <div id="promptlist"></div>
  </nav>

  <main class="galley">
    <div class="sheet">
      <details class="brief">
        <summary>Prompt as issued</summary>
        <pre id="brief"></pre>
      </details>
      <div class="slug">
        <h2 id="slugname"></h2>
        <span class="chip" id="slugchip"></span>
      </div>
      <div class="tabs">
        <span class="lbl">Repeat</span>
        <span id="repeats"></span>
        <span class="stats" id="stats"></span>
      </div>
      <div class="proof" id="proof"></div>
    </div>
  </main>

  <aside class="margin">
    <div class="marginhead">
      <p class="eyebrow">Mannerism taxonomy</p>
      <div class="addrow">
        <input id="taxin" placeholder="Name a pattern&hellip;" aria-label="Name a pattern">
        <button id="taxadd">Mark</button>
      </div>
    </div>
    <div class="marginbody">
      <ul class="tax" id="taxlist"></ul>
      <p class="hint" id="taxhint">Every entry records the sample you were reading
        when you named it, so a pattern can be traced back to its evidence.</p>
      <p class="eyebrow" style="margin-top:24px">Notes on this sample</p>
      <textarea class="notes" id="notes" placeholder="Free notes&hellip;"></textarea>
      <button class="wide" id="copy">Copy taxonomy &amp; notes</button>
    </div>
  </aside>
</div>

<script>
const DATA = __DATA__;
const K = "aiw-galley-" + DATA.run;

let state = {sub:"a", prompt:DATA.prompts[0].id, repeat:1};
let store = {tax:[], notes:{}};
try{const r=localStorage.getItem(K); if(r) store=JSON.parse(r);}catch(e){}
const save = () => {try{localStorage.setItem(K,JSON.stringify(store))}catch(e){}};

const $ = id => document.getElementById(id);
const esc = s => s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const forPrompt = () => DATA.samples
  .filter(s => s.substrate===state.sub && s.prompt===state.prompt)
  .sort((a,b)=>a.repeat-b.repeat);
const current = () => forPrompt().find(s=>s.repeat===state.repeat) || forPrompt()[0];

$("facts").innerHTML = [
  ["model", DATA.meta.model], ["cli", DATA.meta.cli.split(" ")[0]],
  ["corpus", DATA.meta.corpus], ["samples", DATA.meta.ok + " ok / " + DATA.meta.failed + " failed"],
  ["cost", "$" + DATA.meta.cost.toFixed(2)], ["commit", DATA.meta.git],
].map(([k,v]) => `<span data-k="${k}"><b>${esc(String(v))}</b></span>`).join("");

function drawRail(){
  const marks = {};
  store.tax.forEach(t => {marks[t.prompt] = (marks[t.prompt]||0)+1});
  let html = "";
  for(const reg of ["conversational","document"]){
    const ps = DATA.prompts.filter(p=>p.register===reg);
    html += `<p class="group">${reg} &middot; ${ps.length}</p>`;
    for(const p of ps){
      const m = marks[p.id] ? `<span class="marked">${marks[p.id]}&#9679;</span>` : "";
      html += `<button class="item" data-p="${p.id}" aria-current="${p.id===state.prompt}">
        <span class="pid">${p.id}</span><span class="pname">${esc(p.name)}</span>${m}</button>`;
    }
  }
  $("promptlist").innerHTML = html;
  $("promptlist").querySelectorAll(".item").forEach(b =>
    b.onclick = () => {state.prompt=b.dataset.p; state.repeat=1; draw();});
}

function draw(){
  drawRail();
  const p = DATA.prompts.find(x=>x.id===state.prompt);
  const reps = forPrompt(), s = current();
  $("brief").textContent = p.body;
  $("slugname").textContent = p.name;
  $("slugchip").textContent = "substrate " + state.sub;
  $("slugchip").className = "chip " + state.sub;
  $("repeats").innerHTML = reps.map(r =>
    `<button data-r="${r.repeat}" aria-pressed="${r.repeat===state.repeat}">r${r.repeat}</button>`
  ).join("");
  $("repeats").querySelectorAll("button").forEach(b =>
    b.onclick = () => {state.repeat=+b.dataset.r; draw();});
  if(s){
    $("stats").textContent = `${s.words} words · $${s.cost.toFixed(4)} · ${s.key}`;
    $("proof").textContent = s.text;
    $("notes").value = store.notes[s.key] || "";
    $("notes").disabled = false;
  } else {
    $("stats").textContent = "";
    $("proof").innerHTML = '<span class="nosel">No sample for this combination.</span>';
    $("notes").value = ""; $("notes").disabled = true;
  }
  drawTax();
}

function drawTax(){
  const counts = {};
  store.tax.forEach(t => {counts[t.text] = (counts[t.text]||0)+1});
  const seen = new Set();
  $("taxlist").innerHTML = store.tax.filter(t => {
    if(seen.has(t.text)) return false; seen.add(t.text); return true;
  }).map((t,i) => `<li><span class="n">${String(counts[t.text]).padStart(2,"0")}</span>
      <span class="txt">${esc(t.text)}</span>
      <button class="del" data-t="${esc(t.text)}" aria-label="Remove">&times;</button></li>`).join("");
  $("taxlist").querySelectorAll(".del").forEach(b =>
    b.onclick = () => {
      store.tax = store.tax.filter(t => t.text !== b.dataset.t); save(); draw();});
  $("taxhint").textContent = store.tax.length
    ? `${seen.size} pattern${seen.size===1?"":"s"} named across ${new Set(store.tax.map(t=>t.key)).size} samples.`
    : "Every entry records the sample you were reading when you named it, so a pattern can be traced back to its evidence.";
}

$("subseg").querySelectorAll("button").forEach(b =>
  b.onclick = () => {
    state.sub = b.dataset.s;
    $("subseg").querySelectorAll("button").forEach(x =>
      x.setAttribute("aria-pressed", String(x.dataset.s===state.sub)));
    state.repeat = 1; draw();});

function addTax(){
  const v = $("taxin").value.trim();
  if(!v) return;
  const s = current();
  store.tax.push({text:v, key:s?s.key:"—", prompt:state.prompt, sub:state.sub});
  $("taxin").value = ""; save(); draw();
}
$("taxadd").onclick = addTax;
$("taxin").onkeydown = e => {if(e.key==="Enter") addTax();};
$("notes").oninput = () => {
  const s = current(); if(!s) return;
  store.notes[s.key] = $("notes").value; save();};

$("copy").onclick = async () => {
  const byText = {};
  store.tax.forEach(t => {(byText[t.text] ||= []).push(`${t.sub}/${t.key}`)});
  let out = `# Mannerism taxonomy — ${DATA.run} (${DATA.meta.arm} arm)\n\n`;
  for(const [text, keys] of Object.entries(byText))
    out += `- ${text}\n  evidence: ${keys.join(", ")}\n`;
  const notes = Object.entries(store.notes).filter(([,v]) => v.trim());
  if(notes.length){
    out += `\n# Notes\n\n`;
    for(const [k,v] of notes) out += `## ${k}\n${v}\n\n`;
  }
  try{
    await navigator.clipboard.writeText(out);
    $("copy").textContent = "Copied — paste it back to Claude";
  }catch(e){
    $("copy").textContent = "Clipboard blocked; see console";
    console.log(out);
  }
  setTimeout(() => {$("copy").textContent = "Copy taxonomy & notes";}, 2600);
};

draw();
</script>
"""

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2]))
