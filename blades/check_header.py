#!/usr/bin/env python3
"""
Header blade — validates the header block of a generator script BEFORE delivery.

Usage:  python3 check_header.py <script.txt> [more.txt ...]
        python3 check_header.py -            (read one script from stdin)

Rules enforced (CONTRACT.md §1.5):
 1. GENERATOR line present, with a version and a DATE plus TIME
    form:  # GENERATOR: <name> v<n> — YYYY-MM-DD HH:MM
    READER and PROBE are accepted in place of GENERATOR.
 2. RUNS-IN line present, naming the EXECUTOR VERSION the script was written
    for, major.minor:
        # RUNS-IN:  EXECUTOR 1.0
    The variable set is part of the contract of that version and is not
    named. The console checks the version softly (ExecutorConsole.$versionCheck):
    no version is silent, an unreadable one is a trace line. The blade is the
    author's side and is stricter: 'EXECUTOR' followed by something that is not
    <major>.<minor> FAILS -- a typo here is the author's, and the console would
    only mention it. The form before 1.0, '(v1.<n> variable set)', still
    passes, with a NOTE.
 3. CREATES / MODIFIES / REMOVES lines present (may say 'nothing')
 4. the script opens its protocol with a run stamp:
    Calculate result as con('run ',#T, ...) -- or con('run manually ',#T, ...)
    on the manual road: execMode cannot tell the roads apart, because 0
    also means "written before the column was filled", so the textual marker
    in the protocol is the only reliable distinction and must be allowed here.
 5. a script that rebuilds RUNTIME classes opens with the self-jump
    (Do ...$execute.$modify(<N>) + Quit all methods) and <N> matches the
    position of the start marker.
    The RUNTIME set is a set of CLASSES, but the real reason for the manual
    road is narrower: the console cannot rebuild a method that is IN THE
    RUNNING STACK. A runtime class can hold methods nobody calls during a
    run, and forcing those onto the manual road buys nothing and costs the
    seatbelt, the manifest and the verdict. The blade cannot see the stack,
    so the author declares it:
        # ROAD: ordinary — <why this method is not in the running stack>
    That lifts the self-jump demand. The reason is required and must be
    substantial; the blade will not accept a rubber stamp. Declaring
    'ordinary' and carrying a self-jump anyway is a contradiction and is
    flagged. Without a ROAD line the class-level rule applies.
 6. every class named in MODIFIES is freed in the prologue:
    Close design <Class> (+ closing live instances for window classes) —
    otherwise the rebuild stalls on an open editor or a live instance
 7. no bare '##' followed immediately by a non-space character anywhere in
    the emitted text — Omnis rewrites '##x' to '## x', so such a tag never
    reaches the parser
"""
import sys, re, os

