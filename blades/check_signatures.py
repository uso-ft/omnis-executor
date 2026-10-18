#!/usr/bin/env python3
"""
Signature blade — compares every call site against the declared parameter
count of the method it calls.

Usage:  python3 check_signatures.py <export-root> [script.txt ...]

A method name that Omnis also documents is reported as a NOTE, never as a
mismatch: at a call site the two cannot be told apart. The list comes from
notation_vocab.json, built by build_notation_vocab.py.

The defect it exists for: a method is given a required parameter, and one of
its call sites is missed --

        Calculate vBackup as $itasks.Executor.$ensureVault()

Omnis does NOT complain: a missing parameter simply arrives empty. A method
that builds a file path from it then creates a library called ".lbs" in the
Omnis directory, and reopens it on every run.

WHAT IT REPORTS

  1. MORE arguments than declared -> FAIL. The extra ones are discarded, so
     the call claims something the method does not do.

  2. A script that GIVES A METHOD A NEW PARAMETER -> the blade lists every
     call site of that method in the library, as a checklist. This is the
     main event, and the reason the blade exists.

  3. FEWER arguments than declared -> NOTE, but ONLY when a parameter that
     is not marked `_opt` is being omitted (CONTRACT.md §3.6). Listing needs
     --opt; the count is always shown.

  Without the `_opt` convention, fewer-arguments could not be judged at all. Measured on the
  Executor library: 64 call sites pass fewer arguments than declared, and
  they are fine -- Omnis parameters are optional and trailing ones are
  routinely omitted ($cloneMethodToAndExecute is called with 5 of 9).
  Even zero-of-one is normal: $setExecutorValues() appears 14 times.
  The defect above looks STRUCTURALLY IDENTICAL to all of those. What makes
  it a defect is temporal -- the method has just gained the parameter. That is what
  check 2 catches, and no static arity rule ever could.

RESOLUTION AND ITS LIMITS
  A call `x.$foo(a,b)` is only checked when `$foo` is unambiguous across the
  library: either it exists in exactly one class, or every class that has it
  declares the same number of parameters.  Otherwise the receiver would have
  to be resolved, which is not reliably possible from text.  Ambiguous names
  are listed at the end so the silence is visible.

  Built-in Omnis methods ($add, $assign, $findname ...) are never checked --
  only names that appear as user methods in the export.

  THE AUDIT IS ONLY AS GOOD AS THE EXPORT.  A method whose signature changed
  since the last export is compared against its old declaration.  Re-export
  after changing any signature, then run this.
"""
import sys, os, json, re, glob


def load_methods(root):
    """{methodName: {paramCount: [class, ...]}} from every methods.json."""
    sigs = {}
    for mj in glob.glob(os.path.join(root, '**', 'methods.json'), recursive=True):
        if '__MACOSX' in mj:
            continue
        cls = os.path.basename(os.path.dirname(mj))
        try:
            entries = json.load(open(mj, encoding='utf-8', errors='replace'))
        except Exception:
            continue
        for m in entries:
            name = m.get('name', '')
            if not name.startswith('$'):
                continue
            names = [v.get('name', '') for v in m.get('pvardefs', [])]
            n = len(names)
            sigs.setdefault(name, {}).setdefault(n, {'cls': [], 'names': names})
            sigs[name][n]['cls'].append(cls)
    return sigs


def split_args(s):
    """Top-level comma split, honouring quotes and nesting."""
    out, depth, cur, inq = [], 0, '', False
    for ch in s:
        if ch == "'":
            inq = not inq
            cur += ch
        elif inq:
            cur += ch
        elif ch in '([':
            depth += 1
            cur += ch
        elif ch in ')]':
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


def param_additions(text):
    """Methods a script gives a new parameter to.

    A `$methods.$findname('$X')` or `$methods.$add('$X')` establishes the
    current method; a later `$lvardefs.$add(name,type,sub,len,TRUE)` gives it
    a parameter. The fifth argument is a BOOLEAN, not a position -- and it is
    written both as `kTrue` and as a bare `1` in practice, so the argument
    list is parsed rather than matched at the tail.
    """
    found, current = [], None
    for raw in text.split('\n'):
        line = raw.strip()
        if line.startswith('#'):
            continue
        m = re.search(r"\$methods\.\$(?:findname|add)\s*\(\s*'(\$\w+)'", line)
        if m:
            current = m.group(1)
        # The fifth argument of $lvardefs.$add is a BOOLEAN "is a parameter".
        # Written as kTrue or as a bare 1 -- both occur in our own scripts,
        # which is why this is parsed instead of pattern-matched at the tail.
        for m2 in re.finditer(r"\$lvardefs\.\$add\s*\(", line):
            body = call_body(line, line.index('(', m2.end() - 1))
            if body is None:
                continue
            a = split_args(body)
            if len(a) >= 5 and a[4].strip() in ('kTrue', '1') and current:
                if current not in found:
                    found.append(current)
    return found


def call_sites(name, root):
    """Every place in the export that calls `name`."""
    out = []
    for omh in glob.glob(os.path.join(root, '**', '*.omh'), recursive=True):
        if '__MACOSX' in omh:
            continue
        rel = os.path.join(os.path.basename(os.path.dirname(omh)),
                           os.path.basename(omh))
        for n, raw in enumerate(open(omh, encoding='utf-8', errors='replace')
                                .read().split('\n'), 1):
            line = raw.strip()
            if line.startswith('#') or ('.' + name + '(') not in line:
                continue
            body = call_body(line, line.index('.' + name + '(') + len(name) + 1)
            given = len(split_args(body)) if body is not None else -1
            out.append((rel, n, given, line[:90]))
    return out


