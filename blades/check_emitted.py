#!/usr/bin/env python3
"""
Emission blade -- runs the other blades over the method body a script GENERATES.

Usage:  python3 check_emitted.py [--export <root>] <script.txt> [more.txt ...]
        python3 check_emitted.py --show <script.txt>     print the reconstruction

WHY THIS EXISTS.  Every other blade reads the SCRIPT.  None of them reads the
text the script assembles in `con(text2,'…')` chains and hands to
`$methodtext.$assign`.  That text is checked by Omnis alone, at assign time,
and its whole answer is `NO` -- no line named, no reason given.

A script can be CLEAN while the body it generates is refused:

  `If flag`     -- `flag` is the keyword for #F, and check_commands knows it
  `val(seg)`    -- `val()` is not an Omnis function, and check_notation says
                   so plainly when it is shown the line

Both sit inside string literals, so no blade reading the script sees them.
This one shows them the lines.

HOW.  The emission lines of a generator look like

    Calculate text2 as con(text2,'If isclear(pPath)',kCr)
    Calculate text2 as con(text2,'Quit method con(',chr(91),'edit',chr(93),' …')

so the literals are concatenated, `chr(nn)` is turned back into its character,
and everything else -- variables, kCr, function calls -- is dropped.  The
result is the method body as Omnis will see it, and the other blades run over
it.

WHAT IT CANNOT DO, said plainly so nobody trusts it too far:

  - a `con()` carrying a VARIABLE cannot be reconstructed; that piece is simply
    missing from the line, and the line may then read as nonsense.  Such lines
    are LISTED at the end rather than hidden, so the reader can judge them.
  - a body assembled in more than one variable, or across several methods, is
    missed entirely.
  - it does not know which method the body is destined for, so `check_define`
    and the variable blades are NOT run: their questions need the target's
    variable set, which lives in the export and not here.

Only `check_notation` and `check_commands` are run, and only they -- those two
answer from the text alone.  Pass `--export` or every method of the library
reads as invented.

Two more forms are read: the BLOCK REPLACEMENT (kCr-bordered NEW blocks
swapped in with replaceall, one $methodtext.$assign), and the single method
LINE written through $text.$assign. And with --export a CALLS check runs over
every reconstructed line: `$cinst.$m(` and `obj.$m(` (obj a kObject variable
of an addressed class) must name a method the CURRENT export has.
check_notation cannot answer that when its vocabulary was built from an older
export.
"""
import sys, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# `Calculate <var> as con(<var>,…)` -- the house form of an emission chain.
RE_EMIT = re.compile(r"^Calculate\s+(\w+)\s+as\s+con\(\s*\1\s*,(.*)\)\s*$")
# the same chain, opened:  Calculate text2 as ''
RE_OPEN = re.compile(r"^Calculate\s+(\w+)\s+as\s+''\s*$")
# where a chain ENDS, and the only thing that tells us it was a method body:
# $methodtext.$assign(<var>).  Without this the protocol assembly, which is
# written in exactly the same form (`Calculate result as con(result,…)`), is
# read as a method and every blade then argues with a sentence of German.
RE_TARGET = re.compile(r"\$methodtext\.\$assign\(\s*(\w+)\s*\)")
RE_PIECE = re.compile(r"'((?:[^']|'')*)'|\"((?:[^\"]|\"\")*)\"|chr\((\d+)\)")
# A literal INSIDE an emitted literal is written with doubled quotes --
# 'Do out.$add(''verdict'',''ok'')'. Ending the literal at the first quote of
# the pair would let 'verdict' and 'ok' fall OUT of the string.
def _unesc(s):
    return s.replace("''", "'").replace('\"\"', '\"')



def pieces(body):
    """Concatenate the literals of one emission line; chr(nn) becomes its
    character.  Returns (text, leftover) where leftover is everything this
    could not see -- a variable, a function call, kCr."""
    out = ''
    for mm in RE_PIECE.finditer(body):
        a, b, c = mm.group(1), mm.group(2), mm.group(3)
        out += chr(int(c)) if c else _unesc(a if a is not None else b)
    rest = RE_PIECE.sub('', body)
    rest = re.sub(r'[\s,]|kCr', '', rest)
    return out, rest


