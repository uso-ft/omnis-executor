#!/usr/bin/env python3
"""
Jump-link blade — validates every jump line BEFORE delivery.
Usage:  python3 check_jumplinks.py <file-with-jump-block>  [export-root]
        python3 check_jumplinks.py -   (read lines from stdin)

Rules enforced (the jump-line form of CONTRACT.md §4):
 1. every target line starts with 'Do ' (a bare expression is not a valid
    method line — the clicked line becomes the jumper's method text)
 2. METHOD target  -> LIB.$classes.CLASS.$methods.//$name//.$modify(LINE)
 3. CLASS target   -> the bare path LIB.$classes.CLASS, checked for existence.
    $jump hands every target to Tool.$edit, which resolves it quietly and opens a
    pure class with $modify(ref,kTrue).
    REFUSED: iTools.$modify(<path>.$ref,kFalse), an old form. $edit cannot walk
    a call, cuts at the last '.$' and shows the PROPERTY MANAGER instead. Also
    refused: LIB.$classes.CLASS.$modify(n).
 4. OBJECT method  -> full container chain via objlink, never guessed
 5. VARIABLE target -> LIB.$classes.CLASS.$cvardefs.NAME (or $ivardefs) — the
    design editor opens at the variable list of that class, which is as close
    as the notation gets to a single variable. Checked against
    cvardefs/ivardefs in class.json, because a
    typo in the name jumps to a list that simply does not hold it, and
    nothing says so at the time of the click.
 5b. LOCAL VARIABLE or PARAMETER of a method ->
    LIB.$classes.CLASS.$methods.//NAME//.$lvardefs.VAR — Tool.$edit opens the
    owner method and moves to Parameters or Locals by $parmno. Checked against
    lvardefs/pvardefs in methods.json -- the whole path, not only the method.
 6. OTHER -> plain full path wrapped in Do
 7. existence: class / method / object / variable must exist in the export
 8. line number must be within the method's line count
 9. SHORT library form: a target never starts with $root.$libs. or $libs.
    Both resolve, but the short form is what the jump
    list, the target field and the log show, and one form is readable at a
    glance. A computed library ($root.$libs.[name]) is refused as well: a jump
    target is a fixed address.
"""
import sys, os, re, json

def load_export(root):
    """index classes, methods, objects and objlink->order mapping

    The root may be given at EITHER level: the library folder that holds the
    class folders, or the folder one above it that holds the library.  This
    blade wanted the first, check_notation --export wants the second, and
    check_all hands both the same string. With the wrong level every jump
    line would report "class not found in export", a false FAIL.

    The descent fires ONLY when the given level indexed no method file at all,
    which is exactly the wrong-level case; when the root is already correct
    nothing below runs and the behaviour is bit-for-bit what it was.
    """
    idx = {'classes': {}, 'methods': {}, 'objs': {}, 'order': {}}
    if not os.path.isdir(root):
        return idx
    _index_level(root, idx)
    if not any(idx['methods'].values()):
        for lib in sorted(os.listdir(root)):
            libdir = os.path.join(root, lib)
            if os.path.isdir(libdir):
                _index_level(libdir, idx)
    return idx

def _index_level(root, idx):
    """index one folder as if it held the class folders; merges into idx"""
    for cls in os.listdir(root):
        cdir = os.path.join(root, cls)
        if not os.path.isdir(cdir):
            continue
        idx['classes'][cls] = cdir
        methods = set()
        for f in os.listdir(cdir):
            if f.endswith('.omh'):
                methods.add(f[:-4])
        idx['methods'][cls] = methods
        odir = os.path.join(cdir, 'objs')
        if os.path.isdir(odir):
            objs = {}
            for o in os.listdir(odir):
                jf = os.path.join(odir, o, 'object.json')
                if os.path.isfile(jf):
                    try:
                        d = json.load(open(jf))
                        objs[o] = {'order': d.get('order'),
                                   'objlink': d.get('properties', {}).get('objlink')}
                    except Exception:
                        objs[o] = {'order': None, 'objlink': None}
            idx['objs'][cls] = objs
    return idx

def container_chain(cls, obj, idx):
    """resolve full container chain of an object via objlink -> order"""
    objs = idx['objs'].get(cls, {})
    if obj not in objs:
        return None
    chain = [obj]
    seen = set()
    cur = obj
    while True:
        link = objs[cur]['objlink']
        if link in (None, 0):
            break
        parent = [n for n, v in objs.items() if v['order'] == link]
        if not parent or parent[0] in seen:
            break
        cur = parent[0]
        seen.add(cur)
        chain.insert(0, cur)
    return chain

