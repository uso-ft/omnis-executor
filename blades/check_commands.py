#!/usr/bin/env python3
"""
Command blade — verifies that every operative line starts with a REAL Omnis
command, checked against omnis_command_table.txt (made by build_tables.py).

Usage:  python3 check_commands.py <script.txt> [more.txt ...]
        python3 check_commands.py -            (read one script from stdin)

The table is looked for next to this script, then in the current directory.

WHAT THIS CATCHES: invented or mistyped command heads -- `Calculatte`,
`Send to tracelog`, `Close designs`.  That is the failure mode this blade
exists for: a command that simply does not exist.

WHAT IT DOES NOT CATCH, by design: argument forms.  The table lists commands
in their reference form with placeholder words -- `If calculation`,
`While calculation`, `For each line in list` -- which never appear literally
in written code (`If cBackup&iTargetRef`, `For k from 1 to 50 step 1`).
Matching whole entries against real lines would flag correct code on nearly
every loop and conditional, and a blade that cries wolf gets switched off.
So the check is deliberately coarse: the HEAD word must exist.
`Set referense x to y` therefore passes (head `Set` is real) -- the notation
and variable blades are the net for that.
"""
import sys, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE_NAME = 'omnis_command_table.txt'


def load_heads():
    for cand in (os.path.join(HERE, TABLE_NAME), TABLE_NAME):
        if os.path.isfile(cand):
            heads = set()
            entries = set()
            with open(cand, encoding='utf-8', errors='replace') as fh:
                for raw in fh:
                    entry = raw.rstrip('\n').strip()
                    if not entry:
                        continue
                    entries.add(entry)
                    heads.add(entry.split()[0])
            return heads, entries, cand
    return None, None, None


# Commands whose argument is a CALCULATION, never message text.  Curly braces
# there are Omnis 7 syntax; the current compiler rejects the line, it is stored
# empty, and the Executor's read-back check reports expected/received. Old
# pages still show `Test for valid calculation {evalf(...)}`; the form appears
# nowhere in the current help. Message commands (OK message, Send to trace log,
# Working message ...) DO take braces and are not listed here.
CALC_COMMANDS = (
    'Test for valid calculation', 'Set search as calculation',
    'Calculate', 'If', 'While', 'Until', 'Do',
)
RE_BRACE = re.compile(r'\{')
RE_STRING = re.compile(r"'[^']*'|\"[^\"]*\"")

# --- two FORM rules, against the grain of the head-only design ---------------
# The docstring above says argument forms are out of scope, and that stays true
# for the general case.  These two are exceptions because each is a single,
# certain, silent failure that no other blade sees.
#
# `flag` is the spoken name of #F and appears only in the long forms
# `If flag true`, `If flag false`, `While flag true|false`, `Until flag ...`,
# `Else If flag ...`.  A bare `If flag` is an unfinished command: Omnis refuses
# the LINE, and one refused line makes $methodtext.$assign refuse the whole
# body. `flag1`, `flag2`, `flag3` are ordinary names and must not fire -- \b does it.
RE_FLAGWORD = re.compile(r'^(?:Else\s+If|If|While|Until)\s+flag\b(?!\s+(?:true|false)\b)',
                         re.IGNORECASE)

# `Set reference x = y` instead of `to`.  The head `Set` is real, so the head
# check passes it; the notation and variable blades do not look at it either.
# Only the '=' directly after the reference name is caught -- an
# '=' further along belongs to a comparison inside the source expression.
RE_SETREF_EQ = re.compile(r'^Set\s+reference\s+[A-Za-z_]\w*(?:\.[A-Za-z_$]\w*)*\s*=')


def check(text, heads):
    probs = []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        # a line may carry a trailing '## comment'
        i = line.find('##')
        if i >= 0:
            line = line[:i].strip()
        if not line:
            continue
        # Only braces in the LIVE part of the line count. A brace inside a
        # string literal is text -- `Do [name3].$add('OK message {Result=[x]}')`
        # is a generator writing a legitimate message line.
        bare = RE_STRING.sub("''", line)
        if line.startswith(CALC_COMMANDS) and RE_BRACE.search(bare):
            probs.append(
                f"line {n}: curly braces in the argument of a CALCULATION "
                f"command -- that is Omnis 7 syntax, the current compiler "
                f"rejects the line and stores it empty. Write the calculation "
                f"without braces")
        if RE_FLAGWORD.match(line):
            probs.append(
                f"line {n}: 'flag' after {line.split()[0]} is the KEYWORD for #F, "
                f"not a variable -- the command form is 'flag true' or "
                f"'flag false'. Omnis refuses this line, and one refused line "
                f"makes $methodtext.$assign refuse the whole body. If a "
                f"variable was meant, it may not be called 'flag'")
        if RE_SETREF_EQ.match(line):
            probs.append(
                f"line {n}: 'Set reference ... =' -- the command takes 'to', "
                f"not '='. Omnis refuses the line silently")
        head = re.split(r'[\s(]', line, 1)[0]
        if head not in heads:
            probs.append(f"line {n}: '{head}' is not an Omnis command head "
                         f"-- not in {TABLE_NAME}")
    return probs


def main():
    heads, entries, tablepath = load_heads()
    if heads is None:
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
    bad = 0
    for name, text in files:
        probs = check(text, heads)
        if probs:
            bad += 1
            print(f"FAIL {os.path.basename(name)}")
            for p in probs:
                print(f"     -> {p}")
        else:
            print(f"ok   {os.path.basename(name)}")
    print(f"\n{len(files)-bad}/{len(files)} clean (commands, {len(entries)} known)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
