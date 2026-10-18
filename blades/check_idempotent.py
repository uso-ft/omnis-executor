#!/usr/bin/env python3
"""
Idempotency blade — finds edits that grow every time the script is run.

Usage:  python3 check_idempotent.py <script.txt> [more.txt ...]
        python3 check_idempotent.py -          (read one script from stdin)

A script run twice can damage what its first run built correctly. Two
examples of the same shape:

    Calculate text2 as con(name2,'vaultPath',name3)
    Calculate text as replaceall(text,text2,con(text2,',',...))
                                      ^^^^^     ^^^^^
    replaceall(text,'Calculate cName as pClassRef.$name',
                con('Calculate cName as pClassRef.$name',kCr,...))
                     ^^^^^^^^^^ search repeated in the replacement

When the replacement CONTAINS the search, the pattern matches inside its own
result.  Run 1 is correct, run 2 doubles, run 3 triples.  Nothing in the
script says "run me only once", and nothing stops a second click.

RULE: for `replaceall(subject, search, replacement)`
  - search is a quoted literal that also appears inside replacement  -> FAIL
  - search is a bare variable whose name also appears in replacement -> FAIL

The idempotent form searches for the DOUBLED pattern instead, so a second run
finds nothing:  replaceall(text,con(p,p),p)  -- here the search `con(p,p)` is
not contained in the replacement `p`, and the blade stays quiet.

INSERTING a line into existing text is inherently non-idempotent -- the
replacement must contain the anchor, or the anchor is gone.  There is no
clever pattern that fixes this; the only real protection is a GUARD that
checks whether the change was already applied and skips the whole rewrite.
Such a line may be marked with a trailing `## GUARDED` comment.  The blade
then reports it as a NOTE instead of a failure -- the mark is not an excuse,
it is a claim the reviewer has to check: is there really a guard, and does it
test for something the rewrite introduces?

NOT flagged: replaceall calls whose search is a composed expression, and any
other command.  Narrow on purpose.
"""
import sys, re, os

# Omnis literals come in BOTH quote styles: 'text' with doubled inner quotes,
# and "text", which embeds a single quote without doubling. Masking only the
# single-quoted form would let the contents of a double-quoted string be read
# as code.
RE_STRING = re.compile(r"'[^']*'|\"[^\"]*\"")

# $methodtext.$assign with an EMPTY string deletes the method's local variables
# and parameters. '#' keeps them, '' deletes them (CONTRACT.md §3.5, Omnis
# ST/PF/1528). A generator that creates a method, declares its locals and then
# clears the placeholder this way loses every one of them, and the body it adds
# afterwards runs against variables that no longer exist. Known and still
# easy to miss, so it is checked mechanically. Drop the placeholder line
# through $methodlines instead; that never touches $lvardefs.
RE_EMPTY_ASSIGN = re.compile(r"\$methodtext\.\$assign\s*\(\s*''\s*\)")


def split_args(s):
    """Split a call's argument text on top-level commas."""
    out, depth, cur, inq = [], 0, '', False
    for ch in s:
        if ch == "'":
            inq = not inq
            cur += ch
        elif inq:
            cur += ch
        elif ch == '(':
            depth += 1
            cur += ch
        elif ch == ')':
            depth -= 1
            cur += ch
        elif ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def call_body(line, start):
    """Text between the parentheses of a call that begins at `start`."""
    i = line.find('(', start)
    if i < 0:
        return None
    depth, inq = 0, False
    for j in range(i, len(line)):
        ch = line[j]
        if ch == "'":
            inq = not inq
        elif inq:
            continue
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return line[i + 1:j]
    return None


def check(text):
    probs = []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if line.startswith('#'):
            continue
        i = line.find('##')
        if i >= 0:
            line = line[:i]

        if RE_EMPTY_ASSIGN.search(line):
            probs.append(
                f"line {n}: $methodtext.$assign('') deletes the method's local "
                f"variables and parameters. Use $assign('#') to keep them, and "
                f"drop the placeholder line through $methodlines afterwards")

        guarded = 'GUARDED' in raw
        for m in re.finditer(r'\breplaceall\s*\(', line):
            body = call_body(line, m.start())
            if body is None:
                continue
            args = split_args(body)
            if len(args) < 3:
                continue
            search, repl = args[1], args[2]

            if search.startswith("'") and search.endswith("'") and len(search) > 2:
                if search[1:-1] and search[1:-1] in repl:
                    if guarded:
                        probs.append(
                            f"NOTE line {n}: insertion marked ## GUARDED -- verify the "
                            f"guard really skips the rewrite when already applied")
                    else:
                        probs.append(
                            f"line {n}: replaceall search {search[:40]}... is contained "
                            f"in its own replacement -- NOT idempotent, a second run "
                            f"doubles it. Search for the DOUBLED pattern instead.")
                continue

            if re.fullmatch(r'[A-Za-z_]\w*', search):
                if re.search(r'\b' + re.escape(search) + r'\b', repl):
                    if guarded:
                        probs.append(
                            f"NOTE line {n}: insertion marked ## GUARDED -- verify the "
                            f"guard really skips the rewrite when already applied")
                    else:
                        probs.append(
                            f"line {n}: replaceall search '{search}' also appears in "
                            f"its own replacement -- NOT idempotent, a second run "
                            f"doubles it. Search for the DOUBLED pattern instead.")
    return probs


def main():
    args = sys.argv[1:]
    if not args or args[0] == '-':
        files = [('<stdin>', sys.stdin.read())]
    else:
        files = []
        for a in args:
            if os.path.isfile(a):
                files.append((a, open(a, encoding='utf-8', errors='replace').read()))
            else:
                print(f"skip (not a file): {a}")
    bad = 0
    for name, text in files:
        probs = check(text)
        hard = [p for p in probs if not p.startswith('NOTE ')]
        soft = [p for p in probs if p.startswith('NOTE ')]
        if hard:
            bad += 1
            print(f"FAIL {os.path.basename(name)}")
        else:
            print(f"ok   {os.path.basename(name)}")
        for p in hard:
            print(f"     -> {p}")
        for p in soft:
            print(f"     .. {p[5:]}")
    print(f"\n{len(files)-bad}/{len(files)} clean (idempotency)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