def method_line_count(root, cls, method, idx=None):
    """Line count of a method body, or None when the file cannot be found.

    The class directory is taken from the INDEX, not rebuilt from root+cls:
    load_export may have indexed one level below the given root, and joining
    root and cls then points at nothing, and a silent None would skip rule 8
    altogether -- a jump line to line 9999 would pass.
    """
    cdir = (idx or {}).get('classes', {}).get(cls) or os.path.join(root, cls)
    p = os.path.join(cdir, method + '.omh')
    if not os.path.isfile(p):
        return None
    t = open(p, encoding='utf-8', errors='replace').read().replace('\r', '')
    lines = t.split('\n')
    while lines and lines[-1] == '':
        lines.pop()
    return len(lines)

def creations(text):
    """Classes and methods this script CREATES, so a jump line may point there.

    A creation script legitimately jumps to a method that does not exist in
    the export yet -- the export was taken before the run. Two signals must
    agree: the script declares at least one class it creates or modifies (the
    CREATES line names classes only, never methods), AND a real
    `$methods.$add('$name')` stands in the body. A typo is still caught,
    because a use that differs from the `$methods.$add` literal is not in the
    set.
    """
    header, body = False, set()
    for line in text.split('\n'):
        st = line.strip()
        if st.startswith('# CREATES:') or st.startswith('# MODIFIES:'):
            if re.search(r'\b\w+\.\w+\b', st.split(':', 1)[1]):
                header = True
        for m in re.finditer(r"\$methods\.\$add\s*\(\s*'(\$\w+)'", line):
            body.add(m.group(1))
    return body if header else set()


def created_classes(text):
    """CLASSES this script creates, by the same two-signal rule.

    A script that builds a whole class must be able to point at it -- the
    class exists nowhere else yet.
    Both signals again: the name after a library prefix on the CREATES line,
    AND a real `$classes.$add(<type>,'Name')` in the body.
    """
    header, body = set(), set()
    for line in text.split('\n'):
        if line.strip().startswith('# CREATES:'):
            # The library name may start in lower case: execScratch.zzProbeWin
            # is a class a probe builds in execScratch.
            for m in re.finditer(r'(?<![\w$.])\w+\.(\w+)\b', line.split(':', 1)[1]):
                header.add(m.group(1))
        for m in re.finditer(r"\$classes\.\$add\s*\(\s*k\w+\s*,\s*'([\w]+)'", line):
            body.add(m.group(1))
    return header & body


def method_vars(cls, meth, idx, root):
    """names of the locals and parameters of one method (methods.json of the
    class), or None when the method is not there."""
    cdir = idx.get('classes', {}).get(cls) or os.path.join(root or '', cls)
    p = os.path.join(cdir, 'methods.json')
    if not os.path.isfile(p):
        return None
    try:
        data = json.load(open(p, encoding='utf-8', errors='replace'))
    except Exception:
        return None
    for m in data if isinstance(data, list) else []:
        if m.get('name') == meth:
            return {v.get('name') for k in ('lvardefs', 'pvardefs') for v in m.get(k, [])}
    return None

def class_vars(root, cls, kind, idx):
    """the names in cvardefs or ivardefs of one class, or None when unreadable

    None and an empty set are different answers: None means the blade could
    not look (no class.json in the export) and must stay quiet, an empty set
    means the class really declares no variable of that kind.
    """
    cdir = idx['classes'].get(cls)
    if not cdir:
        return None
    jf = os.path.join(cdir, 'class.json')
    if not os.path.isfile(jf):
        return None
    try:
        d = json.load(open(jf, encoding='utf-8'))
    except Exception:
        return None
    return {v.get('name') for v in d.get(kind, []) if isinstance(v, dict)}