def check(path, text):
    probs = []
    lines = text.split('\n')

    # --- 1 GENERATOR line with date AND time -------------------------------
    # The family line may read GENERATOR, READER or PROBE, as $parseHeader
    # accepts; the verdict needs one of them -- without a family row it
    # answers 'open' and judges nothing. The demands on version, date and
    # time are the same for all three, and a bare probe with no header at all
    # is not failed: check_all only reaches this blade when a header line is
    # present.
    gen = [l for l in lines
           if re.match(r'#\s*(GENERATOR|READER|PROBE):', l.strip())]
    if not gen:
        probs.append("no family header line -- '# GENERATOR:', '# READER:' "
                     "or '# PROBE:'")
    else:
        g = gen[0]
        if not re.search(r'\bv\d+', g):
            probs.append("GENERATOR line carries no version (v1, v2, ...)")
        m = re.search(r'(\d{4}-\d{2}-\d{2})(\s+(\d{1,2}:\d{2}))?', g)
        if not m:
            probs.append("GENERATOR line carries no date")
        elif not m.group(3):
            probs.append("GENERATOR line has a date but NO TIME — "
                         "agreed form: YYYY-MM-DD HH:MM")

    # --- 2 RUNS-IN ---------------------------------------------------------
    runs = [l for l in lines if 'RUNS-IN' in l]
    if not runs:
        probs.append("no 'RUNS-IN' line (which variable set?)")
    else:
        # since 1.0: '# RUNS-IN: EXECUTOR <major>.<minor>'.
        # The value is read as the console reads it: after the colon, trimmed,
        # case-insensitive, anything after the minor ignored (a patch, a note).
        val = runs[0].split(':', 1)[1].strip() if ':' in runs[0] else ''
        if re.match(r'EXECUTOR\s+\d+\.\d+', val, re.I):
            pass
        elif re.search(r'(v0|v1\.\d+)\s*(variable\s*)?set', runs[0]):
            probs.append("NOTE RUNS-IN names a variable set, the form before "
                         "1.0 -- since 1.0 write '# RUNS-IN: EXECUTOR 1.0'")
        elif re.match(r'EXECUTOR\b', val, re.I) and 'CONSOLE' not in val.upper():
            probs.append("RUNS-IN names no Executor version this console can "
                         "read -- the form is '# RUNS-IN: EXECUTOR 1.0' "
                         "(major.minor)")
        else:
            probs.append("RUNS-IN line names no Executor version "
                         "(e.g. EXECUTOR 1.0)")

    # --- 3 CREATES / MODIFIES / REMOVES ------------------------------------
    for key in ('CREATES', 'MODIFIES', 'REMOVES'):
        if not any(key in l for l in lines):
            probs.append(f"no '{key}:' line")

    # --- 5 self-jumping prologue for RUNTIME classes ------------------------
    RUNTIME = {'ExecutorConsole', 'Tool', 'Startup_Task', 'Executor', 'ExecutorVessel'}
    mods = [l for l in lines if 'MODIFIES' in l]
    touches_runtime = False
    if mods:
        named = set(re.findall(r'\b([A-Z]\w*)\.\$', mods[0]))
        named |= set(re.findall(r'\b(?:Executor|ZIDETOOLS)\.([A-Za-z_]\w*)', mods[0]))
        touches_runtime = bool(named & RUNTIME)

    # --- the ROAD declaration ----------------------------------------------
    # touches_runtime asks "does this name a runtime CLASS". The manual road
    # exists for a narrower reason: a method that is in the RUNNING STACK
    # cannot be rebuilt underneath itself. Class membership is a proxy for
    # that, and a coarse one. The author may say so explicitly.
    road = [l for l in lines if re.match(r'\s*#\s*ROAD:', l)]
    road_ordinary = False
    if road:
        r = road[0]
        mr = re.match(r'\s*#\s*ROAD:\s*(ordinary|manual)\b(.*)$', r, re.I)
        if not mr:
            probs.append("ROAD line present but unreadable — the form is "
                         "'# ROAD: ordinary — <reason>' or '# ROAD: manual'")
        else:
            road_ordinary = mr.group(1).lower() == 'ordinary'
            reason = mr.group(2).strip(' \t-—:')
            if road_ordinary:
                if len(reason) < 20:
                    probs.append(
                        "ROAD: ordinary needs a REASON, and a real one — it "
                        "overrides the runtime-class rule, so it says why the "
                        "changed method is not in the running stack")
                elif not touches_runtime:
                    probs.append(
                        "NOTE ROAD: ordinary declared but MODIFIES names no "
                        "runtime class — the declaration overrides nothing "
                        "and can go")
    # The DEMAND for a self-jump depends on MODIFIES.  Its CORRECTNESS does not:
    # a read-only probe declares MODIFIES: nothing and still carries the
    # prologue, and a wrong line number sends the run into the middle of the
    # script -- so the number is checked whenever a prologue is there.
    # The other direction is a NOTE, not a failure: a script that changes no
    # runtime class does not need the manual road, and giving it one takes it
    # OUT of the vessel -- past the seatbelt, past the manifest and past the
    # verdict. A note, because there may be good reasons to run something by
    # hand that
    # this check cannot see, and a blade that goes red without cause gets
    # switched off.
    ops = [(k, l) for k, l in enumerate(lines) if l.strip()
           and not l.strip().startswith('#')]
    first = ops[0][1].strip() if ops else ''
    m = re.match(r"Do Executor\.\$classes\.Executor\.\$methods\.//\$execute//"
                 r"\.\$modify\((\d+)\)", first)
    if (touches_runtime and not road_ordinary) or m:
        if not ops:
            probs.append("script has no operative lines")
        else:
            if not m:
                probs.append("rebuilds runtime classes but the first operative line is "
                             "not the self-jump: Do Executor.$classes.Executor.$methods."
                             "//$execute//.$modify(<N>) ## Jump to start point")
            else:
                declared = int(m.group(1))
                if len(ops) < 2 or not ops[1][1].strip().startswith('Quit all methods'):
                    probs.append("self-jump is not followed by 'Quit all methods'")
                marker = [k for k, l in enumerate(lines, 1) if 'Start from here' in l]
                if not marker:
                    probs.append("no start marker line ('# <------ Start from here !')")
                else:
                    want = marker[0] + 1
                    while want <= len(lines) and not lines[want-1].strip():
                        want += 1
                    if declared != want:
                        probs.append(f"self-jump targets line {declared} but the start "
                                     f"marker puts the first operative line at {want}")
                if m and not touches_runtime:
                    probs.append(
                        "NOTE carries a self-jump but MODIFIES names no runtime "
                        "class -- the manual road runs OUTSIDE the vessel, so "
                        "the backup, the manifest and the verdict are skipped. "
                        "Intended? If not, drop the three prologue lines")
                if m and road_ordinary:
                    probs.append(
                        "declares 'ROAD: ordinary' and carries a self-jump — "
                        "the two say opposite things. The self-jump wins in "
                        "Omnis, so the declaration is the lie: drop one")

    # --- 6 free-the-class prologue for every MODIFIED class -----------------
    mods = [l for l in lines if 'MODIFIES' in l]
    if mods:
        named = set(re.findall(r'\b(?:Executor|ZIDETOOLS)\.([A-Za-z_]\w*)', mods[0]))
        named |= set(re.findall(r'\b([A-Z]\w*)\.\$', mods[0]))
        skip = {'Executor', 'ZIDETOOLS', 'Executor_Backups'}
        for cls in sorted(named - skip):
            # Accept a library-qualified form. The plain name resolves in the
            # CURRENT library, which is right only while script and target
            # share one; across libraries 'Close design Tool' would close the
            # wrong Tool. Both are accepted; which one is correct depends on
            # where the script runs, and the blade cannot know that.
            if not re.search(r'Close design\s+(?:[A-Za-z_]\w*\.)?' + re.escape(cls) + r'\b', text):
                probs.append(f"MODIFIES names class '{cls}' but no "
                             f"'Close design {cls}' (or 'Close design "
                             f"<Lib>.{cls}') in the prologue")

    # --- 4 run stamp in the protocol (docstring rule 4) ---------------------
    if not re.search(r"Calculate\s+result\s+as\s+con\('run(?: manually)?\s+',#T", text):
        probs.append("protocol does not open with a run stamp: "
                     "Calculate result as con('run ',#T,...), or "
                     "con('run manually ',#T,...) on the manual road (A7)")

    # --- 7 '##' glued to a non-space char ----------------------------------
    for i, l in enumerate(lines, 1):
        for m in re.finditer(r'##(\S)', l):
            if m.group(1) in '#\'"),=':
                continue
            probs.append(f"line {i}: '##{m.group(1)}' — Omnis inserts a space "
                         f"('## {m.group(1)}'), the tag never survives; "
                         f"use a single '#' marker")
            break

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
        probs = check(name, text)
        # Findings prefixed NOTE are informational and do not fail the file --
        # same convention as the other blades.
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
            print(f"     .. {p}")
    print(f"\n{len(files)-bad}/{len(files)} headers valid")
    return 0 if bad == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
