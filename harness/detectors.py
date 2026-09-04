#!/usr/bin/env python3
"""Detectors implementing TAXONOMY.md.

Every detector here corresponds to a numbered taxonomy entry and was justified
against a quoted passage from a real baseline sample (DESIGN.md 4.2b). None was
invented a priori.

Cadence detectors (S1-S3) rank above markup detectors (S4-S6): the defects that
make the prose tiring are prosodic, and markup rates must never stand in for
them.

Rates are per 1,000 words except where the unit says otherwise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

FENCE = re.compile(r"```.*?```", re.S)
# Line-anchored, so a fence only ever opens and closes at the start of a line.
FENCE_BLOCK = re.compile(r"^```.*?^```[^\n]*$", re.S | re.M)
INLINE_MD = re.compile(r"\*\*|\*|`|_")
HEADER = re.compile(r"^#{1,6}\s+\S", re.M)
BOLD_HEADER = re.compile(r"^\*\*[^*\n]{2,70}\*\*:?\s*$", re.M)
TABLE_ROW = re.compile(r"^\|.*\|\s*$", re.M)
LIST_ITEM = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s)")
HRULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def unwrap(raw: str) -> str:
    """Undo a whole answer wrapped in one code fence.

    Two samples in `ablate-R03` return an entire README inside a ```markdown
    fence. The non-greedy FENCE regex then pairs the outer opener with the
    first inner closer, and every prose metric is computed on shell commands.
    Nested same-length fences are ambiguous in general; this handles the case
    that actually occurs -- the model fenced its whole reply. The inner fence
    count is the guard, so an answer that really is one code block is left be.
    """
    lines = raw.strip().splitlines()
    if len(lines) < 4 or not lines[0].startswith("```") or len(lines[0].strip()) <= 3:
        return raw                      # no opener, or an opener with no info string
    fences = [i for i, l in enumerate(lines) if l.strip().startswith("```")]
    if len(fences) < 4 or len(fences) % 2:
        return raw                      # no nesting inside, or unbalanced
    # The outer wrapper closes at the last fence; anything after it is the
    # model's own commentary and stays. One sample ends with a paragraph there.
    close = fences[-1]
    return "\n".join(lines[1:close] + lines[close + 1:])


def segment(raw: str) -> list[tuple[str, str]]:
    """The document as classified blocks, in order, fences kept whole.

    Detectors that cannot see a paragraph's neighbours misread it -- S1 proved
    that three times over (DESIGN.md 4.2b). This is the shared view so that a
    detector can ask what sits either side of a block.
    """
    out: list[tuple[str, str]] = []
    pos = 0
    for m in FENCE_BLOCK.finditer(raw):
        out += _plain(raw[pos:m.start()])
        out.append(("code", m.group(0)))
        pos = m.end()
    out += _plain(raw[pos:])
    return out


def _plain(chunk: str) -> list[tuple[str, str]]:
    res = []
    for block in re.split(r"\n\s*\n", chunk):
        b = block.strip()
        if not b:
            continue
        if HRULE.match(b):
            kind = "rule"          # a horizontal rule is not a paragraph
        elif b.startswith("#"):
            kind = "header"
        elif b.startswith("|"):
            kind = "table"
        elif b.startswith(">"):
            kind = "quote"
        elif LIST_ITEM.match(b):
            kind = "list"
        else:
            kind = "prose"
        res.append((kind, b))
    return res


@dataclass
class Doc:
    """One sample, normalized once so every detector sees the same text."""
    raw: str

    def __post_init__(self) -> None:
        self.raw = unwrap(self.raw)
        self.words = len(self.raw.split()) or 1
        self.blocks = segment(self.raw)

        # Prose paragraphs: blocks that are not headers, list items, table
        # rows, blockquotes, horizontal rules or code. Cadence is a property of
        # prose, and list items would otherwise register as one-sentence
        # paragraphs en masse.
        self.paragraphs: list[str] = [INLINE_MD.sub("", b)
                                      for k, b in self.blocks if k == "prose"]

        self.para_sents = [self._split(p) for p in self.paragraphs]
        self.sentences = [s for group in self.para_sents for s in group]

    @staticmethod
    def _split(p: str) -> list[str]:
        p = re.sub(r"\b([A-Z]|etc|e\.g|i\.e|vs|approx)\.\s", r"\1<DOT> ", p)
        parts = re.split(r"(?<=[.!?])\s+", p)
        return [s.replace("<DOT>", ".").strip() for s in parts if s.strip()]

    def per_k(self, n: int) -> float:
        return round(n * 1000 / self.words, 3)