def check(line, idx, root, created=frozenset(), newclasses=frozenset()):
    """returns list of problems for one jump line"""
    probs = []
    raw = line.strip()
    if not raw or raw.startswith('## ====='):
        return probs
    body = raw.lstrip('#').strip()
    if not body:
        return probs
    code = body.split('##')[0].strip()
    if not code:
        return probs

    if not code.startswith('Do '):
        probs.append("missing 'Do ' prefix — a bare expression is not a valid method line")
        return probs

    expr = code[3:].strip()

    # --- rule 9: short library form ---
    m = re.match(r"(\$root\.)?\$libs\.(.*)$", expr)
    if m:
        probs.append(f"long library form -- write the short form: '{m.group(2)}' "
                     "(no $root.$libs. in front, rule 9)")
        return probs

    # --- the old CLASS form iTools.$modify(...) -- refused ---
    m = re.match(r"(?:iTools|tools)\.\$modify\((.+?)\.\$ref\s*,\s*(kFalse|kTrue)\)$", expr)
    if m:
        path = re.sub(r"^(\$root\.)?\$libs\.", "", m.group(1))
        probs.append(f"iTools.$modify(...) does not jump: Tool.$edit cannot walk a call "
                     f"and shows the property manager -- write the bare path '{path}' (rule 3)")
        return probs

    # --- CLASS target: the bare path ---
    m = re.match(r"([\w#]+)\.\$classes\.([\w#]+)$", expr)
    if m:
        cls = m.group(2)
        if cls not in idx['classes'] and cls not in newclasses:
            probs.append(f"class '{cls}' not found in export")
        return probs

    # --- METHOD target ---
    m = re.match(r"([\w#]+)\.\$classes\.([\w#]+)\.\$methods\.//(.+?)//\.\$modify\((\d+)\)$", expr)
    if m:
        lib, cls, meth, ln = m.group(1), m.group(2), m.group(3), int(m.group(4))
        if cls in newclasses:
            # the whole class is built by this script. When the script adds
            # methods by name, the jump must name one of them -- otherwise a
            # misspelt method of the script's own class would pass.
            if created and meth not in created:
                probs.append(f"method '{meth}' is not one this script adds to the "
                             f"class it builds ({', '.join(sorted(created))})")
        elif cls not in idx['classes']:
            probs.append(f"class '{cls}' not found in export")
        elif meth in created:
            pass          # created by this very script -- not in the export yet
        elif meth not in idx['methods'].get(cls, set()):
            probs.append(f"method '{meth}' not found in class '{cls}'")
        else:
            n = method_line_count(root, cls, meth, idx)
            if n is not None and ln > n:
                probs.append(f"line {ln} beyond method length ({n} lines)")
            if ln < 1:
                probs.append("line number must be >= 1")
        return probs

    # --- OBJECT method target ---
    m = re.match(r"([\w#]+)\.\$classes\.([\w#]+)\.(\$objs\..+)\.\$methods\.//(.+?)//\.\$modify\((\d+)\)$", expr)
    if m:
        lib, cls, objpath, meth, ln = m.group(1), m.group(2), m.group(3), m.group(4), int(m.group(5))
        if cls not in idx['classes']:
            probs.append(f"class '{cls}' not found in export")
            return probs
        parts = [p for p in objpath.split('.') if p != '$objs']
        leaf = parts[-1]
        chain = container_chain(cls, leaf, idx)
        if chain is None:
            probs.append(f"object '{leaf}' not found in class '{cls}'")
        else:
            # Both sides must be spelled the same way. Joining the given path
            # with '.' while the expected one is joined with '.$objs.' would
            # fail every NESTED object jump link.
            expected = '.$objs.'.join(chain)
            got = '.$objs.'.join(parts)
            if expected != got:
                probs.append(f"container chain wrong: given '{got}', objlink says '{expected}'")
        return probs

    # --- CLASS via $modify(n) — the mistake to catch ---
    m = re.match(r"[\w#]+\.\$classes\.([\w#]+)\.\$modify\(\d*\)$", expr)
    if m:
        probs.append("class target uses method syntax $modify(n) — write the "
                     "bare path LIB.$classes.CLASS for a class (rule 3)")
        return probs

    # --- VARIABLE target: $cvardefs / $ivardefs of a class ---
    m = re.match(r"([\w#]+)\.\$classes\.([\w#]+)\.\$(cvardefs|ivardefs)\.([\w#]+)$", expr)
    if m:
        cls, kind, var = m.group(2), m.group(3), m.group(4)
        if cls in newclasses:
            return probs                      # the whole class is built by this script
        if cls not in idx['classes']:
            probs.append(f"class '{cls}' not found in export")
            return probs
        names = class_vars(root, cls, kind, idx)
        if names is None:
            return probs                      # no class.json to read: stay quiet
        if var not in names:
            other = 'ivardefs' if kind == 'cvardefs' else 'cvardefs'
            hint = f" (it is a {other[:-4]} of that class)" if var in (class_vars(root, cls, other, idx) or set()) else ''
            probs.append(f"variable '{var}' not found in {kind} of class '{cls}'{hint}")
        return probs

    # --- LOCAL VARIABLE / PARAMETER: $lvardefs of a method ---
    m = re.match(r"([\w#]+)\.\$classes\.([\w#]+)\.\$methods\.(//)?([\w$#]+)(//)?\.\$lvardefs\.([\w#]+)$", expr)
    if m:
        cls, meth, var = m.group(2), m.group(4), m.group(6)
        if meth.startswith('$') and not (m.group(3) and m.group(5)):
            probs.append(f"method name '{meth}' must be written //{meth}// (rule 2)")
            return probs
        if cls in newclasses:
            return probs
        if cls not in idx['classes']:
            probs.append(f"class '{cls}' not found in export")
            return probs
        names = method_vars(cls, meth, idx, root)
        if names is None:
            probs.append(f"method '{meth}' not found in class '{cls}'")
            return probs
        if var not in names:
            probs.append(f"variable '{var}' is neither a local nor a parameter of '{cls}.{meth}'")
        return probs

    # --- plain path (property / group) ---
    if expr.startswith('$root.') or re.match(r"^[\w#]+\.\$", expr):
        return probs

    probs.append("unrecognized jump form — check against the build instructions")
    return probs

