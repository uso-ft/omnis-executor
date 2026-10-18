#!/usr/bin/env python3
"""
Emission-variable blade -- does the generated body use names the TARGET method
actually has?

Usage:  python3 check_emitted_vars.py [--export <root>] <script.txt> [...]
        python3 check_emitted_vars.py --show <script.txt>

WHY THIS EXISTS.  check_emitted reconstructs the body a script generates and
runs check_notation and check_commands over it.  Its own header says why it
stops there: "it does not know which method the body is destined for, so
check_define and the variable blades are NOT run: their questions need the
target's variable set, which lives in the export and not here."

WHAT IT DOES NOT CATCH, said plainly, because a blade trusted beyond its reach
is worse than none:

  - A declaration that is ATTEMPTED and silently REJECTED.
    $ivardefs.$add('iList',kList,kSimplechar,0): kSimplechar is the subtype of
    kCharacter and a kList takes none, so iList is never created and every
    emitted line using it is refused. This blade reads the $add and believes
    it. Only the run knows; the counter-measure is to read the names BACK
    after the declaration and compare them.
  - A body built by SPLICING text read from another method. That is not an
    emission chain and cannot be reconstructed from the script.

WHAT IT DOES CATCH: a generated line that uses a name nobody declares
anywhere -- neither the export nor the script itself. Omnis refuses such a
line silently, one at a time, and the symptom looks like anything but the
cause.

WHAT IT CHECKS.  For every name the emitted body uses as a variable, the name
must be declared on the target method -- either already in the export, or added
by the script itself before the emission.

TWO EMISSION FORMS are recognised:

  1  con-chain     Calculate text2 as con(text2,'…',kCr)   ending in
                   $methodtext.$assign(text2)          (check_emitted's form)
  2  source list   Do list.$add('…')  …  group.$add(text)  in a loop


THE TARGET is taken from the last $methods.$findname('$name') or
$methods.$add('$name') before the emission, together with the class path.

LIMITS, stated rather than hidden:

  - Without --export only the names the script adds itself are known, so a
    method that already has locals reads as if it had none.  The blade says so
    and checks nothing rather than crying wolf.
  - A name that appears only inside a con() with a variable piece cannot be
    seen, exactly as in check_emitted.
  - Identification of "this token is a variable" is conservative: anything
    followed by '(' is taken for a function, k-constants and $-notation and
    #-variables are skipped, and every command word from the command table is
    removed.  A name that slips through is reported; a name wrongly reported is
    worse than one missed, so the doubtful cases are listed separately as
    UNSURE and do not fail the run.
"""
import sys, os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))

RE_EMIT   = re.compile(r"^Calculate\s+(\w+)\s+as\s+con\(\s*\1\s*,(.*)\)\s*$")
RE_ASSIGN = re.compile(r"\$methodtext\.\$assign\(\s*(\w+)\s*\)")
RE_LISTADD = re.compile(r"^Do\s+(\w+)\.\$add\(\s*(.*?)\s*\)\s*$")
# form 3. A single method LINE rewritten in place:
#     Do <ref>.$text.$assign('<code>')            direct literal
#     Calculate textN as '<code>' … Do <ref>.$text.$assign(textN)
# The cheapest write there is (lore 10.10).
RE_LINEASSIGN = re.compile(r"\$text\.\$assign\(\s*(.+?)\s*\)\s*(?:Returns\s+\w+\s*)?$")
RE_CALCLIT = re.compile(r"^Calculate\s+(\w+)\s+as\s+(.*)$")
RE_GROUPADD = re.compile(r"\bgroup\.\$add\(\s*(\w+)\s*\)")
RE_PIECE  = re.compile(r"'((?:[^']|'')*)'|\"((?:[^\"]|\"\")*)\"|chr\((\d+)\)")
# A literal INSIDE an emitted literal is written with doubled quotes --
# 'Do out.$add(''verdict'',''ok'')'. Ending the literal at the first quote of
# the pair would let 'verdict' and 'ok' fall OUT of the string, and every word
# inside them would read as an undeclared variable.
def _cut_comment(s):
    """the line up to the first '##' that is not inside a string literal"""
    q = ''
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            if c == q:
                if i + 1 < len(s) and s[i + 1] == q:
                    i += 2
                    continue
                q = ''
        elif c in ("'", '"'):
            q = c
        elif c == '#' and i + 1 < len(s) and s[i + 1] == '#':
            return s[:i]
        i += 1
    return s