# --------------------------------------------------------------- suppressed --

def s1_one_sentence_paragraphs(d: Doc) -> float:
    """Taxonomy 1 - the staccato. Share of prose paragraphs that are a single
    short sentence. Baseline 30.0% (A). Invisible to sentence-level metrics:
    the chop is between sentences, not inside them."""
    if not d.paragraphs:
        return 0.0
    n = sum(1 for g in d.para_sents
            if len(g) == 1 and len(g[0].split()) <= 25)
    return round(100 * n / len(d.paragraphs), 2)


def s2_long_then_punch(d: Doc) -> float:
    """Taxonomy 2 - the mannered cadence. Share of prose paragraphs ending in a
    sentence of <=9 words directly after one of >=20. Baseline 10.4% (A).

    Evidence: "...or with wall time (an expiry - token TTL, idle reaper, lease).
    That correlation alone splits the field in half."  [a-control-c02-r1]"""
    if not d.paragraphs:
        return 0.0
    n = 0
    for g in d.para_sents:
        if len(g) < 2:
            continue
        lens = [len(s.split()) for s in g]
        if lens[-1] <= 9 and max(lens[:-1]) >= 20:
            n += 1
    return round(100 * n / len(d.paragraphs), 2)


def s2_counts(d: Doc) -> tuple[int, int]:
    """S2's numerator and denominator, kept apart so the arm can pool them.

    s2_long_then_punch returns one sample's percentage, and averaging those
    percentages weighs a 3-paragraph reply the same as a 30-paragraph document.
    The arm's real rate is punch paragraphs over all paragraphs, so score.py
    sums these across the arm instead. See DETECTORS_POOLED."""
    if not d.paragraphs:
        return 0, 0
    n = 0
    for g in d.para_sents:
        if len(g) < 2:
            continue
        lens = [len(s.split()) for s in g]
        if lens[-1] <= 9 and max(lens[:-1]) >= 20:
            n += 1
    return n, len(d.paragraphs)


# Metrics whose arm-level value is a pooled ratio rather than a mean of
# per-sample ratios: {id: (counter, scale)}. Only S2 for now. S1, S3 and every
# per-1k-word rate have the same shape and are not pooled yet, because changing
# them moves the numbers R02 was attributed on and that is a decision, not a
# repair. score.py --pooling-report measures what it would do to each.
DETECTORS_POOLED = {"S2": (s2_counts, 100.0)}


PIVOT = re.compile(
    # "Its" is a possessive, not the pivot: taxonomy entry 3 names "It's".
    r"^(?:(?:That|This|Those|These)(?:'s|s|\s+(?:is|are|was|means|matters|alone))"
    r"|It(?:'s|\s+(?:is|are|was|means|matters|alone)))\b")


def s3_pivot_opener(d: Doc) -> float:
    """Taxonomy 3 - delivery mechanism for the epigram. Share of sentences
    opening with a That/This/It pivot. Baseline 4.1% (A).

    Evidence: "That's coupling you'll regret at deletion time." [a-control-c04-r2]"""
    if not d.sentences:
        return 0.0
    n = sum(1 for s in d.sentences if PIVOT.match(s))
    return round(100 * n / len(d.sentences), 2)


def s4a_header_rate(d: Doc) -> float:
    """Taxonomy 4 - reflexive sectioning. Baseline 9.00/1k (A), 67% of samples."""
    return d.per_k(len(HEADER.findall(d.raw)) + len(BOLD_HEADER.findall(d.raw)))


def s4b_table_row_rate(d: Doc) -> float:
    """Taxonomy 4 - reflexive tabulation. Baseline 4.21/1k (A)."""
    return d.per_k(len(TABLE_ROW.findall(d.raw)))


INLINE_BOLD = re.compile(r"(?<!^)(?<!\n)\*\*[^*\n]{3,80}\*\*")
# A bold label opening a list entry: R06 permits it, so S5 must not count it.
LIST_LABEL = re.compile(r"^(\s*(?:[-*+]|\d+\.)\s+)\*\*[^*\n]{2,80}\*\*(?::|\.|,)?", re.M)


def s5_inline_bold(d: Doc) -> float:
    """Taxonomy 5 - typography standing in for intonation. Bold inside prose
    rather than as a header or a label. Baseline 3.97/1k (A), 6.81 (B).

    Evidence: "that's **5.1 billion rows**" [a-control-c04-r2]

    Two forms are excluded, and both are the use R06 permits: bold occupying a
    whole line, which is a label standing over a paragraph, and bold opening a
    list item, which is a label at the head of an entry. The second was counted
    until 2026-09-04 because the bullet sits before it, so the metric reported
    the rules restoring lists as a ratified defect coming back. Excluding it,
    the ruled arms carry no inline bold at all. The copyeditor ruled that a bold
    list label is not a defect; see TAXONOMY.md entry 5."""
    body = BOLD_HEADER.sub("", FENCE.sub("", d.raw))
    body = LIST_LABEL.sub(r"\1", body)
    return d.per_k(len(INLINE_BOLD.findall(body)))


