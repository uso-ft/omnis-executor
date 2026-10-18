#!/usr/bin/env python3
"""
Runner — runs EVERY blade over the given file(s).  One command, so that
forgetting a single blade is not possible.

Usage:  python3 check_all.py [--export <root>] <script.txt> [more.txt ...]
        python3 check_all.py --selftest --export <Executor export>

Why this exists: the blades run on EVERY delivered line, a two-line probe
included. Friction is what makes a check get skipped, so there is exactly one
thing to run and no judgement call about whether a piece of text is big
enough to deserve it.

Before the first script: the data files must lie beside the blades (three
tables, notation_vocab.json, vars_executor_v12_types.txt). A missing one stops
the run -- a rule that did not run is never reported as passed. The first line
of the output names the help and the libraries the vocabulary was built from.

Blades run:
  check_notation.py    always
  check_commands.py    always
  check_constants.py   always
  check_variables.py   always -- every variable against the closed set of
                       vars_executor_v12_types.txt, with the type rules
  check_idempotent.py  always
  check_define.py      always
  check_reserved.py    always -- the names a script INVENTS for a method, a
                       variable definition or a column (a local called `flag`
                       is the keyword for #F).
  check_emitted_vars.py always -- the names that generated body uses, against
                       the variables the TARGET method actually has
  check_emitted.py     always -- the method BODY a script generates, which no
                       other blade reads. Pass --export, or every method of
                       the library reads as invented. A CLEAN script can
                       still generate a body Omnis refuses with no line named.
  check_stamp.py       always -- the header identity and the run stamp must be
                       the same name and the same version
  check_blocks.py      always -- balances If/While/For/Repeat/Switch and the
                       Begin...End blocks. Omnis takes method lines one at a
                       time, so a doubled `If` with one `End If` is not
                       refused at assign time.
  check_danger.py      always -- the danger scan of CONTRACT.md §2, the same
                       rules as ExecutorConsole.$dangerFindings. Reports what
                       the console will ask or note on the run path; a finding
                       is a NOTE and never fails a script.
  check_header.py      only when a header line is present -- a bare probe has
                       no header and must not be failed for lacking one; the
                       absence is reported as a NOTE instead, so a generator
                       that forgot its header still stands out.
  check_jumplinks.py   when the text contains jump links.  Pass --export <root>
                       to enable existence checking against an exported
                       library; without it the blade cannot verify that a
                       class/method/line actually exists and is skipped.

Coverage rule: a script whose header declares MODIFIES
with real content MUST carry a JUMP LINKS block, and every class named in
MODIFIES must appear in at least one jump line.  Touching something without
saying where is a delivery defect, not a matter of taste.

Result rule: a script carrying the self-jumping
prologue runs from the CODE CLASS, started by hand.  There is no vessel frame,
so nothing fills the console's Result field -- `Quit method result` goes into
the void.  Such a script must end with `Copy to clipboard result`, which is
how Executor.$codes.Executor.$execute has always ended.  The full ending is

    Set reference ref3 to $clib.$classes.ExecutorConsole.$insts().$first()
    Do ref3.$setExecutorValues()      ## re-derive title/target/source FIRST
    Do ref3.cResult.$assign(result)
    Do ref3.$saveToLog()
    Copy to clipboard result
    OK message Done {...}

and the long form must ALSO end with an `OK message`: the clipboard copy is
silent, and a hand-started method gives no other sign that it finished. The
short form, `Do ref3.$finishRun(result)`, does all of it, the report included.
"""
import sys, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

ALWAYS = ['check_notation.py', 'check_commands.py', 'check_constants.py',
          'check_variables.py', 'check_idempotent.py',
          'check_define.py', 'check_reserved.py', 'check_emitted.py',
          'check_emitted_vars.py', 'check_blocks.py', 'check_stamp.py',
          'check_danger.py']
HEADER_MARKS = ('# GENERATOR:', '# READER:', '# PROBE:', '# RUNS-IN:')


# What the blades read besides the script. Without one of them a blade would
# skip a rule, so the runner refuses to start rather than report CLEAN.
DATA_FILES = ['omnis_command_table.txt', 'omnis_constants_table.txt',
              'omnis_reserved_table.txt', 'notation_vocab.json',
              'vars_executor_v12_types.txt']


