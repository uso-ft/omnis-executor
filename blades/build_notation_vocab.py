#!/usr/bin/env python3
"""
Vocabulary builder for check_notation.py -- run once per Omnis version, and
again when your library has grown.

Usage:
  python3 build_notation_vocab.py --help-root <dir> [--export <dir> ...]
                                  [--out notation_vocab.json]

  --help-root   the unpacked Omnis help: the folder holding `commands`,
                `functions` and `notation` (inside omnis_HELP.zip: `omnis`).
  --export      the JSON export of one of YOUR libraries, the folder holding
                its class folders. May be given more than once.
  --out         default: notation_vocab.json beside this script, where the
                blades look for it.

What it makes
-------------
One flat vocabulary the blades load in milliseconds, so the help tree does
not have to be present at check time.

  help_member   a `$token` the help documents as a MEMBER of an item -- a row
                of a properties or methods table, an anchor, a syntax line.
  help_mention  a `$token` the help mentions anywhere else in its text.
  functions     the Omnis functions: the title of every function page that
                reads `name()`.
  function_groups  the owners of static functions: `FileOps`, `OJSON` ...
                `FileOps.$deletefile(...)` names no variable.
  command_words the lower-case words of the command syntax lines (`as`, `to`,
                `step` ...), minus the function names. `Calculate x as (a+b)`
                is not a call of `as(`.
  seen_in       `$token` -> the libraries whose CODE uses it (string literals
                and comments masked). Usage is evidence of use, not of
                existence: a library's own method looks exactly like notation
                at a call site, and a typo that sits in shipped code is still
                a typo. `check_notation` reports a token known only from here
                as a NOTE, never as clean help notation.

The four help trees are read together on purpose: `FileOps.$deletefile`
lives in `functions`, not in `notation`, and concluding from absence in one
tree is how it was once reported as invented.
"""
import argparse, glob, html, json, os, re, sys

# structured markup -> the token is a documented MEMBER of some item
MEMBER_PATS = [
    re.compile(r'<td>\s*(\$[A-Za-z_]\w*)\s*</td>'),        # table cell = the name
    re.compile(r'>\s*(\$[A-Za-z_]\w*)\s*</a>'),            # cross-reference anchor
    re.compile(r'<td>\s*(\$[A-Za-z_]\w*)\s*\('),           # cell opening a signature
    re.compile(r'<title>[^<]*?(\$[A-Za-z_]\w*)'),          # <title>FileOps.$deletefile()
    re.compile(r'<h1>[^<]*?(\$[A-Za-z_]\w*)'),             # <h1>FileOps.$deletefile()
    re.compile(r'<b>[^<]*?(\$[A-Za-z_]\w*)\s*</b>\s*\('),  # Syntax: <b>...$x</b>(
]
RE_TAG = re.compile(r'<[^>]+>')
RE_TITLE = re.compile(r'<title>(.*?)</title>', re.S)
RE_FUNC_TITLE = re.compile(r'([A-Za-z_]\w*)\(\)')
RE_GROUP_TITLE = re.compile(r'([A-Za-z_]\w*)\.\$\w+\(\)')
RE_TOKEN = re.compile(r'(\$[A-Za-z_]\w*)')
RE_LITERAL = re.compile(r"'[^']*'|\"[^\"]*\"")
HERE = os.path.dirname(os.path.abspath(__file__))


def read(path):
    return open(path, encoding='utf-8', errors='replace').read()


def scan_help(root):
    member, mention, files = set(), set(), 0
    for f in glob.glob(os.path.join(root, '**', '*.htm'), recursive=True):
        files += 1
        t = read(f)
        for p in MEMBER_PATS:
            member.update(m.group(1) for m in p.finditer(t))
        mention.update(RE_TOKEN.findall(html.unescape(RE_TAG.sub(' ', t))))
    return member, mention | member, files


def scan_functions(root):
    """-> (functions, function groups). The functions are the same list
    build_tables.py writes to functions.txt; the groups are the owners of the
    static functions, `FileOps` in `FileOps.$deletefile()`."""
    out, groups = set(), set()
    for f in glob.glob(os.path.join(root, 'functions', 'groups', '*', '*.htm')):
        m = RE_TITLE.search(read(f))
        t = html.unescape(m.group(1)).strip() if m else ''
        mm = RE_FUNC_TITLE.fullmatch(t)
        if mm:
            out.add(mm.group(1))
        mm = RE_GROUP_TITLE.fullmatch(t)
        if mm:
            groups.add(mm.group(1))
    return out, groups