def _unesc(s):
    return s.replace("''", "'").replace('\"\"', '\"')

# Every notation form a target is written in:
#  - a method is addressed `$methods.$findname('$name')`, `$methods.$add(...)`
#    or `$methods.//$name//`, the escape form every jump line carries;
#  - a class is addressed `Lib.$classes.Class`, the library-first form.
# A form not recognised resolves the target to None.None, and every class
# variable of the target would be reported as invented -- loud and wrong on a
# correct script.
RE_TARGETM = re.compile(r"\$methods\.(?:\$(?:findname|add)\(\s*'(\$?\w+)'\s*\)"
                        r"|//(\$?\w+)//)")
RE_TARGETC = re.compile(r"(?:\$root\.\$libs\.)?\b(\w+)\.\$(?:classes|codes|windows|"
                        r"reports|menus|toolbars|tasks|objects)\.(\w+)")
RE_VARADD = re.compile(r"\$lvardefs\.\$add\(\s*'(\w+)'")
# the house form is two steps -- Set reference group to <m>.$lvardefs, then
# Do group.$add('name',...). Reading only the one-liner reported nine added
# names as none.
RE_VARGRP = re.compile(r"Set\s+reference\s+(\w+)\s+to\s+\w+\.\$(?:lvardefs|ivardefs|cvardefs|tvardefs)")
RE_VARANY = re.compile(r"\$(?:lvardefs|ivardefs|cvardefs|tvardefs)\.\$add\(\s*'(\w+)'")
# A script can also introduce a name by RENAMING an existing definition --
# pStopAt becomes pStopAt_opt, and the body line that used it is rewritten.
# The new name is not in the export. Any $name.$assign is counted, class
# renames included: it can only widen the known set, so it costs a miss and
# never an alarm.
RE_VARRENAME = re.compile(r"\$name\.\$assign\(\s*'(\w+)'\s*\)")

def added_names(text):
    out = (set(RE_VARADD.findall(text)) | set(RE_VARANY.findall(text))
           | set(RE_VARRENAME.findall(text)))
    for g in set(RE_VARGRP.findall(text)):
        out |= set(re.findall(r"\b" + re.escape(g) + r"\.\$add\(\s*'(\w+)'", text))
    return out

def commands():
    p = os.path.join(HERE, 'omnis_command_table.txt')
    if not os.path.exists(p):
        return set()
    out = set()
    for l in open(p, encoding='utf-8', errors='replace'):
        for w in l.strip().split():
            if w.isalpha():
                out.add(w.lower())
    return out

def command_names():
    """Whole command names, lower case: `open library`, `close design` ..."""
    p = os.path.join(HERE, 'omnis_command_table.txt')
    if not os.path.exists(p):
        return set()
    return {l.strip().lower() for l in open(p, encoding='utf-8', errors='replace')
            if l.strip()}


def function_groups():
    """`FileOps`, `OJSON` ... from notation_vocab.json (build_notation_vocab.py)."""
    try:
        import json
        v = json.load(open(os.path.join(HERE, 'notation_vocab.json'), encoding='utf-8'))
        return set(v.get('function_groups', []))
    except Exception:
        return set()


RE_OPTIONS = re.compile(r'^([A-Za-z][A-Za-z ]*?)\s*\(([A-Za-z ,]*)\)')
CMD_NAMES = command_names()
FUNC_GROUPS = function_groups()


def pieces(body):
    """the literal text of one emission line, variables dropped"""
    out = []
    for m in RE_PIECE.finditer(body):
        if m.group(3):
            out.append(chr(int(m.group(3))))
        else:
            out.append(_unesc(m.group(1) if m.group(1) is not None else m.group(2)))
    return ''.join(out)

