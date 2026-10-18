#!/usr/bin/env python3
"""
Block blade — balances the block commands of a delivered script BEFORE delivery.

Usage:  python3 check_blocks.py <script.txt> [more.txt ...]
        python3 check_blocks.py -            (read one script from stdin)

A doubled `If` with one `End If` passes every other blade. Omnis accepts such
a method line by line -- `$methodlines.$add` takes each line on its own -- so
the imbalance is not refused at assign time and only shows up as behaviour,
which is the most expensive way to find it.

WHAT IS COUNTED
---------------
Only a line whose FIRST WORD is a block command.  A generator that writes
`Do lines.$add('If flag')` carries the word inside a literal and on a line that
begins with `Do`, so it is not counted -- which is the whole reason the rule is
anchored at the start of the line rather than searched for.

Comment lines (`#`, `;`) are skipped, and so is everything between
`Begin text block` and `End text block`: the lines in a text block are TEXT and
may begin with anything.

RULES
 1 UNCLOSED   an opener with no closer.  Reported at the line of the OPENER,
              because that is where the reader has to go, not at the end.
 2 UNOPENED   a closer with no opener above it.
 3 MISMATCH   a closer of the wrong kind, e.g. `End While` over an `If`.
              Omnis would refuse the method as a whole; the blade names the
              opener it collided with.
 4 ORPHAN     `Else`, `Else If`, `Case` or `Default` outside the block it
              belongs to (`Else` outside an `If`, `Case` outside a `Switch`).

WHAT IS NOT CHECKED, DELIBERATELY
Indentation.  `$methodtext` carries no indentation and Omnis rewrites method
lines (check_notation rule 3b for the same reason). A blade that
judged nesting by tabs would report the whole library.
"""
import os
import re
import sys

# opener -> the closer it demands.  The keys are matched as whole words at the
# start of a line, longest first, so `End If` is never read as `End`.
OPENERS = {
    'If': 'End If',
    'While': 'End While',
    'For': 'End For',
    'Repeat': 'Until',
    'Switch': 'End Switch',
    'Begin reversible block': 'End reversible block',
    'Begin critical block': 'End critical block',
    'Begin statement': 'End statement',
    'Begin text block': 'End text block',
    'Begin print job': 'End print job',
}
CLOSERS = set(OPENERS.values())
# a middle word and the opener it is only legal inside
MIDDLES = {'Else': 'If', 'Else If': 'If', 'Case': 'Switch', 'Default': 'Switch'}

# Longest first: 'Else If' before 'Else', 'End If' before 'End'.
_WORDS = sorted(set(OPENERS) | CLOSERS | set(MIDDLES), key=len, reverse=True)
_RE = re.compile(r'^(' + '|'.join(re.escape(w) for w in _WORDS) + r')\b',
                 re.IGNORECASE)

# The canonical spelling, keyed by the lowercase form, so a line written
# `end if` reports as `End If`.
_CANON = {w.lower(): w for w in _WORDS}


def keyword(line):
    """The block keyword a line opens with, or None."""
    s = line.strip()
    if not s or s.startswith('#') or s.startswith(';'):
        return None
    m = _RE.match(s)
    if not m:
        return None
    return _CANON[m.group(1).lower()]


def check(text):
    probs = []
    stack = []          # (keyword, lineno)
    in_text_block = False
    for n, line in enumerate(text.split('\n'), 1):
        kw = keyword(line)
        if in_text_block:
            # only its own ending is read; everything else in there is TEXT
            if kw == 'End text block':
                in_text_block = False
                stack.pop()
            continue
        if kw is None:
            continue
        if kw in OPENERS:
            stack.append((kw, n))
            if kw == 'Begin text block':
                in_text_block = True
            continue
        if kw in MIDDLES:
            want = MIDDLES[kw]
            if not stack or stack[-1][0] != want:
                where = f"inside '{stack[-1][0]}' from line {stack[-1][1]}" \
                    if stack else "at the top level"
                probs.append(f"line {n}: '{kw}' {where} -- it belongs to "
                             f"'{want}'")
            continue
        # a closer
        if not stack:
            probs.append(f"line {n}: '{kw}' closes nothing -- no open block "
                         f"above it")
            continue
        opener, oline = stack[-1]
        if OPENERS[opener] != kw:
            probs.append(f"line {n}: '{kw}' over '{opener}' from line {oline} "
                         f"-- that block wants '{OPENERS[opener]}'")
            # Pop anyway: keeping it would report every later closer as well.
            stack.pop()
            continue
        stack.pop()
    for opener, oline in reversed(stack):
        probs.append(f"line {oline}: '{opener}' is never closed -- "
                     f"'{OPENERS[opener]}' is missing")
    return probs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or args[0] == '-':
        files = [('<stdin>', sys.stdin.read())]
    else:
        files = []
        for a in args:
            if os.path.isfile(a):
                files.append((a, open(a, encoding='utf-8',
                                      errors='replace').read()))
            else:
                print(f"skip (not a file): {a}")
    bad = 0
    for name, text in files:
        probs = check(text)
        if probs:
            bad += 1
            print(f"FAIL {os.path.basename(name)}")
            for p in probs:
                print(f"     -> {p}")
        else:
            print(f"ok   {os.path.basename(name)}")
    print(f"\n{len(files)-bad}/{len(files)} clean (blocks)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
