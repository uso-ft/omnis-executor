#!/usr/bin/env python3
"""
Variable blade — verifies that every bare identifier used as a VARIABLE exists
in the target context's declared set.

Usage:  python3 check_variables.py [--vars <list.txt>] <script.txt> [more.txt ...]
        python3 check_variables.py -                  (read one script from stdin)

Default set: vars_executor_v12_types.txt (name TAB type), the parameters and
locals of Executor.$codes.Executor.$execute -- the closed set of CONTRACT.md
§1.2. The vessel does not have a set of its own: the method's $lvardefs are
copied into the injected vessel method, so the two are identical by
construction. Another target needs its own list, passed with --vars.

The typical catch: `iTools` handed to the vessel, which knows `tools` --
iTools is an instance variable of the CONSOLE and is not in the injected set.

HOW A VARIABLE IS TOLD APART FROM EVERYTHING ELSE
  A dotted chain whose head starts with `$` is notation      -> skipped
  A chain head followed by `(` is a function call            -> skipped
  `#D`, `#T`, `#F`, `#S1` ... are hash variables             -> skipped
  `kSomething` is a constant                                 -> skipped
  `kcursArrow`, `kerrNotFound`: a lower-case family the
  constants table uses -- a constant too                    -> skipped
  Text inside single quotes is a literal                     -> skipped
  The command head itself                                    -> skipped
  For commands whose argument is a CLASS or LIBRARY name
  (Close design, Save class, Open library, ...) the bare
  argument is a class name, not a variable                   -> skipped,
                                                                but `[expr]`
                                                                inside it is
                                                                still scanned
  What survives is a bare identifier at the head of a chain -- `list.$linecount`
  yields `list`, `cName` yields `cName`.  Those are variables and get checked.

SCOPE: written for INJECTED scripts (the vessel / $execute set).  It is not
meant for console object methods, which legitimately use things no script ever
sees: implicit $event parameters (pSystemKey, pEventCode ...), bare window
object names in field commands (efTargetPath ...), and free menu-command text.
Pointing it at those will produce noise; that is scope, not a defect.

TYPES
-----
The names carry fixed TYPES. Without them the blade would pass
`Calculate group as methodRef.$methodlines.$fullname` -- `group` is kItemref,
`$fullname` is a path string, and an item reference cannot be Calculated into.
The variable was picked by its NAME (it holds a group) rather than by its
type; names like classRef or list carry their type, `group` carries a concept.

Three rules, from the type column of the variable file:
  an item reference is filled with `Set reference`, never `Calculate`
  everything else is filled with `Calculate`, never `Set reference`
  a kRow is not asked list questions

The third rule: `Calculate row as ref3.$settingsSpec()` -- the method answers
with a LIST, `row` is a kRow, the assignment keeps LINE ONE in silence,
`row.$linecount` then says 1, and the count that follows is wrong and
plausible. No error, no warning, a small
believable number. Neither rule above can see it: the name IS in the set and
`Calculate` IS the right verb for a kRow.  What gives it away is the QUESTION
asked afterwards -- `$line`, `$linecount`, `$search(`, `$add(`, `$remove(`,
`$sendall(` are things one asks a list.

Evidence, not style: across the method files of the Executor library there
is not one `Calculate <reference variable> as`. Without a type column the
type rules are skipped, and the blade says so.
"""
import sys, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
# One file, not two: name TAB type. The names are the column in front of the
# tab, the types the column behind it. Two files that must agree is one more
# than necessary.
DEFAULT_VARS = 'vars_executor_v12_types.txt'

# commands whose argument is NOT an expression -- a class name, a library
# name, or free message text.  Only a bracketed [expr] inside such a line can
# hold a variable.
NOEXPR = (
    'Close design', 'Save class', 'Delete class', 'Rename class',
    'Open library', 'Create library', 'Close library',
    'Open window instance', 'Open form instance', 'Open menu instance',
    'Open toolbar instance', 'Install menu', 'Remove menu',
    'Start task', 'Close task',
    'OK message', 'Yes/No message', 'No/Yes message', 'Working message',
    'Prompt for input', 'Breakpoint', 'Send to trace log',
    # The argument is a CLASS PATH, `Task/$method`, not an expression:
    # `Load error handler Startup_Task/$handleError` names no variable.
    'Load error handler', 'Unload error handler',
)

# List questions.  Asked of a variable the types file calls a kRow, they mean
# the row was filled from something that answers with a list.  $colcount and
# $cols are deliberately NOT here: a row has columns.
RE_ROW_LISTQ = re.compile(
    r'\b([A-Za-z_]\w*)\.(\$line\b|\$linecount\b|\$search\(|\$add\(|'
    r'\$remove\(|\$sendall\(|\$merge\(|\$totc\()')