# R06 permits the em-dash "where a sentence is interrupted and then resumed"
# and forbids it "as a general joint between two clauses". Taxonomy entry 6
# names only the joint: "used where a comma, colon, or full stop would serve".
# Matched dashes within one unit are the permitted interruption; the odd one
# out is the joint. A unit is a sentence or a single line, so a list item
# carrying "`--apply` — perform the renames" counts on its own.
EM_UNIT = re.compile(r"(?<=[.!?])\s+|\n")


def _em_dash_split(d: Doc) -> tuple[int, int]:
    """(paired interruptions, unpaired joints), fences excluded."""
    paired = joints = 0
    for unit in EM_UNIT.split(FENCE_BLOCK.sub("", d.raw)):
        n = unit.count("—")
        paired += n - n % 2
        joints += n % 2
    return paired, joints


def s6_em_dash(d: Doc) -> float:
    """Taxonomy 6 - the em-dash as a joint where a comma, colon or full stop
    would serve. Baseline 9.54/1k (A).

    Counted every em-dash until 2026-09-04, including the paired interruption
    R06 calls correct, which is 21% of the control's hits and was overstating
    every arm. Same fault as S5 counting a bold list label and S3 counting
    "Its": a detector contradicting the rule it serves.

    Evidence: "because none of this is random — the flag is a fixed property of
    the file" [a-guide-as-shipped-c02-r2]. The permitted use is K5.
    """
    return d.per_k(_em_dash_split(d)[1])


ARROW = re.compile(r"->|=>|[\u2192\u21d2\u2190\u21d0]")


def s8_arrow(d: Doc) -> float:
    """Taxonomy 7 - the arrow as connective. Per 1k words, fences excluded.

    Named by the copyeditor three times over while they were marking something
    else, which is what qualifies it under DESIGN.md 4.2b:
    "The use of an arrow. That's not how a human writes."     [a-control-c01-r2]
    "Too much ise of dashes, em dashes, arrows."              [a-control-c01-r3]
    "That arrow again."                                       [a-control-c01-r3]

    Evidence: "8 passing -> 3 failing" [a-control-c01-r1]. Baseline 1.69/1k (A),
    39% of samples. Every arrow in the control is the unicode form; not one
    ASCII arrow appears in prose outside a fence.

    style/rules.md never names an arrow, so the fall to 0.03 is a side effect of
    rules aimed elsewhere and nothing holds it there. That is the reason to
    measure it: an unmeasured win is one a later rule change can undo unseen.
    """
    return d.per_k(len(ARROW.findall(FENCE_BLOCK.sub("", d.raw))))


LABEL_MAX_WORDS = 12
LABEL_STOPS = (".", "!", "?", ":", ",", ";")


def s9_unattached_label(d: Doc) -> float:
    """Taxonomy 8 - a bare label standing where a colon lead-in belongs.

    A short prose block, one line, no terminal punctuation, that introduces the
    block below it rather than sectioning the document. The copyeditor marked
    two of these and said what they wanted instead:

        Unverified                                            [a-control-c01-r1]
        "Is that really its own sentence? Regardless, I think it should be
        'The following is unverified:' and be part of the following paragraph."

    The document's own first block is excluded: a pull-request description that
    opens with its title is following the register, not committing the defect.

    Read this beside S4a, not instead of it. Fourteen of the control's fifteen
    hits are bold, so S4a already counts them among its headers; what S4a cannot
    say is that they are labels rather than sections, and that they cluster in
    the conversational register where a reply should have no headers at all.
    """
    n = 0
    for i, (kind, text) in enumerate(d.blocks):
        if kind != "prose" or i == 0 or i + 1 >= len(d.blocks):
            continue
        t = INLINE_MD.sub("", text).strip()
        if "\n" in t or t.endswith(LABEL_STOPS):
            continue
        if 1 <= len(t.split()) <= LABEL_MAX_WORDS:
            n += 1
    return d.per_k(n)


# ----------------------------------------------------------------- held out --
# Never named in style/rules.md. If the suppressed metrics fall while these sit
# still, the rules are dodging named tokens rather than changing how it writes.