def reconstruct(text):
    """Every method body the script assembles, in order.

    Returns a list of (varname, lines, suspect).  A chain starts at
    `Calculate <var> as \'\'` and ends at `$methodtext.$assign(<var>)`, so a
    script that builds three bodies in the same variable yields three.
    """
    targets = set(RE_TARGET.findall(text))
    bodies, open_chains = [], {}
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        m = RE_OPEN.match(line)
        if m and m.group(1) in targets:
            open_chains[m.group(1)] = ([], [])
            continue
        m = RE_EMIT.match(line)
        if m and m.group(1) in open_chains:
            lines, suspect = open_chains[m.group(1)]
            out, rest = pieces(m.group(2))
            lines.append(out)
            if rest:
                suspect.append((len(lines), n, out, rest))
            continue
        m = RE_TARGET.search(line)
        if m and m.group(1) in open_chains:
            lines, suspect = open_chains.pop(m.group(1))
            if lines:
                bodies.append((m.group(1), lines, suspect))
    return bodies


# --- the source-list form ------------------------------------------------
# The body is collected in a list and fed line by line into $methodlines.
#     Do list.$add('Calculate size as 0')
#     ...
#     Calculate text as trim(list.[n].src,...)
#     Set reference ref3 to group.$add(text)
# Without this form such a generator reads as "nothing generated", and every
# emitted line goes unchecked.
RE_GROUPADD = re.compile(r"\b(\w+)\.\$add\(\s*(\w+)\s*\)")
RE_FROMLIST = re.compile(r"Calculate\s+(\w+)\s+as\s+.*?\b(\w+)\.\[n\]\.\w+")
RE_LISTADD = re.compile(r"^Do\s+(\w+)\.\$add\(\s*(.*?)\s*\)\s*$")


def reconstruct_lists(text):
    """bodies collected in a list and fed into $methodlines, same shape as
    reconstruct(): (varname, lines, suspect)"""
    lines_all = text.split('\n')
    # which variable reaches a group's $add, and which list it was read from
    fed = set()
    for l in lines_all:
        m = RE_GROUPADD.search(l.strip())
        if m and 'methodlines' not in l:
            fed.add(m.group(2))
    listnames = {}
    for l in lines_all:
        m = RE_FROMLIST.match(l.strip())
        if m and m.group(1) in fed:
            listnames[m.group(2)] = True
    out = []
    for lname in listnames:
        body, suspect = [], []
        for n, raw in enumerate(lines_all, 1):
            m = RE_LISTADD.match(raw.strip())
            if not m or m.group(1) != lname:
                continue
            arg = m.group(2)
            if arg.startswith('$cols'):
                continue
            txt, rest = pieces(arg)
            if not txt.strip():
                continue
            body.append(txt)
            if rest:
                suspect.append((len(body), n, txt, rest))
        if body:
            out.append((lname, body, suspect))
    return out



# --- form 4: BLOCK REPLACEMENT ---------------------------------------------
# The whole method text is read, each change is an OLD and a NEW block, both
# kCr-bordered con-chains,
# swapped in with replaceall, and ONE $methodtext.$assign writes the result:
#     Calculate text3 as ''
#     Calculate text3 as con(text3,kCr,'If refKind=2')
#     ...
#     Calculate text as replaceall(text,text2,text3)
#     ...
#     Do methodRef.$methodtext.$assign(text)
# The assigned variable is never the one the lines are chained into, so form 1
# sees nothing. Only a chain that REACHES a replaceall into the assigned
# variable counts: the same
# variables are rebuilt afterwards for the read-back verification, and those
# chains write nothing.
RE_REPLACE = re.compile(r"^Calculate\s+(\w+)\s+as\s+replaceall\(\s*\1\s*,\s*(\w+)\s*,\s*(\w+)\s*\)")


def _split_kcr(body):
    """split a con() argument list at every kCr that stands OUTSIDE a literal"""
    parts, buf, i, q = [], '', 0, ''
    while i < len(body):
        c = body[i]
        if q:
            buf += c
            if c == q:
                if i + 1 < len(body) and body[i + 1] == q:
                    buf += q
                    i += 2
                    continue
                q = ''
        elif c in ("'", '"'):
            q = c
            buf += c
        elif body.startswith('kCr', i) and not (i and (body[i-1].isalnum() or body[i-1] in '_$')) \
                and not (i + 3 < len(body) and (body[i+3].isalnum() or body[i+3] == '_')):
            parts.append(buf)
            buf = ''
            i += 3
            continue
        else:
            buf += c
        i += 1
    parts.append(buf)
    return parts