# Omnis external static objects: usable without any declaration
STATICS = {'FileOps', 'FontOps'}

# Library-level notation groups.  A chain head followed by one of these is a
# LIBRARY name (`Executor.$classes.Startup_Task`), never a variable -- no
# variable is ever followed by `.$classes`.  Class-level groups such as
# `$methods` or `$objs` are deliberately NOT listed: `methodRef.$methods` has
# a variable at its head.
LIB_GROUPS = {
    '$classes', '$codes', '$windows', '$reports', '$menus', '$toolbars',
    '$tasks', '$objects', '$files', '$searches', '$schemas', '$queries',
    '$tables', '$remoteforms', '$remotetasks', '$htmlcontrols', '$subwindows',
}

# words that are grammar, not identifiers, once the command head is stripped
KEYWORDS = {
    'as', 'to', 'from', 'step', 'Returns', 'by', 'in', 'at', 'for', 'of',
    'on', 'with', 'and', 'or', 'not', 'do', 'the',
}

# Omnis literals come in BOTH quote styles: 'text' with doubled inner quotes,
# and "text", which embeds a single quote without doubling. Masking only the
# single-quoted form would let the contents of a double-quoted string be read
# as code.
RE_STRING = re.compile(r"'[^']*'|\"[^\"]*\"")
RE_CHAIN = re.compile(r'(?<![\w.$#])([A-Za-z_]\w*)((?:\.[$]?\w+)*)')
RE_BRACKET = re.compile(r'\[([^\]]*)\]')
RE_CONST = re.compile(r'^(k[A-Z0-9]|ev[A-Z]|cmd[A-Z])')
# The lower-case constant families -- `kcursArrow`, `kerrNotFound`, `kmacOS`.
# A head of that shape whose prefix the constants table uses is a CONSTANT, and
# check_constants judges whether it exists. `keyCode` has the same shape, but
# `key` is no family of the table, so it is still read as a variable.
RE_FAMILY = re.compile(r'(k[a-z]+)[A-Z]\w*')
RE_LEADPARENS = re.compile(r'^\s*\([^)]*\)\s*')


def load_commands():
    """Command entries + head words, longest first, for prefix stripping."""
    for cand in (os.path.join(HERE, 'omnis_command_table.txt'),
                 'omnis_command_table.txt'):
        if os.path.isfile(cand):
            entries, heads = set(), set()
            with open(cand, encoding='utf-8', errors='replace') as fh:
                for raw in fh:
                    e = raw.rstrip('\n').strip()
                    if e:
                        entries.add(e)
                        heads.add(e.split()[0])
            return sorted(entries | heads, key=len, reverse=True)
    return []


CMDS = load_commands()


def load_families():
    """The lower-case prefixes the constants table uses: kcurs, kerr, kmac ..."""
    for cand in (os.path.join(HERE, 'omnis_constants_table.txt'),
                 'omnis_constants_table.txt'):
        if os.path.isfile(cand):
            out = set()
            with open(cand, encoding='utf-8', errors='replace') as fh:
                for raw in fh:
                    m = RE_FAMILY.fullmatch(raw.strip())
                    if m:
                        out.add(m.group(1))
            return out
    return set()


FAMILIES = load_families()


def strip_command(code):
    """Remove the leading command and any option parenthesis behind it.

    Applied twice: `Else If ...` is two table entries in a row, and stripping
    only `Else` would leave `If` looking like an identifier.
    """
    for _ in range(2):
        hit = False
        for c in CMDS:
            if code.startswith(c) and (len(code) == len(c)
                                       or not code[len(c)].isalnum()):
                code = RE_LEADPARENS.sub('', code[len(c):])
                hit = True
                break
        if not hit:
            break
        code = code.lstrip()
    return code


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


def load_vars(path):
    for cand in (path, os.path.join(HERE, path)):
        if os.path.isfile(cand):
            with open(cand, encoding='utf-8', errors='replace') as fh:
                # name TAB type, or a bare name -- both are read
                return {l.split('\t')[0].strip() for l in fh if l.strip()}, cand
    return None, None