OFFER = re.compile(
    r"(?i)(want me to|shall i|if you (?:tell|give|share|point) me|say the word"
    r"|happy to|i can (?:give|write|do|run|pull|draft))")


def s7_terminal_offer(d: Doc) -> float:
    """Taxonomy 7. Share of samples closing with a service offer. Baseline 17%
    (A), 23% (B). Held out until R01 moved it 23%->7% without naming it, which
    showed the guard was not independent of the rules."""
    tail = "\n".join(d.raw.rstrip().splitlines()[-3:])
    return 100.0 if OFFER.search(tail) else 0.0


HEDGE = re.compile(r"(?i)\b(?:might|may|could|possibly|perhaps|likely|arguably|somewhat)\b")


def h1_hedge_density(d: Doc) -> float:
    """Held out. Replaces terminal offer. Baseline 1.51/1k (A), 2.00 (B).
    Unrelated to cadence and to closing moves, so a cadence rule should not
    touch it."""
    return d.per_k(len(HEDGE.findall(d.raw)))


INTENSIFIER = re.compile(r"(?i)\b(?:genuinely|actually|truly|really)\b")


def h2_intensifier(d: Doc) -> float:
    """Held out. Baseline 1.20/1k (A), 1.87 (B)."""
    return d.per_k(len(INTENSIFIER.findall(d.raw)))


TRICOLON = re.compile(r"\b\w+, \w+,? and \w+\b")


def h3_tricolon(d: Doc) -> float:
    """Held out. Baseline 0.54/1k (A), 0.57 (B)."""
    return d.per_k(len(TRICOLON.findall(d.raw)))


# --------------------------------------------------------------- collateral --
# Not defects. The inverse: structure the rules must not destroy. R04 names
# headings and tables only, but the model generalized it to every structural
# device, and nothing in the suppressed set could see that happen. Both entries
# were justified by a copyeditor reading the galley of the longest paragraphs
# and rejecting the length hypothesis in favour of these.

LIST_ITEM_M = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s)", re.M)


def k1_list_items(d: Doc) -> float:
    """Enumerable content kept as a list. Control 11.61/1k conversational,
    9.61 document; shipped rules 0.00 and 1.91.

    Evidence, on a 292-word paragraph running six competing explanations
    together as sentences: "I think it would read better if wrote the
    alternative explanations as a list rather than part of one big paragraph."
    [a-treatment-c02-r1#2]"""
    return d.per_k(len(LIST_ITEM_M.findall(FENCE.sub("", d.raw))))


def k2_code_blocks(d: Doc) -> float:
    """Worked examples kept as code. Control 4.48/1k on documents, shipped 1.94.

    Evidence, on a migration guide enumerating three dict habits in continuous
    prose: "There's too much prose here without examples. I'm supposed to be
    reading a guide, not a novel." [a-treatment-d05-r3#5]"""
    return d.per_k(len(FENCE.findall(d.raw)))


def k3_opening_paragraph(d: Doc) -> float:
    """The answer stated before it is explained. Control 28.4 words on
    substrate A, shipped rules 64.9; one-sentence openers fall 16/36 to 5/36.

    The opening paragraph is where the control puts its verdict, alone, and
    then explains it. R02 reads a standalone verdict as a paragraph cut away
    from the one after it and joins them, which is the same move that took the
    list items in K1 and the code blocks in K2. Rising here means the reader
    has to find the answer inside the reasoning instead of being handed it.

    Evidence, on a 150-word paragraph developing a design the answer rejects:
    "It's not too long in the strictest sense but it's discussing at length
    what turns out to be wrong advice. The control is directly saying it's a
    bad idea." [a-treatment-c04-r2#3]"""
    if not d.paragraphs:
        return 0.0
    return float(len(d.paragraphs[0].split()))


# A table block, and the grid test R04 already states in words: several things
# compared across the same dimensions, where a reader will want to find one
# cell. The median-cell bound is what separates that from R04's own
# counter-example, "a column of labels beside a column of prose". Calibrated
# against every table in the control, substrate A: 18 of them, median body cell
# 1.0 to 7.0 words, 2 to 5 columns. The bound exists so that a rule which
# brings tables back cannot be credited for bringing pseudo-tables back.

TABLE_BLOCK = re.compile(r"(?:^\|.*\|[ \t]*\n)+", re.M)
TABLE_RULE = re.compile(r"^\|[\s:\-|]+\|$")