def emitted_lines(text):
    """reconstruct the generated body, both forms"""
    lines = text.split('\n')
    out = []
    # form 1: con-chain into $methodtext.$assign
    targets = set(RE_ASSIGN.findall(text))
    for l in lines:
        m = RE_EMIT.match(l.strip())
        if m and m.group(1) in targets:
            out.extend(pieces(m.group(2)).split('\n'))
    # form 2: a source list fed line by line into a method's $methodlines
    # Only a list whose value actually reaches group.$add counts. The first
    # cut took every list indexed with .[n]. and swallowed the blade's own
    # verification list -- nine names that were never emitted at all.
    fed = set(RE_GROUPADD.findall(text))
    listnames = set()
    for l in lines:
        s = l.strip()
        m = re.match(r"Calculate\s+(\w+)\s+as\s+.*?\b(\w+)\.\[n\]\.\w+", s)
        if m and m.group(1) in fed:
            listnames.add(m.group(2))
    for l in lines:
        m = RE_LISTADD.match(l.strip())
        if m and m.group(1) in listnames:
            arg = m.group(2)
            if arg.startswith('$cols'):
                continue
            out.append(pieces(arg))
    # form 3: one line at a time into <ref>.$text
    fed3 = set()
    for l in lines:
        m = RE_LINEASSIGN.search(l.strip())
        if not m:
            continue
        arg = m.group(1)
        if re.match(r"^\w+$", arg):
            fed3.add(arg)               # a variable -- collect its literals below
        else:
            out.append(pieces(arg))     # a literal handed in directly
    if fed3:
        for l in lines:
            m = RE_CALCLIT.match(l.strip())
            if m and m.group(1) in fed3:
                out.append(pieces(m.group(2)))
    # form 4: BLOCK REPLACEMENT -- kCr-bordered NEW blocks chained into a
    # variable that reaches `replaceall(T,old,new)`, T being the variable
    # handed to $methodtext.$assign. Chains of the same variable that never
    # reach a replaceall (the read-back verification) are ignored.
    re_rep = re.compile(r"^Calculate\s+(\w+)\s+as\s+replaceall\(\s*\1\s*,\s*(\w+)\s*,\s*(\w+)\s*\)")
    swaps = {m.group(3) for m in (re_rep.match(l.strip()) for l in lines)
             if m and m.group(1) in targets}
    cur = {}
    for l in lines:
        st = l.strip()
        m = re.match(r"^Calculate\s+(\w+)\s+as\s+''\s*$", st)
        if m and m.group(1) in swaps:
            cur[m.group(1)] = []
            continue
        m = RE_EMIT.match(st)
        if m and m.group(1) in cur:
            cur[m.group(1)].append(m.group(2))
            continue
        m = re_rep.match(st)
        if m and m.group(3) in cur:
            for body in cur.pop(m.group(3)):
                out.append(pieces(body))
    return [o for o in out if o.strip()]

def target_of(text):
    # findall over an alternation yields a tuple per match; take whichever
    # group fired.
    ms = [a or b for a, b in RE_TARGETM.findall(text)]
    cs = RE_TARGETC.findall(text)
    meth = ms[0] if ms else None
    cls = cs[0][1] if cs else None
    lib = cs[0][0] if cs else None
    return lib, cls, meth

def targets_all(text):
    """every class and every method the script addresses.

    A script may rewrite lines in SEVERAL methods, in several classes.
    Reading only the FIRST target and checking every emitted line against it
    turns a correct script into a page of false alarms, which is the one
    thing this blade must not do. The cross product of the
    classes and the methods found is used instead: it can only WIDEN the known
    set, so it costs a miss and never an alarm -- the same trade the blade makes
    for list columns.
    """
    ms = [a or b for a, b in RE_TARGETM.findall(text)]
    cs = RE_TARGETC.findall(text)
    return cs, ms

def class_vars(root, lib, cls):
    """the class's OWN variables -- every method of the class sees them.

    A method checked against its locals alone would report every instance
    or class variable it uses as invented. The method entry in methods.json
    cannot carry these; they live in class.json beside it.
    """
    names = set()
    if not (root and lib and cls):
        return names
    for cand in (os.path.join(root, lib, cls, 'class.json'),
                 os.path.join(root, cls, 'class.json')):
        if os.path.exists(cand):
            try:
                d = json.load(open(cand, encoding='utf-8'))
            except Exception:
                return names
            for key in ('ivardefs', 'cvardefs'):
                for v in d.get(key, []) or []:
                    if v.get('name'):
                        names.add(v['name'])
            return names
    return names


