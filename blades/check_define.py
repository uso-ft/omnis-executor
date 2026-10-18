#!/usr/bin/env python3
"""
Define blade — checks that every column named in `$define(...)` exists as a
declared variable.

Usage:  python3 check_define.py [--vars <list.txt>] <script.txt> [more.txt ...]

The mistake it catches:

    Do out.$define(libName,clsName,moddate,bytes)

`$define` takes VARIABLES and borrows their names AND types.  If they are not
declared, the line does not compile.  What makes it dangerous is the aftermath:
`$add` on an undefined list still appears to work, the method returns rows, and
only a column-by-column look reveals that the data went nowhere.

TWO CASES, both checked:

  GENERATED — the `$define` sits inside a string being assembled into a method
    body.  Its columns must appear among the `$lvardefs.$add('X',...)`,
    `$ivardefs.$add` or `$cvardefs.$add` calls of the SAME script, because that
    is where the target method's variables are created.

  DIRECT — the `$define` is an operative line of the script itself.  Its
    columns must be in the target variable set (vars_executor_v12_types.txt,
    name TAB type, the same file check_variables reads).

`$define()` with no arguments is the deliberate "clear the columns" form and is
never reported.

SCOPE, same as the variable blade: the DIRECT case judges against the injected
script's variable set, so pointing this blade at the library's own .omh files
produces noise -- each method there has its own locals, which this blade cannot
know.  Measured on the Executor library: 12 of 232 methods report, all of them
that kind.  The GENERATED case has no such limit and is the one the blade was
built for.

NOT checked: `$cols.$add('name',type,...)`, which takes the column name as a
STRING and needs no variable at all.  That is the way to widen an existing list.
"""
import sys, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VARS = 'vars_executor_v12_types.txt'

# A declaration is `$lvardefs.$add('X',...)` -- or the indirection the
# Executor itself uses: the group path is put in a variable (`#S1`, `text3`)
# and the call reads `[text3].$add('X',...)`. Both forms declare.
RE_DECL = re.compile(
    r"(?:\$(?:lvardefs|ivardefs|cvardefs|tvardefs)\.\$add\s*\(\s*'([^']+)'"
    r"|\[[^\]]+\]\.\$add\s*\(\s*'([^']+)'\s*,\s*k)")
# Omnis literals come in BOTH quote styles: 'text' with doubled inner quotes,
# and "text", which embeds a single quote without doubling. Masking only the
# single-quoted form would let the contents of a double-quoted string be read
# as code.
RE_STRING = re.compile(r"'[^']*'|\"[^\"]*\"")


