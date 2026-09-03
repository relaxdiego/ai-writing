#!/usr/bin/env python3
"""Build an S1 galley: every one-sentence paragraph, sorted by what it does.

S1 is taxonomy entry 1, the staccato, and it is the headline metric. It counts
the share of prose paragraphs holding one sentence of 25 words or fewer. It rose
6.79 -> 24.15 under R02's collateral clauses, which reads as a large regression.

It is not one. The clauses tell an answer to state its verdict first and alone,
and they brought back the lists, tables and code blocks R02 had killed. A verdict
stated alone is a one-sentence paragraph. A line introducing a list is a
one-sentence paragraph. S1 cannot tell either of them from the fragment floating
in prose that the copyeditor actually named, because S1 looks at a paragraph and
never at what sits on either side of it.

So this walks the raw text with the blocks left in, sorts every one-sentence
paragraph by what follows it, and sets each one in place:

  opening    the answer's first prose block. R02 puts the verdict here.
  lead-in    directly followed by a list, table or code block.
  the rest   everything the first two questions did not catch.

The copyeditor ruled the first two out of S1 and could not rule on the third,
because it was labelled "the floating fragment" and described as "prose above,
prose below" when that is true of 2 of its 12. It is the residue of a
forward-looking sort. Six of the twelve are a paragraph commenting on the block
*above* it, which is the reverse of a lead-in.

So the header of every hit now states where it sits, in both directions, and the
control's own hits are markable: the defect is at full strength there, 66 hits
against 5, and it has to be named from the run that still has it.

Paragraphs over S1's 25-word cap are kept and badged rather than dropped: where
the cap falls is a boundary the copyeditor can see only if the near misses are
on the page.

Usage: make_s1_reader.py <run> <prev-run> <control-run> <out.html>
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "harness"))
from detectors import Doc  # noqa: E402
from make_verdict_reader import blocks, render  # noqa: E402
from make_paragraph_reader import load_glosses  # noqa: E402

# A standalone horizontal rule is not a paragraph. Doc counts it as one, which
# puts four of the shipped run's sixteen leftover hits down to `---`. That is a
# real fault in the detector, left alone here: changing an estimator invalidates
# every cached result.json, which is a decision and not this script's to take.
HRULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")

MARKS = re.compile(r"\*\*|\*|`|_")
CAP = 25  # S1's own word cap, from detectors.s1_one_sentence_paragraphs

# A ruling pasted back from the galley is baked into the next build. The marks
# used to live only in the reader's browser, and a cleared browser lost a
# afternoon's judging. They are the deliverable, so they belong in the repo and
# in the page; localStorage now only holds what is newer than the file.
KIND_OF = {"opening verdict": "opening", "list lead-in": "lead-in",
           "floating fragment": "floating", "everything else": "floating"}
VERDICT_OF = {"the defect": "defect", "not the defect": "clean",
              "yes": "defect", "no": "clean"}


def read_ruling(path: Path, rows: list[dict]) -> dict:
    """Turn a pasted ruling table back into the galley's own store.

    Rows are matched on prompt, repeat, kind and word count, consumed in
    document order so that the two keys that are not unique still land on
    distinct hits. Anything unmatched is reported rather than dropped silently.
    """
    if not path.is_file():
        return {}
    seed: dict[str, dict] = {}
    pool: dict[tuple, list[dict]] = {}
    for r in rows:
        pool.setdefault((r["pid"], r["rep"], r["what"], r["words"]), []).append(r)

    unmatched = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0] in KIND_OF:          # the per-kind ruling
            v = VERDICT_OF.get(cells[2].lower())
            seed["rule:" + KIND_OF[cells[0]]] = {"v": v or "", "n": cells[3]}
        elif len(cells) == 6 and "·" in cells[0]:            # one marked hit
            pid, rep = cells[0].split("·r")
            key = (pid, int(rep), KIND_OF.get(cells[2], cells[2]), int(cells[3]))
            hits = pool.get(key) or []
            if not hits:
                unmatched += 1
                continue
            h = hits.pop(0)
            seed["hit:" + h["id"]] = {"v": VERDICT_OF.get(cells[4], ""), "n": cells[5]}
    if unmatched:
        print(f"  warning: {unmatched} pasted rows matched no hit", file=sys.stderr)
    return seed


def hits_in(raw: str) -> tuple[list[dict], int]:
    """Every one-sentence prose paragraph, classified by what follows it."""
    bs = [(k, b) for k, b in blocks(raw) if not (k == "prose" and HRULE.match(b))]
    first_prose = next((i for i, (k, _) in enumerate(bs) if k == "prose"), None)

    out = []
    for i, (kind, body) in enumerate(bs):
        if kind != "prose":
            continue
        sents = Doc._split(MARKS.sub("", body))
        if len(sents) != 1:
            continue
        nxt = bs[i + 1][0] if i + 1 < len(bs) else None
        if i == first_prose:
            what = "opening"
        elif nxt in ("list", "table", "code"):
            what = "lead-in"
        else:
            what = "floating"
        # Both neighbours are kept. A lead-in cannot be judged without the
        # list it leads into; and the block *above* turned out to matter just as
        # much, since half the residue is commentary on it.
        prev = bs[i - 1] if i else None
        out.append({
            "what": what, "words": len(body.split()),
            "counted": len(sents[0].split()) <= CAP,
            "index": i,
            "prev_kind": prev[0] if prev else None,
            "prev_html": render(*prev) if prev else "",
            "html": render(kind, body),
            "next_kind": nxt,
            "next_html": render(*bs[i + 1]) if nxt else "",
        })
    n_prose = sum(1 for k, _ in bs if k == "prose")
    return out, n_prose


def sweep(run_dir: Path) -> tuple[list[dict], dict]:
    man = json.loads((run_dir / "manifest.json").read_text())
    rows, n_prose = [], 0
    for s in man["samples"]:
        if not s["ok"] or s["substrate"] != "a":
            continue
        raw = (run_dir / "samples" / f"{s['key']}.md").read_text(encoding="utf-8")
        hs, np_ = hits_in(raw)
        n_prose += np_
        for h in hs:
            rows.append({**h, "key": s["key"], "pid": s["prompt_id"],
                         "rep": s["repeat"], "register": s["register"]})
    return rows, {"man": man, "n_prose": n_prose}


def tally(rows: list[dict], n_prose: int) -> dict:
    t = {"opening": 0, "lead-in": 0, "floating": 0}
    c = {"opening": 0, "lead-in": 0, "floating": 0}
    for r in rows:
        t[r["what"]] += 1
        if r["counted"]:
            c[r["what"]] += 1
    return {"all": t, "counted": c, "n_prose": n_prose,
            "pct": round(100 * sum(c.values()) / n_prose, 2) if n_prose else 0.0}


def s1_mean(run_dir: Path) -> float:
    p = run_dir / "result.json"
    if not p.is_file():
        return 0.0
    return json.loads(p.read_text())["aggregates"]["a"]["S1"]["mean"]


def build(run: Path, prev: Path, ctrl: Path, out: Path) -> None:
    rows, meta = sweep(run)
    prev_rows, prev_meta = sweep(prev)
    ctrl_rows, ctrl_meta = sweep(ctrl)
    man = meta["man"]

    glosses = load_glosses(man["corpus_version"])
    prompts = {}
    for p in man["corpus_prompts"]:
        body = (REPO / p["path"]).read_text(encoding="utf-8")
        prompts[p["id"]] = {
            "register": p["register"],
            "name": next((l.split(":", 1)[1].strip() for l in body.splitlines()
                          if l.startswith("name:")), p["id"]),
            "gloss": glosses.get(p["id"]),
        }

    for r in rows:
        r["id"] = f"{r['key']}:{r['index']}"
    for r in ctrl_rows:
        r["id"] = "ctrl:" + r["key"] + ":" + str(r["index"])

    seed = read_ruling(REPO / "verdicts" / f"s1-{run.name}.md", rows)

    data = {
        "run": run.name, "prev_run": prev.name, "control_run": ctrl.name,
        "meta": {"model": man["model_requested"], "corpus": man["corpus_version"],
                 "style_sha": (man.get("style_sha256") or "")[:16],
                 "cli": man["cli_version"]},
        "counts": {"now": tally(rows, meta["n_prose"]),
                   "prev": tally(prev_rows, prev_meta["n_prose"]),
                   "control": tally(ctrl_rows, ctrl_meta["n_prose"])},
        "s1": {"now": s1_mean(run), "prev": s1_mean(prev), "control": s1_mean(ctrl)},
        "cap": CAP,
        "prompts": prompts,
        "hits": rows,
        # The control's own residue: the defect at full strength, markable,
        # because it cannot be named from a run the rules have cleared of it.
        "control_floating": [r for r in ctrl_rows if r["what"] == "floating"],
        "seed": seed,
    }
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    c = data["counts"]["now"]["all"]
    print(f"{out}  ({out.stat().st_size // 1024} KB, {len(rows)} hits: "
          f"{c['opening']} opening, {c['lead-in']} lead-in, {c['floating']} the rest; "
          f"{len(data['control_floating'])} control hits; {len(seed)} marks restored)")


TEMPLATE = r"""<title>What S1 Counts</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Spectral:ital,wght@0,400;0,500;0,600;1,400&family=JetBrains+Mono:wght@400;500;700&display=swap">
<style>
:root{
  --paper:#eef0f2; --raised:#f8f9fa; --sunk:#e3e6e9;
  --ink:#14181d; --ink-soft:#535d68; --ink-faint:#828c96;
  --rule:#cfd5da; --hair:#e0e4e8;
  --open:#2b4a8f;  --open-wash:#2b4a8f14;
  --lead:#3f6b52;  --lead-wash:#3f6b5214;
  --float:#9c3b2e; --float-wash:#9c3b2e14;
  --focus:#2b4a8f;
  --ui:"Archivo",ui-sans-serif,system-ui,-apple-system,sans-serif;
  --prose:"Spectral",Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#121519; --raised:#191d23; --sunk:#0d1013;
  --ink:#e6e9ec; --ink-soft:#98a3ae; --ink-faint:#6b7681;
  --rule:#2a3038; --hair:#22272e;
  --open:#7f9ce0;  --open-wash:#7f9ce01c;
  --lead:#79b18f;  --lead-wash:#79b18f1c;
  --float:#d9776a; --float-wash:#d9776a1c;
  --focus:#7f9ce0;
}}
:root[data-theme="dark"]{
  --paper:#121519; --raised:#191d23; --sunk:#0d1013;
  --ink:#e6e9ec; --ink-soft:#98a3ae; --ink-faint:#6b7681;
  --rule:#2a3038; --hair:#22272e;
  --open:#7f9ce0;  --open-wash:#7f9ce01c;
  --lead:#79b18f;  --lead-wash:#79b18f1c;
  --float:#d9776a; --float-wash:#d9776a1c;
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

/* the split */
.split{margin:28px 0 0;border:1px solid var(--rule);background:var(--raised);
  overflow-x:auto}
.split table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;
  min-width:520px}