def scan_command_words(root):
    """Lower-case words of the command SYNTAX lines, placeholders left out:
    `as`, `to`, `from`, `step` ... `Calculate x as (a+b)` puts `as` right
    before a bracket, and check_notation must not read it as a function."""
    out = set()
    for f in glob.glob(os.path.join(root, 'commands', 'groups', '*', '*.htm')):
        m = re.search(r'<h2>Syntax</h2>(.*?)<h2>', read(f), re.S)
        if not m:
            continue
        s = re.sub(r'<div class="omsc_variable">.*?</div>', ' ', m.group(1), flags=re.S)
        out.update(re.findall(r'\b[a-z][a-z0-9]*\b', html.unescape(RE_TAG.sub(' ', s))))
    return out


def code_tokens(line):
    """$tokens of one method line: comment lines skipped, literals and a
    trailing ## comment masked."""
    s = line.strip()
    if not s or s.startswith('#') or s.startswith(';'):
        return []
    s = RE_LITERAL.sub("''", s)
    i = s.find('##')
    if i >= 0:
        s = s[:i]
    return RE_TOKEN.findall(s)


def scan_export(root):
    """-> (library name, set of $tokens used in its code)"""
    lib = os.path.basename(os.path.normpath(root))
    p = os.path.join(root, 'library.json')
    if os.path.isfile(p):
        try:
            lib = json.load(open(p, encoding='utf-8')).get('name') or lib
        except (ValueError, AttributeError):
            pass
    toks = set()
    files = 0
    for f in glob.glob(os.path.join(root, '**', '*.omh'), recursive=True):
        files += 1
        for line in read(f).replace('\r\n', '\n').replace('\r', '\n').split('\n'):
            toks.update(code_tokens(line))
    return lib, toks, files


def help_version(root):
    """'10.22' from the title of the help's index page ('Omnis Studio 10.22
    Documentation'); '?' when the page does not say."""
    p = os.path.join(root, 'index.htm')
    m = re.search(r'Omnis Studio (\d+(?:\.\d+)+)', read(p)) if os.path.isfile(p) else None
    return m.group(1) if m else '?'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--help-root', required=True)
    ap.add_argument('--export', action='append', default=[])
    ap.add_argument('--out', default=os.path.join(HERE, 'notation_vocab.json'))
    a = ap.parse_args()

    root = a.help_root
    if not os.path.isdir(os.path.join(root, 'commands')) and \
            os.path.isdir(os.path.join(root, 'omnis', 'commands')):
        root = os.path.join(root, 'omnis')
    if not os.path.isdir(os.path.join(root, 'notation')):
        print(f'NOT A HELP FOLDER: {a.help_root} holds no `notation` folder')
        return 2

    version = help_version(root)
    member, mention, nfiles = scan_help(root)
    print(f'help: {nfiles} htm, {len(member)} member tokens, {len(mention)} mentioned')
    functions, groups = scan_functions(root)
    print(f'functions: {len(functions)}, function groups: {len(groups)}')
    command_words = scan_command_words(root) - functions
    print(f'command words: {len(command_words)}')

    seen, libs = {}, []
    for p in a.export:
        if not os.path.isdir(p):
            print(f'NOT A FOLDER: --export {p}')
            return 2
        lib, toks, nomh = scan_export(p)
        libs.append(lib)
        for t in toks:
            seen.setdefault(t, set()).add(lib)
        print(f'export {lib}: {nomh} method files, {len(toks)} distinct tokens')
    if not a.export:
        print('NOTE no --export given: tokens your own code uses are not in the vocabulary')

    vocab = {
        'built_from': {'help_version': version, 'help_files': nfiles,
                       'exports': libs},
        'command_words': sorted(command_words),
        'function_groups': sorted(groups),
        'functions': sorted(functions),
        'help_member': sorted(member),
        'help_mention': sorted(mention - member),
        'seen_in': {t: sorted(l) for t, l in sorted(seen.items())},
    }
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(vocab, fh, indent=0, sort_keys=True)
    only_code = {t for t in seen if t not in mention}
    print(f'\nwrote {a.out}: {len(mention | set(seen))} distinct tokens, '
          f'{len(only_code)} of them known only from your code '
          f'({os.path.getsize(a.out)//1024} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