def load_types(varfile):
    """name -> Omnis type: the variable file itself when it carries name TAB
    type, else a sibling <stem>.types / _types.txt."""
    if not varfile:
        return {}
    stem = os.path.splitext(varfile)[0]
    for cand in (varfile, os.path.join(HERE, varfile), stem + '.types', stem + '.types.txt', stem + '_types.txt',
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


def load_vars(path):
    for cand in (path, os.path.join(HERE, path)):
        if os.path.isfile(cand):
            with open(cand, encoding='utf-8', errors='replace') as fh:
                # name TAB type, or a bare name -- both are read
                return {l.split('\t')[0].strip() for l in fh if l.strip()}
    return set()


def call_body(line, open_paren):
    depth, inq = 0, False
    for j in range(open_paren, len(line)):
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
                return line[open_paren + 1:j]
    return None


def in_string(line, idx):
    """Is position idx inside a single-quoted literal?"""
    inq = False
    for i, ch in enumerate(line):
        if i >= idx:
            return inq
        if ch == "'":
            inq = not inq
    return inq


# --- reference columns -------------------------------------------------------
# A reference stored in a LIST CELL needs () to reach the referenced object
# rather than the cell: `list.refCol().$name` is the object, `list.refCol.$name`
# is the column, and it answers with the COLUMN NAME -- every row then reports
# the column name instead of the object's.
#
# The test goes by TYPE, never by name. A name ending in Ref is a habit; the
# type is a fact, and it is readable from the script:
#   list.$define(a,b,c)          borrows names AND types from real variables
#   list.$cols.$add('n',kItemref) states the type outright
#   [path].$add('n',kItemref)    declares the variable a $define will use
RE_COLADD = re.compile(r"\$cols\.\$add\s*\(\s*'([^']+)'\s*,\s*(k\w+)")
RE_DECL_TYPED = re.compile(
    r"\$(?:lvardefs|ivardefs|cvardefs|tvardefs)\.\$add\s*\(\s*'([^']+)'\s*,\s*(k\w+)"
    r"|\[[^\]]+\]\.\$add\s*\(\s*'([^']+)'\s*,\s*(k\w+)")
RE_CELL = re.compile(r"(?<![\w$.])(\w+)\.(\w+)\.\$")


def reference_columns(text, types):
    """list name -> set of columns that hold an item reference."""
    vartype = dict(types)
    for m in RE_DECL_TYPED.finditer(text):
        name = m.group(1) or m.group(3)
        kind = m.group(2) or m.group(4)
        vartype[name] = kind
    out = {}
    for m in re.finditer(r"(?<![\w$.])(\w+)\.\$define\s*\(([^)]*)\)", text):
        cols = [c.strip() for c in m.group(2).split(',') if c.strip()]
        for c in cols:
            if vartype.get(c) == 'kItemref':
                out.setdefault(m.group(1), set()).add(c)
    for m in re.finditer(r"(?<![\w$.])(\w+)\.\$cols\.\$add\s*\(\s*'([^']+)'\s*,\s*(k\w+)", text):
        if m.group(3) == 'kItemref':
            out.setdefault(m.group(1), set()).add(m.group(2))
    return out


# --- order: locals before the text that uses them ---------------------------
# A method text naming a variable that does not exist yet is REFUSED by Omnis:
# $methodtext.$assign comes back with NO and the method stays as it was. So a
# generator has to create the locals BEFORE it writes the body. Done the
# other way round, the fix silently does nothing.
RE_VARDEF_ADD = re.compile(
    r"(?:\$(?:lvardefs|ivardefs|cvardefs|tvardefs)|\[[^\]]+\])"
    r"\.\$add\s*\(\s*'([^']+)'\s*,\s*k")
RE_BODY_WRITE = re.compile(
    r"\.\$add\s*\(\s*(?:'|con\()|\$methodtext\.\$assign\s*\(")
RE_LVARDEFS_PATH = re.compile(r"(\w+)\s+as\s+\w+\.\$lvardefs\.\$fullname")
RE_LINES_PATH = re.compile(r"(\w+)\s+as\s+\w+\.\$methodlines\.\$fullname")


def declaration_order(text):
    """Report a body written before the locals it may use.

    Only the two paths a generator actually uses are followed: the variable
    holding the $lvardefs path and the one holding the $methodlines path. When
    the first line writing through the METHODLINES path comes before the first
    line adding through the LVARDEFS path, the body is being written into a
    method whose locals do not exist yet.
    """
    probs = []
    lines = text.split('\n')
    lvar_var, line_var = None, None
    first_decl, first_body = None, None
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if line.startswith('#'):
            continue
        m = RE_LVARDEFS_PATH.search(line)
        if m:
            lvar_var = m.group(1)
        m = RE_LINES_PATH.search(line)
        if m:
            line_var = m.group(1)
        if lvar_var and line.startswith(f'Do [{lvar_var}]') and first_decl is None:
            if RE_VARDEF_ADD.search(line):
                first_decl = n
        if line_var and line.startswith(f'Do [{line_var}]') and first_body is None:
            first_body = n
        if '$methodtext.$assign(' in line and first_body is None:
            if "'#'" not in line:
                first_body = n
    if first_decl and first_body and first_body < first_decl:
        probs.append(
            f"line {first_body}: the method body is written before the locals "
            f"are declared (first declaration on line {first_decl}). Omnis "
            f"refuses a method text naming an unknown variable -- locals "
            f"first, body second")
    return probs


def check(text, known, types=None):
    probs = []
    probs.extend(declaration_order(text))
    declared = {g for m in RE_DECL.findall(text) for g in m if g}
    refcols = reference_columns(text, types or {})
    # Only a script that REMOVES and re-adds the method builds it from nothing;
    # there every variable must come from the script itself. A script that only
    # MODIFIES an existing method cannot be judged - the target may already
    # carry variables this blade never sees.
    fresh = ('$methods.$remove(' in text) and ('$methods.$add(' in text)

    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if line.startswith('#'):
            continue

        # A probe has to be able to write the wrong form on purpose, otherwise
        # no rule can ever be measured. '## MEASURED' exempts a line from THIS
        # rule only, and the exemptions are listed as notes so they stay
        # visible. Nothing else is waved through.
        measured = 'MEASURED' in raw
        for m in RE_CELL.finditer(line):
            lst, col = m.group(1), m.group(2)
            if col not in refcols.get(lst, ()):
                continue
            if measured:
                probs.append(
                    f"NOTE line {n}: '{lst}.{col}.$...' without brackets, "
                    f"marked MEASURED -- exempt from the reference column rule")
                continue
            if line[m.end() - 1:m.end() + 1] == '.$' and '()' in line[m.start():m.end()]:
                continue
            probs.append(
                f"line {n}: '{lst}.{col}.$...' reaches the list CELL, not the "
                f"reference in it -- {col} is kItemref, so write "
                f"'{lst}.{col}().$...'. Without the brackets $name answers with "
                f"the column name")

        for m in re.finditer(r'\$define\s*\(', line):
            body = call_body(line, line.index('(', m.end() - 1))
            if body is None or not body.strip():
                continue                      # $define() clears - deliberate
            cols = [c.strip() for c in body.split(',') if c.strip()]
            generated = in_string(line, m.start())
            for c in cols:
                if not re.fullmatch(r'[A-Za-z_]\w*', c):
                    continue                  # not a plain name, skip
                if generated:
                    if c in declared:
                        continue
                    if fresh:
                        probs.append(
                            f"line {n}: generated $define names column '{c}', but "
                            f"no $lvardefs.$add('{c}',...) in this script -- the "
                            f"line will NOT compile and the list stays undefined")
                    else:
                        probs.append(
                            f"NOTE line {n}: $define names column '{c}' and this "
                            f"script does not declare it. Fine IF the target "
                            f"method already has it -- the blade cannot see that")
                else:
                    if c not in known:
                        probs.append(
                            f"line {n}: $define names column '{c}', which is not "
                            f"in the target variable set")
    return probs


RE_COLADD = re.compile(
    r"\$cols\.\$add\(\s*'([^']*)'\s*,\s*(k\w+)\s*,\s*(''|\"\"|k\w+)?")
# Types that REFUSE an empty subtype: the column is not created and every later
# `list.<name>` raises 25207 "Unrecognized variable name". Measured:
# `$cols.$add('pt',kInteger,'',0)` raised on every later line and, far worse,
# left a summary line that read like a clean result because the loop never
# ran. kBoolean and kItemref DO accept '', which is why nothing looks wrong
# when they stand beside it.
# Only these two are listed, because only these two are measured. A blade that
# guesses the rest would fail correct code.
SUBTYPE_REQUIRED = {'kInteger': 'k32bitint', 'kNumber': 'kFloatdp'}


def col_subtypes(text):
    """Report a $cols.$add whose type needs a subtype and was given none."""
    probs = []
    for i, line in enumerate(text.split('\n'), 1):
        if line.lstrip().startswith('#'):
            continue
        for m in RE_COLADD.finditer(line):
            name, typ, sub = m.group(1), m.group(2), m.group(3)
            if typ in SUBTYPE_REQUIRED and sub in ("''", '""', None):
                probs.append(
                    f"line {i}: $cols.$add('{name}',{typ},'',...) has an EMPTY "
                    f"subtype -- {typ} needs one ({SUBTYPE_REQUIRED[typ]}). "
                    f"The column is not created and every later "
                    f"list.{name} raises 25207")
    return probs


def main():
    args = sys.argv[1:]
    varfile = DEFAULT_VARS
    if args and args[0] == '--vars':
        varfile, args = args[1], args[2:]
    known = load_vars(varfile)
    types = load_types(varfile)
    # A names-only list passed with --vars carries no types; a name TAB type
    # file is both lists at once.
    if not known and types:
        known = set(types)
    # No set at all: SKIP the direct rule and say so. With an EMPTY set every
    # column of every direct $define would read as undeclared -- a clean script
    # failing on correct names, and the report blaming the script.
    if not known:
        print(f"NOTE no variable list ({os.path.basename(varfile)} or its "
              f"_types.txt) -- the DIRECT $define rule was NOT run. The "
              f"GENERATED case is unaffected and still runs.")
    if not types:
        print("NOTE no .types file beside the variable list -- the reference "
              "column rule was NOT run")

    if not args or args[0] == '-':
        files = [('<stdin>', sys.stdin.read())]
    else:
        files = [(a, open(a, encoding='utf-8', errors='replace').read())
                 for a in args if os.path.isfile(a)]
    bad = 0
    for name, text in files:
        probs = check(text, known, types) + col_subtypes(text)
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
    print(f"\n{len(files)-bad}/{len(files)} clean (define columns)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