.split th,.split td{padding:10px 14px;text-align:right;font-size:13px;
  border-bottom:1px solid var(--hair)}
.split tbody tr:last-child td{border-bottom:0}
.split th{font-family:var(--mono);font-size:10px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--ink-faint);font-weight:500}
.split th:first-child,.split td:first-child{text-align:left}
.split td:first-child{font-family:var(--mono);font-size:12px;color:var(--ink-soft)}
.split tr.tot td{font-weight:700;border-top:1px solid var(--rule)}
.split .sw{display:inline-block;width:9px;height:9px;margin-right:8px;
  vertical-align:baseline}
.split .sw.opening{background:var(--open)}
.split .sw.lead-in{background:var(--lead)}
.split .sw.floating{background:var(--float)}
.caption{font-size:13.5px;color:var(--ink-soft);margin:12px 0 0;max-width:68ch;
  line-height:1.6}

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
  margin:52px 0 0;padding-bottom:9px;border-bottom:1px solid var(--ink);
  display:flex;flex-wrap:wrap;gap:11px;align-items:baseline}
h2 .n{font-family:var(--mono);font-size:12px;color:var(--ink-faint);font-weight:500}
.sublede{font-size:14.5px;color:var(--ink-soft);margin:11px 0 0;max-width:68ch;
  line-height:1.6}