def scan(text, sigs, where):
    hard, soft = [], []
    for n, raw in enumerate(text.split('\n'), 1):
        line = raw.strip()
        if line.startswith('#'):
            continue
        masked = re.sub(r"'[^']*'", lambda m: "'" + "\x00" * (len(m.group(0)) - 2) + "'", line)
        i = masked.find('##')
        if i >= 0:
            line = line[:i]

        for m in re.finditer(r'\.(\$\w+)\s*\(', line):
            name = m.group(1)
            if name not in sigs:
                continue                     # built-in or unknown -- not ours
            counts = set(sigs[name])
            if len(counts) != 1:
                continue                     # ambiguous, reported separately
            declared = counts.pop()
            pnames = sigs[name][declared]['names']
            body = call_body(line, line.index('(', m.end() - 1))
            if body is None:
                continue
            given = len(split_args(body))
            if given > declared:
                # A name the library declares AND Omnis documents cannot be
                # judged from the text: the call site may mean either.
                # copyRef.$redraw(kTrue,kTrue) is the documented
                # $redraw([bSetcontents,bRefresh,bBobjs]) on a field, not the
                # library's own $redraw.
                if name in SHADOWED:
                    soft.append(f"NOTE {where}:{n}: {name} called with {given} "
                                f"arguments but the library declares "
                                f"{declared} -- this name is ALSO documented "
                                f"Omnis notation, so the call may mean either")
                else:
                    hard.append(f"{where}:{n}: {name} called with {given} arguments "
                                f"but declares {declared}")
            elif given < declared:
                # Omitted parameters are fine WHEN THEY SAY SO: the _opt
                # suffix (CONTRACT.md §3.6) is the only thing that distinguishes
                # a deliberate default from a forgotten argument.
                missing = pnames[given:]
                unmarked = [x for x in missing if not x.endswith('_opt')]
                if unmarked:
                    soft.append(f"NOTE {where}:{n}: {name} omits "
                                f"{', '.join(unmarked)} -- not marked _opt. "
                                f"Either pass it, or rename the parameter so "
                                f"the optionality is declared")
    return hard, soft


def load_shadowed():
    """Method names that Omnis documents itself. A library may declare a
    method of the same name; a call site then cannot be attributed."""
    for cand in (os.path.join(HERE, 'notation_vocab.json'), 'notation_vocab.json'):
        if os.path.isfile(cand):
            v = json.load(open(cand, encoding='utf-8'))
            return set(v.get('help_member', [])) | set(v.get('help_mention', []))
    return set()


HERE = os.path.dirname(os.path.abspath(__file__))
SHADOWED = load_shadowed()


def main():
    args = sys.argv[1:]
    if not args or not os.path.isdir(args[0]):
        print("usage: python3 check_signatures.py <export-root> [script.txt ...]")
        return 2
    root, scripts = args[0], args[1:]

    sigs = load_methods(root)
    if not sigs:
        print(f"BLADE UNUSABLE: no methods.json found under {root}")
        return 2

    ambiguous = sorted(n for n, c in sigs.items() if len(c) > 1)

    hard, soft = [], []
    for omh in glob.glob(os.path.join(root, '**', '*.omh'), recursive=True):
        if '__MACOSX' in omh:
            continue
        rel = os.path.join(os.path.basename(os.path.dirname(omh)),
                           os.path.basename(omh))
        h, s = scan(open(omh, encoding='utf-8', errors='replace').read(), sigs, rel)
        hard += h
        soft += s
    for sc in scripts:
        if os.path.isfile(sc):
            h, s = scan(open(sc, encoding='utf-8', errors='replace').read(),
                        sigs, os.path.basename(sc))
            hard += h
            soft += s

    for p in hard:
        print(f"  -> {p}")
    if '--opt' in sys.argv:
        for p in soft:
            print(f"  .. {p[5:]}")
    print(f"\n{len(sigs)} user methods known, {len(hard)} hard mismatch(es), "
          f"{len(soft)} unmarked-optional (--opt to list)")

    # --- the main event: does a delivered script change a signature? -----
    for sc in scripts:
        if not os.path.isfile(sc):
            continue
        added = param_additions(open(sc, encoding='utf-8', errors='replace').read())
        if not added:
            continue
        print(f"\n=== {os.path.basename(sc)} gives new parameters ===")
        for name in added:
            sites = call_sites(name, root)
            declared = sorted(sigs.get(name, {0: None}))[0]
            print(f"\n  {name}  (declared {declared} before this script, now "
                  f"{declared + 1})")
            if not sites:
                print("    no call site found in the export -- check that the "
                      "export is current")
            for rel, n, given, snippet in sites:
                mark = "  <-- TOO FEW" if 0 <= given <= declared else ""
                print(f"    {rel}:{n}  {given} arg(s){mark}")
                print(f"        {snippet}")
        print("\n  Every one of these must be checked by hand. Omnis does not "
              "complain about a missing\n  parameter -- it arrives empty, and "
              "the method quietly does something else.")
    if ambiguous:
        print(f"not checked (same name, different parameter counts): "
              f"{', '.join(ambiguous)}")
    return 0 if not hard else 1


if __name__ == '__main__':
    sys.exit(main())