def declared_in_export(root, lib, cls, meth):
    """names on the target method, from methods.json"""
    if not (root and lib and cls and meth):
        return None
    for cand in (os.path.join(root, lib, cls, 'methods.json'),
                 os.path.join(root, cls, 'methods.json')):
        if os.path.exists(cand):
            try:
                d = json.load(open(cand, encoding='utf-8'))
            except Exception:
                return None
            ms = d if isinstance(d, list) else d.get('methods', [])
            for e in ms:
                if e.get('name') == meth:
                    names = set()
                    for key in ('lvardefs', 'pvardefs', 'ivardefs', 'cvardefs'):
                        for v in e.get(key, []) or []:
                            names.add(v.get('name'))
                    return names
            # A method of a window OBJECT (efTargetPath.$event)
            # lives in objs/<name>/methods.json, not beside the class's own.
            # Every object method of that name is taken -- it can only widen.
            base = os.path.dirname(cand)
            objdir = os.path.join(base, 'objs')
            found = None
            if os.path.isdir(objdir):
                for o in sorted(os.listdir(objdir)):
                    mp = os.path.join(objdir, o, 'methods.json')
                    if not os.path.exists(mp):
                        continue
                    try:
                        od = json.load(open(mp, encoding='utf-8'))
                    except Exception:
                        continue
                    for e in od:
                        if e.get('name') == meth:
                            found = found or set()
                            for key in ('lvardefs', 'pvardefs'):
                                for v in e.get(key, []) or []:
                                    found.add(v.get('name'))
            if found is not None:
                return found
            # A method the script CREATES is not in the export. That is not
            # "it has no variables" -- it is "nothing to compare against", and
            # the two must not print the same.
            return None
    return None

def used_names(body, cmds):
    """tokens in the emitted body that look like variables"""
    seen, unsure = set(), set()
    for line in body:
        s = line.strip()
        if s.startswith('#'):
            continue
        s = re.sub(r"'[^']*'", " ", s)
        s = re.sub(r'"[^"]*"', " ", s)
        # An inline ## comment on a GENERATED line is not code: cut at the
        # first ## that stands outside a literal, the way Omnis reads it.
        s = _cut_comment(s)
        # Shapes that look like names and are not variables:
        #  - 'On evClick' / 'On evMouseEnter': the EVENT name.
        #  - the prose inside a message command's { } braces: No, Yes, s, the.
        #    Names interpolated with [ ] inside it are kept, they are real.
        #  - k32bitint: a DIGIT may follow the k of a constant (^k[A-Za-z0-9]).
        #  - the OPTIONS of a command, `Open library (Do not close others,Do
        #    not open startup task)`: words, not variables. Only a bracket of
        #    plain words directly after a whole command name is dropped.
        #  - a static function group, `FileOps.$filelist(...)`: FileOps is no
        #    variable. The groups come from the help, via notation_vocab.json.
        mo = RE_OPTIONS.match(s)
        if mo and mo.group(1).strip().lower() in CMD_NAMES:
            s = mo.group(1) + ' ' + s[mo.end():]
        for g in FUNC_GROUPS:
            s = re.sub(r'\b' + re.escape(g) + r'\.(?=\$)', ' ', s)
        if re.match(r'^On\s+ev\w+', s):
            s = re.sub(r'^On\s+ev\w+', ' ', s)
        s = re.sub(r'^(No/Yes|Yes/No|OK|Yes/No/Cancel)\s+message\b[^{]*', ' ', s)
        s = re.sub(r'\{[^{}]*\}', lambda m: ' '.join(
            re.findall(r'\[([^\]]*)\]', m.group(0))) or ' ', s)
        s = re.sub(r"\$\w+", " ", s)          # notation
        # A LIST COLUMN is not a variable: pDiff.clsName is a column of pDiff,
        # not a name the method must declare, and the same goes for row.field.
        # Anything directly after a dot is dropped: it can only cost a miss,
        # never a false alarm, and a name wrongly reported is the worse of
        # the two.
        s = re.sub(r"\.\w+", " ", s)
        s = re.sub(r"#\w+", " ", s)           # #F, #S1, #CT
        first = s.split()[0].lower() if s.split() else ''
        for m in re.finditer(r"\b([A-Za-z_]\w*)\b\s*(\(?)", s):
            tok, paren = m.group(1), m.group(2)
            low = tok.lower()
            if paren == '(':
                continue                      # a function, check_notation's job
            if re.match(r"^k[A-Za-z0-9]", tok) and tok not in ('k',):
                continue                      # constant
            if low in cmds or low in ('do', 'if', 'else', 'end', 'for', 'to',
                                      'from', 'step', 'as', 'quit', 'method',
                                      'calculate', 'set', 'reference', 'while',
                                      'returns', 'not', 'and', 'or', 'class',
                                      'design', 'save', 'close'):
                continue
            if tok in ('C1', 'C2', 'C3', 'C4', 'C5'):
                continue
            if first in ('send', 'ok', 'yes', 'no'):
                unsure.add(tok)
            else:
                seen.add(tok)
    return seen, unsure

