#!/usr/bin/env python3
"""
Stamp blade -- the header identity and the RUN STAMP must be the same words.

Usage:  python3 check_stamp.py <script.txt> [more.txt ...]
        python3 check_stamp.py -            (read one script from stdin)

WHY THIS EXISTS
---------------
Every delivered script carries its identity TWICE.  Once in the header, which
`$parseHeader` reads and which drives the log title and, through `cLogTitle` and
`$runFolderPath`, the name of the run folder:

    # GENERATOR: demo_create v2 - 2026-10-15 01:40 - ...

And once as a literal in its own first operative line, the run stamp
(CONTRACT.md §1.6):

    Calculate result as con('run ',#T,' - demo_create v2',kCr)

Nothing keeps them together. A version bump changes the first and forgets the
second, and the protocol then opens with a line naming the WRONG VERSION of the
script that produced it -- while the run folder beside it is right, because it
is derived. A log row that names the wrong version is worse than one with no
title at all: it sends a later reader to the wrong file with full confidence.

WHAT IS CHECKED
---------------
Only when BOTH are present.  A script with no header is not this blade's
business (`check_header` decides that), and a script with no run stamp is not
failed either: most negative probes carry neither, and a throwaway one-liner
deserves no ceremony.

The comparison is on NAME and VERSION, nothing else.  The date, the time and the
one-line description in the header have no counterpart in the stamp.

The stamp is read as Omnis reads it: the literals of the line are joined,
doubled quotes resolved, and the LAST `<name> v<n>` in the result is taken --
last, because `con('run ',#T,' - name v1',kCr)` puts the identity at the end and
a description in front of it would otherwise win.

THE TRADE
---------
A miss is cheap here and a false alarm is not, so anything unclear goes quiet:
no header line, no stamp line, or a stamp whose literals hold no `<word> v<n>`
at all -- all three report a NOTE and pass.  What it will not do is stay quiet
when both names are there and disagree.
"""
import os
import re
import sys

RE_HEAD = re.compile(r"^#\s*(GENERATOR|READER|PROBE):\s*(\S+)\s+v(\d+(?:\.\d+)?)\b")
RE_STAMP = re.compile(r"^Calculate\s+\w+\s+as\s+con\(\s*'run\s*'")
RE_LIT = re.compile(r"'((?:[^']|'')*)'")
RE_IDENT = re.compile(r"([A-Za-z_][\w]*)\s+v(\d+(?:\.\d+)?)\b")


def header_identity(text):
    for line in text.split('\n'):
        m = RE_HEAD.match(line.strip())
        if m:
            return m.group(2), m.group(3)
    return None, None


def stamp_identity(text):
    """the last <name> v<n> inside the literals of the run stamp line"""
    for line in text.split('\n'):
        s = line.strip()
        if not RE_STAMP.match(s):
            continue
        joined = ''.join(p.replace("''", "'") for p in RE_LIT.findall(s))
        ms = RE_IDENT.findall(joined)
        if ms:
            return ms[-1][0], ms[-1][1], s
        return None, None, s
    return None, None, None


def check(text):
    """returns (problems, notes)"""
    probs, notes = [], []
    hname, hver = header_identity(text)
    sname, sver, sline = stamp_identity(text)
    if hname is None:
        notes.append("no header identity line -- not this blade's business")
        return probs, notes
    if sline is None:
        notes.append(f"header says '{hname} v{hver}'; the script carries no run "
                     f"stamp, which is allowed")
        return probs, notes
    if sname is None:
        notes.append(f"header says '{hname} v{hver}'; the run stamp holds no "
                     f"'<name> v<n>' -- nothing to compare")
        return probs, notes
    if sname != hname:
        probs.append(f"the header calls this script '{hname}' and the run stamp "
                     f"calls it '{sname}'. The log title and the run folder come "
                     f"from the HEADER, so the protocol would open under a name "
                     f"the folder does not carry")
    if sver != hver:
        probs.append(f"the header says v{hver} and the run stamp says v{sver}. "
                     f"The protocol of this run would claim the wrong VERSION of "
                     f"the script that produced it -- a version bump has to "
                     f"change BOTH places")
    return probs, notes


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
        probs, notes = check(text)
        base = os.path.basename(name)
        if probs:
            bad += 1
            print(f"FAIL {base}")
            for p in probs:
                print(f"     -> {p}")
        else:
            print(f"ok   {base}")
        for n in notes:
            print(f"     .. {n}")
    print(f"\n{len(files)-bad}/{len(files)} clean (stamp)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
