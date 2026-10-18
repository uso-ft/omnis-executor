#!/usr/bin/env python3
"""
Constant blade — verifies every kConstant against omnis_constants_table.txt,
the table build_tables.py makes from the Omnis help.

Usage:  python3 check_constants.py <script.txt> [more.txt ...]
        python3 check_constants.py -           (read one script from stdin)

The table is looked for next to this script, then in the current directory.

An invented constant is one of the quietest failures Omnis offers: an unknown
kName evaluates as an empty/zero value rather than raising, so a comparison
simply never matches and the script reports success while doing nothing.

Scanned: `k` + uppercase letter + at least one more character, OUTSIDE single
quoted strings (a constant name mentioned inside a message text is not code).
Numeric forms such as `k0dp` are not scanned -- they are vanishingly rare in
scripts and the pattern would collide with loop variables like `k1`.

Also scanned: the lower-case families -- `kcursArrow`, `kerrNotFound`,
`kmacOS`.  `k` + lower case + an upper-case letter is also how a variable
such as `keyCode` looks, so a name of that shape is only checked when its
lower-case prefix (`kcurs`, `kerr`, ...) is the prefix of a constant in the
table.  The families come from the table, not from this file.
"""
import sys, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE_NAME = 'omnis_constants_table.txt'

RE_CONST = re.compile(r'\bk[A-Z]\w+')
RE_FAMILY = re.compile(r'\b(k[a-z]+)[A-Z]\w*')
# Omnis literals come in BOTH quote styles: 'text' with doubled inner quotes,
# and "text", which embeds a single quote without doubling. Masking only the
# single-quoted form would let the contents of a double-quoted string be read
# as code.
RE_STRING = re.compile(r"'[^']*'|\"[^\"]*\"")


def strip_trailing_comment(line):
    """Cut a trailing '## ...' comment.

    String literals are masked first: a '##' INSIDE a literal is text, not a
    comment. Cutting there would leave an unterminated quote and expose the
    rest of the literal as if it were code. Both quote styles are masked.
    """
    masked = RE_STRING.sub(
        lambda m: m.group(0)[0] + "\x00" * (len(m.group(0)) - 2) + m.group(0)[0], line)
    i = masked.find('##')
    return line if i < 0 else line[:i]


def load_consts():
    for cand in (os.path.join(HERE, TABLE_NAME), TABLE_NAME):
        if os.path.isfile(cand):
            with open(cand, encoding='utf-8', errors='replace') as fh:
                return {l.strip() for l in fh if l.strip()}, cand
    return None, None


def families(known):
    """The lower-case prefixes the table uses: kcurs, kerr, kmac ..."""
    out = set()
    for name in known:
        m = RE_FAMILY.fullmatch(name)
        if m:
            out.add(m.group(1))
    return out


def check(text, known, fams=None):
    if fams is None:
        fams = families(known)
    probs = []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if line.startswith('#'):
            continue
        line = strip_trailing_comment(line)
        # a constant named inside a literal is text, not code
        code = RE_STRING.sub("''", line)
        found = [m.group(0) for m in RE_CONST.finditer(code)]
        found += [m.group(0) for m in RE_FAMILY.finditer(code) if m.group(1) in fams]
        for name in found:
            if name not in known:
                probs.append(f"line {n}: '{name}' is not a known Omnis constant "
                             f"-- unknown kNames evaluate empty and fail SILENTLY")
    return probs


def main():
    known, tablepath = load_consts()
    if known is None:
        print(f"BLADE UNUSABLE: {TABLE_NAME} not found next to the blade "
              f"or in the current directory")
        return 2

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
    fams = families(known)
    bad = 0
    for name, text in files:
        probs = check(text, known, fams)
        if probs:
            bad += 1
            print(f"FAIL {os.path.basename(name)}")
            for p in probs:
                print(f"     -> {p}")
        else:
            print(f"ok   {os.path.basename(name)}")
    print(f"\n{len(files)-bad}/{len(files)} clean (constants, {len(known)} known)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