def main():
    args = [a for a in sys.argv[1:]]
    # No hard-coded fallback root: a stale absolute path looks like a real
    # export and produces a false 'class not found' on every existence-checked
    # line. When no root is given, say so once -- same wording check_all.py
    # prints for this case -- and proceed with an empty index (load_export
    # returns one for any path that is not a directory).
    root = args[1] if len(args) > 1 else None
    if not args or args[0] == '-':
        text = sys.stdin.read()
    else:
        text = open(args[0], encoding='utf-8', errors='replace').read()
    lines = text.split('\n')
    created = creations(text)
    newclasses = created_classes(text)
    if root is None:
        print("NOTE no export root given -- jump lines were NOT verified "
              "against a library. Syntax and existence unchecked.")
        idx = {'classes': {}, 'methods': {}, 'objs': {}, 'order': {}}
    else:
        idx = load_export(root)

    # Only look INSIDE the jump block. $parseJumpBlock does the same at
    # runtime: it starts after the '## ===== JUMP LINKS =====' marker.
    # Without this a documentation comment that merely mentions $root. is
    # reported as a broken jump line.
    marked = [i for i, l in enumerate(lines) if l.strip().startswith('## =====')
              and 'JUMP LINKS' in l.upper()]

    # --- the header is part of the artefact --------------------------------
    # A jump line outside the block is dead: $parseJumpBlock never reaches it,
    # so it renders as an ordinary comment and the click does nothing. The
    # form can be right and the artefact still wrong.
    # Detection is deliberately tight: the comment body must START with 'Do '
    # AND carry $modify, so prose that merely mentions $root. is not caught.
    # The self-jump prologue is NOT a jump line. A manual-road script MUST
    # open with
    #     Do Executor.$classes.Executor.$methods.//$execute//.$modify(<N>)
    # as its FIRST OPERATIVE line (check_header rule 5), which is by
    # definition before any JUMP LINKS block. The number in that line is
    # checked by check_header against the start marker, so nothing goes
    # unchecked by the exemption.
    selfjump = re.compile(r'^Do\s+Executor\.\$classes\.Executor\.\$methods\.'
                          r'//\$execute//\.\$modify\(\d+\)')
    strays = []
    for i, l in enumerate(lines):
        body = l.strip().lstrip('#').strip()
        if body.startswith('Do ') and '$modify' in body:
            if selfjump.match(body):
                continue
            # An OPERATIVE line `Do methodRef.$modify(1)` is code -- it opens the
            # method editor at run time -- not a jump line. An uncommented
            # line counts only when it starts at a library path, the form a
            # jump line has.
            if not l.strip().startswith('#') and \
                    not re.match(r'Do\s+[\w#]+\.\$classes\.', body):
                continue
            if not marked or i < marked[0]:
                strays.append((i + 1, body))
    if strays:
        for ln, body in strays:
            print(f"FAIL {body[:90]}")
            if not marked:
                print("     -> jump line but no '## ===== JUMP LINKS =====' header "
                      "anywhere in the file. $parseJumpBlock starts AFTER that "
                      "marker, so this line is never seen and the click does "
                      f"nothing (line {ln})")
            else:
                print("     -> jump line sits BEFORE the "
                      "'## ===== JUMP LINKS =====' header, so $parseJumpBlock "
                      f"never reaches it (line {ln}). Move it into the block")
        print(f"\n0/{len(strays)} jump lines valid")
        return 1

    if marked:
        lines = lines[marked[0] + 1:]

    total = ok = 0
    for line in lines:
        s = line.strip()
        if not s.startswith('#') or s.startswith('## ====='):
            continue
        body = s.lstrip('#').strip()
        # A line is a jump line when its body starts with 'Do ', or when it
        # carries $modify / iTools (an old form missing its 'Do ' must still
        # be caught). A description line that merely MENTIONS $root. or
        # $libs. is prose.
        if not (body.startswith('Do ') or '$modify' in s or 'iTools' in s):
            continue
        total += 1
        probs = check(line, idx, root, created, newclasses)
        if probs:
            print(f"FAIL {s[:90]}")
            for p in probs:
                print(f"     -> {p}")
        else:
            ok += 1
    print(f"\n{ok}/{total} jump lines valid")
    return 0 if ok == total else 1

if __name__ == '__main__':
    sys.exit(main())