def vocab_line():
    """Which help and which libraries the vocabulary was built from."""
    try:
        import json
        b = json.load(open(blade_path('notation_vocab.json'),
                           encoding='utf-8')).get('built_from', {})
    except (ValueError, OSError, TypeError):
        return "vocabulary: unreadable"
    ex = ', '.join(b.get('exports') or []) or 'none'
    return (f"vocabulary: Omnis help {b.get('help_version', '?')} "
            f"({b.get('help_files', '?')} pages), library exports: {ex}")


def blade_path(name):
    for cand in (os.path.join(HERE, name), name):
        if os.path.isfile(cand):
            return cand
    return None


def run(blade, path, *extra):
    p = blade_path(blade)
    if p is None:
        print(f"--- {blade}: NOT FOUND (skipped)")
        return 0
    print(f"--- {blade}")
    cmd = [sys.executable, p, path] + [e for e in extra if e]
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout or '') + (r.stderr or '')
    print('\n'.join('    ' + l for l in out.rstrip('\n').split('\n')))
    return r.returncode


def modifies_targets(text):
    """Classes named on the MODIFIES line, empty when it says nothing."""
    for l in text.split('\n'):
        if 'MODIFIES' not in l:
            continue
        body = l.split(':', 1)[-1].strip()
        if not body or body.lower().startswith(('nothing', 'runtime', 'targetref')):
            return set()
        named = set(re.findall(r'\b(?:Executor|ZIDETOOLS)\.([A-Za-z_]\w*)', body))
        named |= set(re.findall(r'\b([A-Z]\w*)\.\$', body))
        if not named:
            named = {w for w in re.findall(r'[A-Za-z_]\w*', body)
                     if w not in ('Executor', 'ZIDETOOLS')}
        return named
    return set()


def check_result_delivery(text):
    """A hand-started code-class script must hand its protocol back."""
    if '$methods.//$execute//.$modify(' not in text:
        return []          # runs through the vessel, the frame handles it
    probs = []
    # THE ENDING COMES IN TWO FORMS. $finishRun is one method in the console
    # that writes the log row, stores the result, persists, redraws, copies
    # and reports -- the same ending the vessel road takes. A script that
    # calls it needs nothing else.
    # Only a REAL call counts: a generator that WRITES $finishRun into
    # another method carries the name inside string literals, and a comment
    # naming it is not a call either. Comments out first, then literals.
    bare = '\n'.join(l for l in text.split('\n') if not l.lstrip().startswith('#'))
    bare = re.sub(r"'[^']*'|\"[^\"]*\"", "''", bare)
    if re.search(r'\$finishRun\s*\(', bare):
        if not re.search(r'\$finishRun\s*\(\s*result', bare):
            probs.append("calls $finishRun but not with 'result' -- the "
                         "protocol this script built would not be the one "
                         "recorded")
        return probs

    # The longer ending. $setExecutorValues must run BEFORE the log call: it
    # re-derives title, target and source from the text. Without it the log
    # records the state from the PREVIOUS script.
    m = re.search(r'\$saveToLog', text)
    if m:
        a = text.find('$setExecutorValues')
        b = m.start()
        if a < 0:
            probs.append("calls $saveToLog without $setExecutorValues -- "
                         "the log would record title/target from the previous "
                         "script, not this one")
        elif a > b:
            probs.append("$setExecutorValues comes AFTER $saveToLog -- "
                         "it must run first, it is what derives the title")
    else:
        probs.append("script carries the self-jump prologue but calls neither "
                     "$finishRun nor $saveToLog -- the run leaves no trace "
                     "in the log")
    if re.search(r'\bcResultDisplay\b', text) and not re.search(
            r'#.*cResultDisplay', text):
        probs.append("assigns cResultDisplay -- that variable does not exist; "
                     "the Result field binds on cResult")
    if not re.search(r'\bcResult\.\$assign\(', text):
        probs.append("no 'cResult.$assign(...)' -- the result would not appear "
                     "in the console's Result field")
    if not re.search(r'Copy to clipboard\s+result\b', text):
        probs.append("script carries the self-jump prologue (runs from the CODE "
                     "CLASS, started by hand) but never does 'Copy to clipboard "
                     "result' -- there is no Result field to catch it, the "
                     "protocol is lost")
    if not re.search(r'^\s*OK message\b', text, re.M):
        probs.append("script carries the self-jump prologue but ends without an "
                     "'OK message' -- the clipboard copy is silent, so nothing "
                     "tells the user the method is through")
    return probs