def load_types(varfile):
    """name -> Omnis type, from <varfile stem>.types. Missing file: no rules."""
    if not varfile:
        return {}
    stem = os.path.splitext(varfile)[0]
    # varfile FIRST: when the names and the types live in one file, the file is
    # its own type source and the sibling search below would never find it.
    for cand in (varfile, stem + '.types', stem + '.types.txt', stem + '_types.txt',
                 os.path.join(HERE, os.path.basename(stem) + '.types'),
                 os.path.join(HERE, os.path.basename(stem) + '.types.txt'),
                 os.path.join(HERE, os.path.basename(stem) + '_types.txt')):
        if os.path.isfile(cand):
            out = {}
            for line in open(cand, encoding='utf-8', errors='replace'):
                if '\t' in line:
                    n, t = line.rstrip('\n').split('\t', 1)
                    out[n.strip()] = t.strip()
            return out
    return {}


# assignment to a BARE variable only -- `Calculate list.$line as 1` addresses a
# property of the list, not the variable itself, and is none of our business
RE_CALC_TO = re.compile(r'^Calculate\s+([A-Za-z_]\w*)\s+as\b')
RE_SETREF_TO = re.compile(r'^Set reference\s+([A-Za-z_]\w*)\s+to\b')


def candidates(code):
    """Yield bare identifiers used in a variable position."""
    out = []
    for m in RE_CHAIN.finditer(code):
        head = m.group(1)
        tail = m.group(2)
        if tail.split('.')[1:2] and tail.split('.')[1] in LIB_GROUPS:
            continue          # `Executor.$classes...` -- a library, not a variable
        after = code[m.end():m.end() + 1]
        # `con(` is a function; `iTools.$stripComments(` is a VARIABLE carrying
        # a notation chain -- the bracket belongs to the tail, not to the head.
        if after == '(' and not m.group(2):
            continue
        if RE_CONST.match(head):  # kConstant / evEvent / cmdCommand
            continue
        fam = RE_FAMILY.fullmatch(head)
        if fam and fam.group(1) in FAMILIES:   # kcursArrow / kerrNotFound
            continue
        if head in KEYWORDS:      # grammar word, not an identifier
            continue
        if head in STATICS:       # external static object, never declared
            continue
        out.append((head, m.start()))
    return out


def check(text, known, types=None):
    types = types or {}
    probs = []
    seen = set()
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        line = strip_trailing_comment(line)
        code = RE_STRING.sub("''", line)

        m = RE_CALC_TO.match(code)
        if m and types.get(m.group(1)) == 'kItemref':
            probs.append(
                f"line {n}: 'Calculate {m.group(1)} as ...' -- {m.group(1)} is "
                f"kItemref. An item reference is filled with 'Set reference', "
                f"never Calculate")
        m = RE_SETREF_TO.match(code)
        if m and m.group(1) in types and types[m.group(1)] != 'kItemref':
            probs.append(
                f"line {n}: 'Set reference {m.group(1)} to ...' -- {m.group(1)} "
                f"is {types[m.group(1)]}, not a reference variable")

        # a kRow asked a list question is a list that was received into a row
        for mm in RE_ROW_LISTQ.finditer(code):
            name = mm.group(1)
            if types.get(name) == 'kRow':
                probs.append(
                    f"line {n}: '{name}.{mm.group(2)}' -- {name} is a kRow, and "
                    f"{mm.group(2)} is a question for a LIST. Assigning a list "
                    f"to a row keeps line one in silence, and the count that "
                    f"follows is wrong and plausible")

        if any(code.startswith(c) for c in NOEXPR):
            # only the bracketed expressions inside such a line hold variables
            scan = ' '.join(RE_BRACKET.findall(code))
        else:
            scan = strip_command(code)

        for head, _ in candidates(scan):
            if head in known:
                continue
            key = (n, head)
            if key in seen:
                continue
            seen.add(key)
            probs.append(
                f"line {n}: '{head}' is not in the target variable set "
                f"-- unknown variables make the method text UNASSIGNABLE")
    return probs


def main():
    args = sys.argv[1:]
    varfile = DEFAULT_VARS
    if args and args[0] == '--vars':
        if len(args) < 2:
            print("--vars needs a file")
            return 2
        varfile, args = args[1], args[2:]

    known, used = load_vars(varfile)
    if known is None:
        print(f"BLADE UNUSABLE: variable list '{varfile}' not found")
        return 2
    types = load_types(used)
    if not types:
        print("NOTE no .types file beside the variable list -- the "
              "Calculate/Set reference type rules were NOT run")

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
        probs = check(text, known, types)
        if probs:
            bad += 1
            print(f"FAIL {os.path.basename(name)}")
            for p in probs:
                print(f"     -> {p}")
        else:
            print(f"ok   {os.path.basename(name)}")
    print(f"\n{len(files)-bad}/{len(files)} clean (variables, "
          f"{len(known)} declared in {os.path.basename(used)})")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