/* the ruling: one per kind, which is what was asked for */
.ruling{margin:18px 0 0;border:1px solid var(--rule);border-left:4px solid var(--c);
  background:var(--raised);padding:16px 18px}
.ruling h3{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-faint);margin:0 0 8px;font-weight:500}
.ruling p{margin:0 0 13px;font-size:15px;max-width:66ch;line-height:1.6}
.ruling .vd input{min-width:240px}

/* one hit, in place */
.item{margin:30px 0 0;border-top:1px solid var(--rule);padding-top:16px}
.hd{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline}
.pid{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--ink)}
.pname{font-family:var(--ui);font-weight:600;font-size:15px}
.tag{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-faint);border:1px solid var(--hair);padding:2px 6px}
.tag.over{color:var(--float);border-color:var(--float)}
.tag.sits{font-family:var(--mono);color:var(--ink-soft);background:var(--sunk);
  border-color:transparent;text-transform:none;letter-spacing:.02em}

.frame{margin:14px 0 0;display:grid;grid-template-columns:74px 1fr;
  border-left:3px solid var(--c);background:var(--w)}
.gut{padding:12px 10px;border-right:1px solid var(--hair)}
.gut .st{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--c);font-weight:700;line-height:1.3}
.gut .n{font-family:var(--mono);font-size:19px;font-weight:700;color:var(--ink);
  font-variant-numeric:tabular-nums;line-height:1.2;margin-top:6px}