def check_jump_coverage(text):
    """Report missing jump links for everything the header says it changes."""
    probs = []
    targets = modifies_targets(text)
    if not targets:
        return probs
    if 'JUMP LINKS' not in text.upper():
        probs.append("header declares MODIFIES but the script carries NO "
                     "JUMP LINKS block -- every touched place needs a jump line")
        return probs
    block = text.upper().split('JUMP LINKS', 1)[1]
    for cls in sorted(targets):
        if cls.upper() not in block:
            probs.append(f"MODIFIES names '{cls}' but no jump line points at it")
    return probs


# --selftest: what each negative probe MUST produce, blade by blade, as
# hard/soft finding counts ('->' lines / '..' lines). A probe is the blades'
# own test bench: one that hits LESS than this means a rule was lost, one that
# hits MORE means a rule changed -- both are reported. Measured against an
# export of Executor 1.0.0; the probes that check jump lines and generated
# bodies need that export. Changing a blade on purpose means changing its row
# here in the same delivery.
SELFTEST = {
    'probe_neg_arity': 'notation=2/0',
    'probe_neg_assignargs': 'notation=2/0 emitted_vars=0/1',
    'probe_neg_blockbalance': 'variables=5/0 blocks=1/0',
    'probe_neg_braces': 'commands=1/0',
    'probe_neg_cmdform': 'commands=6/0 variables=4/0 blocks=2/0',
    'probe_neg_colsubtype': 'define=2/0 reserved=1/0',
    'probe_neg_constfamily': 'constants=2/0',
    'probe_neg_createdclass': 'notation=1/0 header=0/1 jumplinks=1/0',
    'probe_neg_cresult': 'notation=1/0 stamp=0/1 header=1/1 delivery=3/0',
    'probe_neg_dqcomment': 'notation=1/0 stamp=0/1 header=0/1',
    'probe_neg_emitted': 'emitted=3/0 emitted_vars=0/1',
    'probe_neg_emittedblock': 'emitted=4/0 emitted_vars=1/1',
    'probe_neg_emptyassign': 'idempotent=1/0',
    'probe_neg_funcs': 'notation=1/0 blocks=1/0',
    'probe_neg_jumpform': 'jumplinks=5/0',
    'probe_neg_lineassign': 'emitted_vars=2/2 header=0/2',
    'probe_neg_lvardefs': 'jumplinks=5/0',
    'probe_neg_methname': 'notation=1/0',
    'probe_neg_notation': 'notation=4/1 stamp=0/1 header=0/1',
    'probe_neg_padding': 'notation=1/0',
    'probe_neg_quotes': 'variables=1/0',
    'probe_neg_refcol': 'notation=1/0 define=1/0',
    'probe_neg_reserved': 'reserved=6/0',
    'probe_neg_runsin': 'header=1/0',
    'probe_neg_stamp': 'stamp=1/0 header=0/1',
    'probe_neg_types': 'variables=4/0',
    'probe_neg_unterminated': 'notation=1/0',
    'probe_neg_vardef': 'notation=0/1',
}
# Generic notes that say what a blade did NOT look at; they are not findings.
SELFTEST_IGNORE = ('no header identity', 'no emission chain', 'no emitted body')


def signature(output):
    """check_all output -> 'blade=hard/soft ...' in the order the blades ran."""
    cur, hits = None, {}
    for l in output.split('\n'):
        m = re.match(r'^--- (\S+)', l)
        if m:
            cur = m.group(1)
            continue
        if cur is None:
            continue
        if re.match(r'^\s+-> ', l):
            hits.setdefault(cur, [0, 0])[0] += 1
        elif re.match(r'^\s+\.\. ', l) and not any(x in l for x in SELFTEST_IGNORE):
            hits.setdefault(cur, [0, 0])[1] += 1
    return ' '.join(f"{b.replace('check_', '').replace('.py', '')}={h}/{s}"
                    for b, (h, s) in hits.items())