def reconstruct_blocks(text):
    """blocks a block-replacement generator swaps in: (varname, lines, suspect)"""
    targets = set(RE_TARGET.findall(text))
    lines_all = text.split('\n')
    swaps = {}                      # new-block variable -> assigned variable
    for raw in lines_all:
        m = RE_REPLACE.match(raw.strip())
        if m and m.group(1) in targets:
            swaps[m.group(3)] = m.group(1)
    out, cur = [], {}
    for n, raw in enumerate(lines_all, 1):
        line = raw.strip()
        m = RE_OPEN.match(line)
        if m and m.group(1) in swaps:
            cur[m.group(1)] = ([], [])
            continue
        m = RE_EMIT.match(line)
        if m and m.group(1) in cur:
            # kCr is the line break of a block, so it splits here instead of
            # vanishing: two lines in one con() stay two lines
            lines, suspect = cur[m.group(1)]
            for part in _split_kcr(m.group(2)):
                txt, rest = pieces(part)
                if txt:
                    lines.append(txt)
                    if rest:
                        suspect.append((len(lines), n, txt, rest))
            continue
        m = RE_REPLACE.match(line)
        if m and m.group(3) in cur:
            lines, suspect = cur.pop(m.group(3))
            if lines:
                out.append((m.group(3) + ' block', lines, suspect))
    return out


# --- form 3: one method LINE into <ref>.$text --------------------------------
# The same form check_emitted_vars reads; here the line is checked for what it
# calls.
RE_LINEASSIGN = re.compile(r"\$text\.\$assign\(\s*(.+?)\s*\)\s*(?:Returns\s+\w+\s*)?$")
RE_CALCLIT = re.compile(r"^Calculate\s+(\w+)\s+as\s+(.*)$")


def reconstruct_lineassign(text):
    lines_all = text.split('\n')
    out, fed = [], set()
    for n, raw in enumerate(lines_all, 1):
        m = RE_LINEASSIGN.search(raw.strip())
        if not m:
            continue
        arg = m.group(1)
        if re.match(r"^\w+$", arg):
            fed.add(arg)
        else:
            txt, rest = pieces(arg)
            if txt.strip():
                out.append(('$text line', [txt], [(1, n, txt, rest)] if rest else []))
    for n, raw in enumerate(lines_all, 1):
        m = RE_CALCLIT.match(raw.strip())
        if m and m.group(1) in fed and not RE_EMIT.match(raw.strip()):
            txt, rest = pieces(m.group(2))
            if txt.strip():
                out.append(('$text line', [txt], [(1, n, txt, rest)] if rest else []))
    return out


# --- CALLS -----------------------------------------------------------------
# A generator that writes a CALL must call a method that exists. A vocabulary
# built from an OLD export still knows a method that has since gone; only the
# current export can answer, so this check runs only with --export.
#   $cinst.$m(   -> $m must be a method of one of the classes the script
#                   addresses, or documented Omnis notation ($redraw, ...)
#   obj.$m(      -> obj a kObject variable of one of those classes (iTools is
#                   kObject Tool): $m must be a method of that class
import json as _json
RE_CALL = re.compile(r"(\$cinst|\b[A-Za-z_]\w*)\.(\$\w+)\s*\(")
RE_CLS = re.compile(r"(?:\$root\.\$libs\.)?\b(\w+)\.\$(?:classes|codes|windows|reports|"
                    r"menus|toolbars|tasks|objects)\.(\w+)")


def _methods_of(export, cls):
    p = os.path.join(export, cls, 'methods.json')
    if not os.path.exists(p):
        return None
    try:
        return {e.get('name') for e in _json.load(open(p, encoding='utf-8'))}
    except Exception:
        return None


def _objvars(export, cls):
    out = {}
    p = os.path.join(export, cls, 'class.json')
    if os.path.exists(p):
        try:
            d = _json.load(open(p, encoding='utf-8'))
        except Exception:
            return out
        for key in ('ivardefs', 'cvardefs'):
            for v in d.get(key, []) or []:
                if v.get('type') == 'kObject' and v.get('subtype'):
                    out[v['name']] = v['subtype']
    return out