def main():
    args = sys.argv[1:]
    export = None
    show = False
    if '--export' in args:
        i = args.index('--export')
        export = args[i + 1]
        del args[i:i + 2]
    if '--show' in args:
        show = True
        args.remove('--show')
    if not args:
        print(__doc__)
        return 2
    cmds = commands()
    total = ok = 0
    for path in args:
        text = open(path, encoding='utf-8', errors='replace').read()
        name = os.path.basename(path)
        body = emitted_lines(text)
        if not body:
            print(f"..   {name}: no emitted body found -- nothing generated, "
                  f"or assembled in a form this blade does not know")
            total += 1
            ok += 1
            continue
        if show:
            print(f"--- {name}: {len(body)} emitted line(s)")
            for b in body:
                print("   ", b)
        lib, cls, meth = target_of(text)
        added = added_names(text)
        allc, allm = targets_all(text)
        fromexp = None
        for (l2, c2) in allc:
            added = added | class_vars(export, l2, c2)
            for m2 in allm:
                got = declared_in_export(export, l2, c2, m2)
                if got is not None:
                    fromexp = (fromexp or set()) | got
        if len(allc) > 1 or len(allm) > 1:
            print(f"     .. several targets, checked against the union: "
                  f"{' '.join(sorted({c for _, c in allc}))} / "
                  f"{' '.join(sorted(set(allm)))}")
        total += 1
        if fromexp is None and not added:
            print(f"..   {name}: target {lib}.{cls}.{meth} -- not in the export "
                  f"and the script adds no variables either. Nothing to compare "
                  f"against. Not checked.")
            ok += 1
            continue
        if fromexp is None:
            # A method the script CREATES has exactly the variables the script
            # gives it, so the added set IS the complete set and the check is
            # sharper here than anywhere else.
            known = added
            print(f"     .. {cls}.{meth} is created by this script; checked "
                  f"against the {len(added)} name(s) it declares")
        else:
            known = fromexp | added
        seen, unsure = used_names(body, cmds)
        missing = sorted(n for n in seen if n not in known)
        if missing:
            print(f"FAIL {name}: emitted body targets {cls}.{meth}")
            for n in missing:
                print(f"     -> '{n}' is used by the generated code but is not a "
                      f"variable of {meth}, and the script does not add it. "
                      f"Omnis refuses such a line silently, one at a time")
            print(f"     .. {meth} has: {' '.join(sorted(known)) or '(none)'}")
        else:
            ok += 1
            print(f"ok   {name}: {len(body)} emitted line(s), every name known to "
                  f"{cls}.{meth}")
        if unsure:
            print(f"     .. UNSURE, not counted: {' '.join(sorted(unsure))}")
    print(f"\n{ok}/{total} clean (emitted variables)")
    return 0 if ok == total else 1

if __name__ == '__main__':
    sys.exit(main())