def _grid_tables(d: Doc) -> int:
    n = 0
    for m in TABLE_BLOCK.finditer(FENCE.sub("", d.raw)):
        rows = [r for r in m.group(0).strip().split("\n")
                if not TABLE_RULE.match(r.strip())]
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        if len(cells) < 3 or max(len(c) for c in cells) < 2:
            continue
        body = [len(c.split()) for row in cells[1:] for c in row]
        if body and sorted(body)[len(body) // 2] <= 8:
            n += 1
    return n


def k4_grid_tables(d: Doc) -> float:
    """Tabular content kept as a table. Control 2.94 per 1k words on documents
    and 0.53 on conversational replies; the shipped rules take both to 0.00.
    Substrate A holds 18 control tables and no treatment table at all.

    The suppressed twin S4b counts every table row and reads its fall to 0.00 as
    R04 working. The ratified defect behind S4b is markup on a chat reply, and
    its quoted evidence is a debugging answer carrying six H2 sections and a
    seven-row table. Document tables were never the target, and R04's own text
    licenses them.

    Evidence, on a postmortem that narrates its timeline in prose because the
    control's Time/Event table is gone: "This is jumping too far ahead to
    'Nothing in our monitoring reacted...' instead of explaining the sequence
    and the cause first." [a-treatment-d04-r2#2] The copyeditor confirmed on
    being asked that the missing table is the complaint."""
    return d.per_k(_grid_tables(d))


# ------------------------------------------------------------------ context --
# Not defects. Reported so a metric change can be read against how much the
# volume and shape of the output moved.

def c1_words(d: Doc) -> float:
    return float(d.words)


def c2_mean_para_words(d: Doc) -> float:
    if not d.paragraphs:
        return 0.0
    return round(sum(len(p.split()) for p in d.paragraphs) / len(d.paragraphs), 2)


def c3_mean_sentence_words(d: Doc) -> float:
    if not d.sentences:
        return 0.0
    return round(sum(len(s.split()) for s in d.sentences) / len(d.sentences), 2)



def k5_em_dash_interruption(d: Doc) -> float:
    """The em-dash use R06 permits, kept visible so over-suppression shows.

    A rule aimed at the joint can take the interruption with it, and a metric
    that counts both cannot tell the two apart. The control writes 44 of these
    against 170 joints.
    """
    return d.per_k(_em_dash_split(d)[0])


DETECTORS = [
    ("S1", "one-sentence paragraphs",   "% of paragraphs", "suppressed", s1_one_sentence_paragraphs),
    ("S2", "long sentence then punch",  "% of paragraphs", "suppressed", s2_long_then_punch),
    ("S3", "That/This pivot opener",    "% of sentences",  "suppressed", s3_pivot_opener),
    ("S4a", "headers",                  "per 1k words",    "suppressed", s4a_header_rate),
    ("S4b", "table rows",               "per 1k words",    "suppressed", s4b_table_row_rate),
    ("S5", "inline bold emphasis",      "per 1k words",    "suppressed", s5_inline_bold),
    ("S6", "em-dash",                   "per 1k words",    "suppressed", s6_em_dash),
    ("S7", "terminal service offer",    "% of samples",    "suppressed", s7_terminal_offer),
    ("S8", "arrow as connective",       "per 1k words",    "suppressed", s8_arrow),
    ("S9", "unattached label",          "per 1k words",    "suppressed", s9_unattached_label),
    ("H1", "hedge density",             "per 1k words",    "held-out",   h1_hedge_density),
    ("H2", "intensifier density",       "per 1k words",    "held-out",   h2_intensifier),
    ("H3", "tricolon",                  "per 1k words",    "held-out",   h3_tricolon),
    ("K1", "list items",                "per 1k words",    "collateral", k1_list_items),
    ("K2", "code blocks",               "per 1k words",    "collateral", k2_code_blocks),
    ("K3", "opening paragraph",        "words",           "collateral", k3_opening_paragraph),
    ("K4", "grid tables",              "per 1k words",    "collateral", k4_grid_tables),
    ("K5", "em-dash interruption",     "per 1k words",    "collateral", k5_em_dash_interruption),
    ("C1", "output length",             "words",           "context",    c1_words),
    ("C2", "mean paragraph length",     "words",           "context",    c2_mean_para_words),
    ("C3", "mean sentence length",      "words",           "context",    c3_mean_sentence_words),
]


def score_text(text: str) -> dict[str, float]:
    d = Doc(text)
    return {mid: fn(d) for mid, _, _, _, fn in DETECTORS}


def count_text(text: str) -> dict[str, tuple[int, int]]:
    """Numerator and denominator for every pooled metric, per sample."""
    d = Doc(text)
    return {mid: fn(d) for mid, (fn, _) in DETECTORS_POOLED.items()}