def _builtin():
    p = os.path.join(HERE, 'notation_vocab.json')
    try:
        v = _json.load(open(p, encoding='utf-8'))
    except Exception:
        return set()
    return set(v.get('help_member', [])) | set(v.get('help_mention', []))


def check_calls(lines, export, classes, added=()):
    """-> list of problems for calls to library methods that do not exist"""
    probs = []
    builtin = _builtin()
    own = set(added)
    objvars = {}
    for c in classes:
        own |= _methods_of(export, c) or set()
        objvars.update(_objvars(export, c))
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith('#'):
            continue
        s = re.sub(r"'(?:[^']|'')*'", "''", s)
        k = s.find('##')
        if k >= 0:
            s = s[:k]
        for m in RE_CALL.finditer(s):
            who, meth = m.group(1), m.group(2)
            if who == '$cinst':
                if meth not in own and meth not in builtin:
                    probs.append(f"line {i}: $cinst.{meth}() -- no method {meth} in "
                                 f"{'/'.join(sorted(classes))} of the export, and not Omnis notation")
            elif who in objvars:
                cls = objvars[who]
                got = _methods_of(export, cls)
                if got is not None and meth not in got and meth not in builtin:
                    probs.append(f"line {i}: {who}.{meth}() -- {who} is kObject {cls}, "
                                 f"and {cls} has no method {meth} in the export")
    return probs

RE_ADDMETHOD = re.compile(r"\$methods\.\$add\s*\(\s*'(\$\w+)'")


def script_methods(text):
    """Methods the script itself adds -- `$methods.$add('$name')` -- to a class
    or to an open instance. They are in no export yet, and the body it emits
    calls them."""
    return set(RE_ADDMETHOD.findall(text))


def run_blade(blade, path, export, own=()):
    cmd = [sys.executable, os.path.join(HERE, blade)]
    if export and blade == 'check_notation.py':
        cmd += ['--export', export]
    if own and blade == 'check_notation.py':
        cmd += ['--own', ','.join(sorted(own))]
    cmd += [path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout


def main():
    args = sys.argv[1:]
    export, show = None, False
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

    bad = 0
    for name in args:
        if not os.path.isfile(name):
            print(f"skip (not a file): {name}")
            continue
        text = open(name, encoding='utf-8', errors='replace').read()
        bodies = (reconstruct(text) + reconstruct_lists(text)
                  + reconstruct_blocks(text) + reconstruct_lineassign(text))
        classes = sorted({c for _, c in RE_CLS.findall(text)})
        added = script_methods(text)
        base = os.path.basename(name)
        if not bodies:
            print(f"..   {base}: no emission chain ending in "
                  f"$methodtext.$assign -- nothing generated, or assembled in "
                  f"a form this blade does not know")
            continue
        fails = 0
        for k, (var, lines, suspect) in enumerate(bodies, 1):
            tag = f"{base} body {k}/{len(bodies)} ({var}, {len(lines)} lines)"
            tmp = os.path.join('/tmp', f'emitted_{k}_' + base)
            open(tmp, 'w', encoding='utf-8').write('\n'.join(lines))
            if show:
                print(f"--- {tag} ---")
                for i, l in enumerate(lines, 1):
                    print(f"{i:>4}  {l}")
                continue
            probs = []
            for blade in ('check_notation.py', 'check_commands.py'):
                out = run_blade(blade, tmp, export, added)
                for l in out.split('\n'):
                    if l.strip().startswith('->'):
                        probs.append(f"{blade[6:-3]}: {l.strip()[3:]}")
            if export:
                for pr in check_calls(lines, export, classes, added):
                    probs.append(f"calls: {pr}")
            if probs:
                fails += 1
                print(f"FAIL {tag}")
                for pr in probs:
                    print(f"     -> {pr}")
            else:
                print(f"ok   {tag}")
            if suspect:
                print(f"     .. {len(suspect)} line(s) carried more than "
                      f"literals, so the reconstruction is partial there:")
                for kk, nn, out, rest in suspect[:4]:
                    print(f"        line {kk} (script line {nn}): {out}")
        if fails:
            bad += 1
        if not export and not show:
            print("     .. no --export given: every method of the library "
                  "reads as invented, so rule 4 findings may be false")
    print(f"\n{len(args)-bad}/{len(args)} clean (emitted method text)")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