def selftest(export):
    """Run every probe beside the blades and compare with SELFTEST."""
    if not export or not os.path.isdir(export):
        print("--selftest needs --export <the JSON export of Executor 1.0.0>: "
              "the jump-line and generated-body probes are checked against it")
        return 2
    import glob
    found = {os.path.splitext(os.path.basename(f))[0]: f
             for f in glob.glob(os.path.join(HERE, 'probe_neg_*.txt'))}
    bad = 0
    for name in sorted(set(found) | set(SELFTEST)):
        if name not in found:
            print(f"FAIL {name}: in the table, but the file is missing")
            bad += 1
            continue
        if name not in SELFTEST:
            print(f"FAIL {name}: probe file without an expected row in SELFTEST")
            bad += 1
            continue
        r = subprocess.run([sys.executable, os.path.abspath(__file__),
                            '--export', export, found[name]],
                           capture_output=True, text=True)
        got = signature((r.stdout or '') + (r.stderr or ''))
        if got == SELFTEST[name]:
            print(f"ok   {name}: {got}")
        else:
            bad += 1
            print(f"FAIL {name}\n     expected {SELFTEST[name]}\n     got      {got}")
    d = blade_path('check_danger.py')
    r = subprocess.run([sys.executable, d, '--selftest'], capture_output=True, text=True)
    print('--- check_danger.py --selftest')
    print('\n'.join('    ' + l for l in (r.stdout or '').rstrip('\n').split('\n')))
    if r.returncode != 0:
        bad += 1
    print(f"\n>>> selftest: {'PASSED' if bad == 0 else f'{bad} FAILED -- a blade rule was lost or changed'}")
    return 0 if bad == 0 else 1


def main():
    args = sys.argv[1:]
    export = None
    if '--export' in args:
        i = args.index('--export')
        if i + 1 < len(args):
            export = args[i + 1]
        args = args[:i] + args[i + 2:]
    if '--selftest' in args:
        return selftest(export)
    args = [a for a in args if os.path.isfile(a)]
    if not args:
        print("usage: python3 check_all.py [--export <root>] <script.txt> ...")
        return 2

    missing = [f for f in DATA_FILES if blade_path(f) is None]
    if missing:
        print("BLADES UNUSABLE -- data file(s) missing beside the blades: "
              + ', '.join(missing))
        print("  the four tables: python3 build_tables.py --help-root <help folder>")
        print("  the vocabulary:  python3 build_notation_vocab.py --help-root "
              "<help folder> [--export <library export> ...]")
        return 2
    print(vocab_line())

    worst = 0
    for path in args:
        text = open(path, encoding='utf-8', errors='replace').read()
        print(f"\n=== {os.path.basename(path)} " + "=" * max(4, 56 - len(os.path.basename(path))))

        blades = list(ALWAYS)
        has_header = any(m in text for m in HEADER_MARKS)
        has_ops = any(l.strip() and not l.strip().startswith('#')
                      for l in text.split('\n'))
        if has_header:
            blades.append('check_header.py')
        has_jumps = 'JUMP LINKS' in text.upper()

        rc = 0
        for b in blades:
            # check_notation.py needs the export too: without it the library's
            # OWN methods are unknown to rule 4 and get reported as invented.
            # check_emitted.py hands the export straight on to check_notation
            # for the same reason -- a generated body calls the library's own
            # methods more often than a script does.
            if b in ('check_notation.py', 'check_emitted.py',
                     'check_emitted_vars.py') and export:
                rc = max(rc, run(b, path, '--export', export))
            else:
                rc = max(rc, run(b, path))

        if has_jumps:
            if export:
                rc = max(rc, run('check_jumplinks.py', path, export))
            else:
                print("--- check_jumplinks.py")
                print("    NOTE no --export <root> given -- jump lines were NOT "
                      "verified against a library. Syntax and existence unchecked.")

        cov = check_jump_coverage(text) + check_result_delivery(text)
        if cov:
            print("--- delivery coverage")
            for c in cov:
                print(f"    -> {c}")
            rc = max(rc, 1)

        worst = max(worst, rc)

        if not has_header and has_ops:
            print("--- check_header.py")
            print("    NOTE no header line found -- header blade skipped. "
                  "Fine for a probe; NOT fine for a generator.")

        print(f"\n>>> {os.path.basename(path)}: "
              f"{'CLEAN' if rc == 0 else 'PROBLEMS FOUND -- do not deliver'}")

    return 0 if worst == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
