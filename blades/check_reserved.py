#!/usr/bin/env python3
"""
Name blade -- checks the names a script INVENTS for something in the library.

Usage:  python3 check_reserved.py <script.txt> [more.txt ...]
        python3 check_reserved.py -            (read one script from stdin)

The table is looked for next to this script, then in the current directory.

WHAT THIS CATCHES.  A script that creates a method, a variable definition or a
column chooses a name, and three kinds of name are refused or subverted by
Omnis.  None of them is visible to the other blades, because every such name
arrives as a STRING LITERAL inside a perfectly ordinary `$add(...)` call.

  1 RESERVED   Thirteen $-names may not be used for CUSTOM notation.  Any
    other $-name is allowed, and a custom method carrying the name of a
    standard one OVERRIDES it -- these thirteen are the exception that does
    not.  Source: Omnis Programming, chapter 3.

  2 CHARS      A variable name may hold Unicode letters, digits and U+80 to
    U+ff; the first character may not be a digit; `. $ & ( ) [ ] #` and
    spaces are forbidden, `_` is allowed.  Same chapter.

  3 FLAG       `flag` is the spoken name of #F and belongs to the command
    grammar (`If flag true`, `While flag false` ...).  A variable called
    `flag` CAN be declared and CAN be assigned -- measured, and that is what
    makes it dangerous -- but `If flag` is refused, and one
    refused line makes `$methodtext.$assign` refuse the whole body.  The
    Executor variable set carries `flag1`, `flag2`, `flag3` for this reason.
    `check_commands` catches the USE; this rule catches the DECLARATION, one
    step earlier.

WHAT THIS DOES NOT CATCH, by design.  A name built at run time --
`$lvardefs.$add(con('p',name),...)` -- is invisible here, because the blade
only reads literals.  Class names are not checked: they follow their own
rules.
"""
import sys, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE_NAME = 'omnis_reserved_table.txt'

# The groups whose $add names a METHOD, and those whose $add names a VARIABLE
# or a COLUMN.  $cols.$add is in the second set: a column name reaches Omnis
# through the same door as a variable name and is subject to the same rules.
RE_METHOD_ADD = re.compile(
    r'\$(?:methods|classmethods|instancemethods)\s*\.\s*\$add\s*\(\s*'
    r'''(''|['"])(.*?)\1''')
RE_VAR_ADD = re.compile(
    r'\$(?:lvardefs|cvardefs|ivardefs|tvardefs|vardefs|cols)\s*\.\s*\$add\s*\(\s*'
    r'''(''|['"])(.*?)\1''')

# A generator writes the $add INSIDE a literal, where its quotes are doubled:
# Do list.$add('Do pList.$cols.$add(''kind'',...)'). The alternation above reads
# ''kind'' as the name kind, not as an empty name.
FORBIDDEN = set('.$&()[]#')


def load_reserved():
    for cand in (os.path.join(HERE, TABLE_NAME), TABLE_NAME):
        if os.path.isfile(cand):
            names = set()
            with open(cand, encoding='utf-8', errors='replace') as fh:
                for raw in fh:
                    entry = raw.strip()
                    if entry and not entry.startswith('#'):
                        names.add(entry.lower())
            return names, cand
    return None, None


def check_name(name):
    """Return a reason string, or None when the name is acceptable."""
    if not name:
        return "the name is empty"
    if name[0].isdigit():
        return "a variable name may not begin with a digit"
    bad = sorted({c for c in name if c in FORBIDDEN})
    if bad:
        return ("carries " + ' '.join(repr(c) for c in bad) +
                " -- forbidden in a variable name (. $ & ( ) [ ] #)")
    if ' ' in name or '\t' in name:
        return "carries a space -- use _ instead"
    return None


def check(text, reserved):
    probs = []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue

        for m in RE_METHOD_ADD.finditer(line):
            name = m.group(2)
            if name.lower() in reserved:
                probs.append(
                    f"line {n}: '{name}' is one of the thirteen reserved names "
                    f"and may not be used for custom notation -- see "
                    f"{TABLE_NAME}")
            elif not name.startswith('$'):
                probs.append(
                    f"line {n}: method name '{name}' does not start with '$' "
                    f"-- a custom method name must")

        for m in RE_VAR_ADD.finditer(line):
            name = m.group(2)
            if name.lower() == 'flag':
                probs.append(
                    f"line {n}: a variable called 'flag' can be declared and "
                    f"assigned, but 'If flag' is refused -- 'flag' is the "
                    f"keyword for #F. Use flag1, flag2, flag3 or a compound "
                    f"name")
                continue
            reason = check_name(name)
            if reason:
                probs.append(f"line {n}: '{name}' -- {reason}")
    return probs


def main():
    reserved, tablepath = load_reserved()
    if reserved is None:
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
                files.append((a, open(a, encoding='utf-8',
                                      errors='replace').read()))
            else:
                print(f"skip (not a file): {a}")
    bad = 0
    for name, text in files:
        probs = check(text, reserved)
        if probs:
            bad += 1
            print(f"FAIL {os.path.basename(name)}")
            for p in probs:
                print(f"     -> {p}")
        else:
            print(f"ok   {os.path.basename(name)}")
    print(f"\n{len(files)-bad}/{len(files)} clean (names, "
          f"{len(reserved)} reserved)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