.gut .u{font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);line-height:1.35}
.stack{padding:12px 16px;min-width:0}
.ctx{opacity:.5}
.ctx.before::before,.ctx.after::before{font-family:var(--mono);font-size:9px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint);
  display:block;margin-bottom:6px}
.ctx.before::before{content:"before"}
.ctx.after::before{content:"after — " attr(data-k)}
.ctx.after{border-top:1px dashed var(--hair);margin-top:12px;padding-top:12px}
.ctx.after.solo{opacity:1}
.hit{border-left:3px solid var(--c);padding-left:14px;margin:12px 0}
.hit p{font-family:var(--prose);font-size:17px;line-height:1.6;margin:0;
  max-width:64ch;color:var(--ink)}
.stack p{font-family:var(--prose);font-size:15.5px;line-height:1.6;margin:0 0 10px;
  max-width:66ch}
.stack>*:last-child{margin-bottom:0}
.stack b{font-weight:600}
.mdh{font-family:var(--ui);font-weight:700;font-size:13px;color:var(--ink);margin:0 0 9px}
.mdh::before{content:"§ ";color:var(--ink-faint)}
ul,ol{font-family:var(--prose);font-size:15px;line-height:1.58;margin:0 0 10px;
  padding-left:21px;max-width:64ch}
li{margin:0 0 4px}
code{font-family:var(--mono);font-size:.85em;background:var(--sunk);padding:1px 4px}
pre.code{font-family:var(--mono);font-size:12px;line-height:1.5;background:var(--sunk);
  padding:11px 13px;overflow-x:auto;margin:0 0 10px;white-space:pre}
blockquote{border-left:2px solid var(--rule);margin:0 0 10px;padding-left:13px;
  font-family:var(--prose);color:var(--ink-soft)}
.scroll{overflow-x:auto;margin:0 0 10px}
table{border-collapse:collapse;font-size:13px;width:100%;font-variant-numeric:tabular-nums}
th,td{border:1px solid var(--hair);padding:6px 9px;text-align:left;vertical-align:top}
th{font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-faint);font-weight:500;background:var(--sunk)}
td{font-family:var(--prose);font-size:14.5px}

.item[data-w="opening"]{--c:var(--open);--w:var(--open-wash)}
.item[data-w="lead-in"]{--c:var(--lead);--w:var(--lead-wash)}
.item[data-w="floating"]{--c:var(--float);--w:var(--float-wash)}
#sec-open .ruling{--c:var(--open)}
#sec-lead .ruling{--c:var(--lead)}
#sec-float .ruling{--c:var(--float)}

/* verdict */
.vd{display:flex;flex-wrap:wrap;gap:7px;margin:13px 0 0;align-items:center}
.vd button{font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;
  text-transform:uppercase;padding:7px 12px;border:1px solid var(--rule);
  background:var(--raised);color:var(--ink-soft);cursor:pointer}
.vd button:hover{border-color:var(--ink-faint);color:var(--ink)}
.vd button[aria-pressed="true"][data-v="defect"]{background:var(--float);
  border-color:var(--float);color:#fff}
.vd button[aria-pressed="true"][data-v="clean"]{background:var(--open);
  border-color:var(--open);color:#fff}
.vd input{flex:1;min-width:200px;font-family:var(--prose);font-size:15px;
  padding:7px 11px;border:1px solid var(--rule);background:var(--raised);color:var(--ink)}
.vd input::placeholder{color:var(--ink-faint);font-family:var(--ui);font-size:13px}

.foot{margin:64px 0 0;padding-top:18px;border-top:1px solid var(--rule);
  font-size:13px;color:var(--ink-faint);max-width:70ch;line-height:1.6}
.foot code{background:none;padding:0;color:var(--ink-soft)}
.empty{padding:34px 0;color:var(--ink-faint);font-size:14px}
@media(max-width:640px){
  .frame{grid-template-columns:1fr}
  .gut{border-right:0;border-bottom:1px solid var(--hair);display:flex;gap:10px;
    align-items:baseline;padding:8px 12px}
  .gut .n{margin-top:0;font-size:15px}
  .stack{padding:12px}
}
</style>

<div class="wrap">
<header class="mast">
  <div class="kicker">
    <span id="k-run"></span><span id="k-model"></span><span id="k-sha"></span>
    <span>substrate A</span>
  </div>
  <h1>What S1 counts</h1>
  <p class="stand">S1 is the staccato: a paragraph holding one short sentence, which asserts and
  then stops. It is the most common defect in the control and the headline metric of this
  project. Under the new clauses <b>it rose from 6.79 to 24.15</b>, which reads as the rules
  making the prose worse. It is not one number. S1 sees a paragraph and never what sits on
  either side of it, so a stated verdict, a line introducing a list, and the staccato itself all
  register as the same event. <b>The first two are now ruled out of S1.</b> What is left is a
  residue rather than a kind, and it has to be named where it still exists &mdash; in the
  control, on the last tab.</p>

  <div class="split" id="split"></div>
  <p class="caption" id="caption"></p>
</header>

<div class="rail">
  <div class="seg" role="group" aria-label="Which kind">
    <button data-sec="open" aria-pressed="true">the opening verdict</button>
    <button data-sec="lead" aria-pressed="false">the list lead-in</button>
    <button data-sec="float" aria-pressed="false">everything else</button>
    <button data-sec="ctrl" aria-pressed="false">name it in the control</button>
  </div>
  <div class="seg" role="group" aria-label="Which register">
    <button data-r="all" aria-pressed="true">both</button>
    <button data-r="conversational" aria-pressed="false">replies</button>
    <button data-r="document" aria-pressed="false">documents</button>
  </div>
  <span class="grow"></span>
  <span class="tally" id="tally"></span>
  <button class="act" id="copy">Copy ruling</button>
</div>

<section id="sec-open">
  <h2>The opening verdict <span class="n" id="n-open"></span></h2>
  <p class="sublede">R02 now tells an answer that reaches a recommendation, a refusal or a
  warning to state it first and by itself. By itself means one paragraph, and these answers
  need one sentence for it. The block under each is what follows, because a verdict swallowed
  by its own reasoning was not stated alone.</p>
  <div class="ruling">
    <h3>The ruling &mdash; answered</h3>
    <p>Is a verdict standing alone at the head of an answer the same defect as the staccato,
    and should S1 go on counting it? <b>No.</b> Fourteen hits, all marked not the defect.</p>
    <div id="rule-open"></div>
  </div>
  <div id="list-open"></div>
</section>

<section id="sec-lead" hidden>
  <h2>The list lead-in <span class="n" id="n-lead"></span></h2>
  <p class="sublede">R02 also brought back the lists, tables and code blocks it had killed. Each
  needs a line to introduce it, and that line is one sentence. The block it introduces is shown
  under it. Most end in a colon; a few do not, and those are the interesting ones.</p>
  <div class="ruling">
    <h3>The ruling &mdash; answered</h3>
    <p>Is a line introducing a list, a table or a code block the same defect as the staccato,
    and should S1 go on counting it? <b>No.</b> Forty-seven hits, all marked not the defect.</p>
    <div id="rule-lead"></div>
  </div>
  <div id="list-lead"></div>
</section>

<section id="sec-float" hidden>
  <h2>Everything else <span class="n" id="n-float"></span></h2>
  <p class="sublede">Not first, and not introducing a block. That is all these have in common:
  this section is what the other two questions did not catch, not a kind of its own. Five follow
  a code block, two follow a list, four end the answer, and two have prose on both sides. Six are
  a paragraph commenting on the block above them &mdash; a lead-in in reverse, which nothing here
  looks for. The header of each says where it sits.</p>
  <div class="ruling">
    <h3>The ruling</h3>
    <p>These are the leftovers, so the question is not yet answerable here. It is answerable in
    the control, which still holds 66 of them against these 5. Mark what you can, then use the
    control tab.</p>
    <div id="rule-float"></div>
  </div>
  <div id="list-float"></div>
</section>

<section id="sec-ctrl" hidden>
  <h2>Name it in the control <span class="n" id="n-ctrl"></span></h2>
  <p class="sublede">The same leftovers in the frozen control, with no rules applied. The
  staccato is at full strength here and nearly gone from the shipped run, so this is the only
  place it can be described from. Mark the ones that are the defect, leave the ones that are
  not, and write what the marked ones have in common. Your sentence becomes what S1 looks for.</p>
  <div class="ruling" id="ctrl-ruling">
    <h3>The naming</h3>
    <p>What do the ones you marked have in common? Say it however you would say it to another
    copyeditor &mdash; the detector gets written from your sentence, not the other way round.</p>
    <div class="vd" data-id="name:staccato">
      <input type="text" id="naming" placeholder="the defect, in your words">
    </div>
  </div>
  <div id="list-ctrl"></div>
</section>

<p class="foot" id="foot"></p>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const K = "s1ruling:" + DATA.run;
// The recorded ruling ships with the page; the browser only holds what is
// newer than it. Clearing the browser now costs nothing.
let store = Object.assign({}, DATA.seed);
try { const r = localStorage.getItem(K); if (r) Object.assign(store, JSON.parse(r)); }
catch (e) {}
const save = () => { try { localStorage.setItem(K, JSON.stringify(store)); } catch (e) {} };

let section = "open", reg = "all";
const KINDS = [["opening", "open"], ["lead-in", "lead"], ["floating", "float"]];
const LABEL = {opening: "opening verdict", "lead-in": "list lead-in",
               floating: "everything else"};
const SHORT = {opening: "verdict", "lead-in": "lead-in", floating: "the rest"};
const AFTER = {list: "a list", table: "a table", code: "a code block",
               header: "a header", prose: "a paragraph", quote: "a quotation"};

$("k-run").textContent = DATA.run;
$("k-model").textContent = DATA.meta.model;
$("k-sha").textContent = "style " + DATA.meta.style_sha;
$("foot").innerHTML =
  "Control <code>" + esc(DATA.control_run) + "</code>. Before the clauses <code>" +
  esc(DATA.prev_run) + "</code>. Now <code>" + esc(DATA.run) + "</code>. Corpus " +
  esc(DATA.meta.corpus) + ", CLI " + esc(DATA.meta.cli) + ". Counts are of paragraphs " +
  "inside S1's " + DATA.cap + "-word cap; a longer one-sentence paragraph is shown and " +
  "badged but not counted. Rulings are kept in this browser only. Built by " +
  "<code>harness/make_s1_reader.py</code>.";

/* the split ------------------------------------------------------------ */
(function () {
  const C = DATA.counts, S = DATA.s1;
  const col = ["control", "prev", "now"];
  const head = "<tr><th>one-sentence paragraphs</th><th>control</th>" +
    "<th>before the clauses</th><th>with the clauses</th></tr>";
  let body = "";
  KINDS.forEach(([k]) => {
    body += '<tr><td><span class="sw ' + k + '"></span>' + LABEL[k] + "</td>" +
      col.map(c => "<td>" + C[c].counted[k] + "</td>").join("") + "</tr>";
  });
  body += '<tr class="tot"><td>S1, share of prose paragraphs</td>' +
    col.map(c => "<td>" + S[c].toFixed(2) + "%</td>").join("") + "</tr>";
  $("split").innerHTML = "<table><thead>" + head + "</thead><tbody>" + body + "</tbody></table>";
  const f = C.now.counted.floating, fc = C.control.counted.floating;
  $("caption").innerHTML =
    "Counts are hits across 36 substrate-A samples; S1 is the mean of the per-sample share, " +
    "which is why it does not divide out of the rows above. <b>The staccato did not come " +
    "back</b>: " + f + " of " + C.now.n_prose + " prose paragraphs, against " + fc + " of " +
    C.control.n_prose + " in the control. The rise is the two rows above it, both ruled out. " +
    "Excluding them, S1 reads 16.45% control, 1.32% before the clauses, 1.68% now.";
})();

/* rendering ------------------------------------------------------------ */
function vd(id, defect, clean, ph) {
  const v = store[id] || {};
  return '<div class="vd" data-id="' + id + '">' +
    '<button data-v="defect" aria-pressed="' + (v.v === "defect") + '">' + defect + "</button>" +
    '<button data-v="clean" aria-pressed="' + (v.v === "clean") + '">' + clean + "</button>" +
    '<input type="text" placeholder="' + ph + '" value="' + esc(v.n || "") + '"></div>';
}

function item(h, markable) {
  const p = DATA.prompts[h.pid] || {name: h.pid, register: h.register};
  const over = h.counted ? "" :
    '<span class="tag over">' + h.words + " words · outside S1&rsquo;s cap</span>";
  const sits = '<span class="tag sits">' +
    (h.prev_kind ? "after " + (AFTER[h.prev_kind] || h.prev_kind) : "opens the answer") +
    " &rarr; " + (h.next_kind ? "before " + (AFTER[h.next_kind] || h.next_kind)
                              : "ends the answer") + "</span>";
  const before = h.prev_html ? '<div class="ctx before">' + h.prev_html + "</div>" : "";
  const after = h.next_html
    ? '<div class="ctx after' + (h.what === "lead-in" ? " solo" : "") +
      '" data-k="' + esc(h.next_kind) + '">' + h.next_html + "</div>"
    : "";
  return '<article class="item" data-w="' + h.what + '" data-r="' + h.register + '">' +
    '<div class="hd"><span class="pid">' + esc(h.pid) + "&thinsp;·&thinsp;r" + h.rep +
    '</span><span class="pname">' + esc(p.name) + '</span><span class="tag">' +
    esc(h.register) + "</span>" + sits + over + "</div>" +
    '<div class="frame"><div class="gut"><div class="st">' + SHORT[h.what] +
    '</div><div class="n">' + h.words + '</div><div class="u">words</div></div>' +
    '<div class="stack">' + before + '<div class="hit">' + h.html + "</div>" + after +
    "</div></div>" +
    (markable ? vd("hit:" + h.id, "the defect", "not the defect",
                   "why, in your words") : "") +
    "</article>";
}

function draw() {
  KINDS.forEach(([kind, sec]) => {
    const rows = DATA.hits.filter(h => h.what === kind &&
      (reg === "all" || h.register === reg));
    $("n-" + sec).textContent = rows.length + (rows.length === 1 ? " hit" : " hits");
    $("rule-" + sec).innerHTML = vd("rule:" + kind, "S1 should count it",
      "S1 should not count it", "the rule you want, in your words");
    $("list-" + sec).innerHTML = rows.length
      ? rows.map(h => item(h, true)).join("")
      : '<p class="empty">Nothing in this register.</p>';
  });
  const cr = DATA.control_floating.filter(h => reg === "all" || h.register === reg);
  $("n-ctrl").textContent = cr.length + " fragments";
  $("list-ctrl").innerHTML = cr.length
    ? cr.map(h => item(h, true)).join("")
    : '<p class="empty">Nothing in this register.</p>';
  const nm = $("naming");
  if (nm && document.activeElement !== nm) nm.value = (store["name:staccato"] || {}).n || "";
  tally();
}

function tally() {
  const ruled = KINDS.filter(([k]) => (store["rule:" + k] || {}).v).length;
  const mk = k => Object.keys(store).filter(x => x.startsWith(k) && store[x].v).length;
  const marks = mk("hit:"), cm = mk("hit:ctrl:");
  $("tally").textContent = ruled + " of 3 ruled" +
    (marks - cm ? " · " + (marks - cm) + " marked" : "") +
    (cm ? " · " + cm + " in control" : "");
}

document.addEventListener("click", e => {
  const sec = e.target.closest("[data-sec]");
  if (sec) {
    section = sec.dataset.sec;
    document.querySelectorAll("[data-sec]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.sec === section)));
    ["open", "lead", "float", "ctrl"].forEach(s =>
      $("sec-" + s).hidden = s !== section);
    window.scrollTo({top: 0, behavior: "instant"});
    return;
  }
  const r = e.target.closest("[data-r]");
  if (r && r.tagName === "BUTTON") {
    reg = r.dataset.r;
    document.querySelectorAll("[data-r]").forEach(b => {
      if (b.tagName === "BUTTON") b.setAttribute("aria-pressed", String(b.dataset.r === reg));
    });
    draw();
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
  const L = ["# The S1 ruling — " + DATA.run, "",
    "Control `" + DATA.control_run + "`, before the clauses `" + DATA.prev_run + "`.", "",
    "## The ruling", "", "| kind | hits | S1 should count it | what you want |",
    "|---|---:|---|---|"];
  KINDS.forEach(([k]) => {
    const v = store["rule:" + k] || {};
    L.push("| " + LABEL[k] + " | " + DATA.counts.now.counted[k] + " | " +
      (v.v ? (v.v === "defect" ? "yes" : "no") : "—") + " | " + (v.n || "") + " |");
  });
  const named = (store["name:staccato"] || {}).n;
  if (named) L.push("", "## The defect, named", "", "> " + named);
  const cmk = DATA.control_floating.filter(h => (store["hit:" + h.id] || {}).v);
  if (cmk.length) {
    L.push("", "## The control, marked", "",
      "| prompt | sits | words | verdict | note |", "|---|---|---:|---|---|");
    cmk.forEach(h => {
      const v = store["hit:" + h.id];
      L.push("| " + h.pid + "·r" + h.rep + " | " +
        (h.prev_kind || "opens") + " → " + (h.next_kind || "ends") + " | " + h.words +
        " | " + (v.v === "defect" ? "the defect" : "not the defect") + " | " + (v.n || "") + " |");
    });
  }
  const marked = DATA.hits.filter(h => (store["hit:" + h.id] || {}).v);
  if (marked.length) {
    L.push("", "## The hits marked", "",
      "| prompt | register | kind | words | verdict | note |",
      "|---|---|---|---:|---|---|");
    marked.forEach(h => {
      const v = store["hit:" + h.id];
      L.push("| " + h.pid + "·r" + h.rep + " | " + h.register + " | " + LABEL[h.what] +
        " | " + h.words + " | " + (v.v === "defect" ? "the defect" : "not the defect") +
        " | " + (v.n || "") + " |");
    });
  }
  const out = L.join("\n");
  try { await navigator.clipboard.writeText(out); }
  catch (e) {
    const t = document.createElement("textarea");
    t.value = out; document.body.appendChild(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  $("copy").textContent = "Copied";
  setTimeout(() => { $("copy").textContent = "Copy ruling"; }, 1600);
});

draw();
</script>
"""


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__.strip().splitlines()[-1])
    build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(),
          Path(sys.argv[3]).resolve(), Path(sys.argv[4]))
