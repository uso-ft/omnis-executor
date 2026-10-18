#!/usr/bin/env python3
"""
Table builder -- makes the lookup tables of the blades from YOUR Omnis help.

Usage:
  python3 build_tables.py --help-root <dir> [--out <dir>] [--legacy]

  --help-root   the unpacked help folder: the one holding `commands`,
                `functions` and `notation` (inside omnis_HELP.zip: `omnis`).
  --out         where the tables are written; default: beside this script,
                which is where the blades look for them.
  --legacy      rebuild the tables exactly as they were made before 1.0.0
                (for comparison only; see below).

Writes:
  omnis_command_table.txt    one command per line, as the help titles it
  omnis_constants_table.txt  one constant per line
  omnis_error_table.txt      kerr constant <TAB> description
  omnis_reserved_table.txt   the thirteen $-names custom notation may not use
  functions.txt              one function name per line

Where each table comes from
---------------------------
Commands   The title of every command page, `commands/groups/<group>/*.htm`.
Constants  Two sources, united:
           1. the first cell of every row on the constants pages,
              `notation/root/constants/*.htm` -- the documented list;
           2. every `kName` in the text of the whole help that is not a
              family prefix: the help writes `kJSTabs... constants` for a
              family, and `kJSTabs` is not a constant. Some components
              document their constants only in examples (`kGRpie`).
           A name with an underscore (`kUniTypeISO8859_1`) and a name with a
           lower-case family (`kcursArrow`, `kerrNotFound`) are included.
Errors     The rows of `notation/root/constants/error_codes.htm`.
Reserved   NOT in the help. Omnis Programming, chapter 3 ("custom notation")
           lists thirteen $-names a custom method may not take; they are
           fixed data in this script.
Functions  The title of every function page, `functions/groups/<group>/*.htm`,
           where it reads `name()`. Static functions of a group
           (`FileOps.$deletefile()`) are notation, not functions, and are
           left to the notation vocabulary.

--legacy
--------
Before 1.0.0 the commands, constants and errors were made the same way but
the constants by one regular expression over the help text only. That missed
every constant with an underscore and every lower-case family, and took family
prefixes for constants. `functions.txt` was the union of file names and every
`word(` in the function pages, prose words included. `--legacy` makes those
tables again, byte for byte, so the builder can be proven against them.
"""
import argparse, glob, html, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

RESERVED = ['$add', '$assign', '$canassign', '$chaincount', '$default',
            '$findname', '$ident', '$isinherited', '$makelist', '$name',
            '$ref', '$serialize', '$wind']

RE_TAG = re.compile(r'<[^>]+>')
RE_TITLE = re.compile(r'<title>(.*?)</title>', re.S)
RE_ROW_FIRST = re.compile(r'<tr><td>([^<]+)</td>')
RE_ROW_PAIR = re.compile(r'<tr><td>([^<]+)</td><td>(.*?)</td></tr>', re.S)
RE_CONST_TEXT = re.compile(r'(?<![\w$.])(k[A-Z0-9]\w*|k[a-z]+[A-Z]\w*)')
RE_CONST_LEGACY = re.compile(r'\bk[A-Z0-9][A-Za-z0-9]*\b')
RE_FUNC_TITLE = re.compile(r'([A-Za-z_]\w*)\(\)')
RE_FUNC_LEGACY = re.compile(r'\b([A-Za-z_]\w*)\s*\(')


def read(path):
    return open(path, encoding='utf-8', errors='replace').read()


def text_of(page):
    return html.unescape(RE_TAG.sub(' ', page))


def title_of(page):
    m = RE_TITLE.search(page)
    return html.unescape(m.group(1)).strip() if m else None


def all_pages(root):
    return sorted(glob.glob(os.path.join(root, '**', '*.htm'), recursive=True))


def commands(root):
    out = set()
    for f in glob.glob(os.path.join(root, 'commands', 'groups', '*', '*.htm')):
        t = title_of(read(f))
        if t:
            out.add(t)
    return sorted(out)


def constants(root):
    documented = set()
    for f in glob.glob(os.path.join(root, 'notation', 'root', 'constants', '*.htm')):
        for m in RE_ROW_FIRST.finditer(read(f)):
            documented.add(html.unescape(m.group(1)).strip())
    in_text = set()
    for f in all_pages(root):
        t = text_of(read(f))
        for m in RE_CONST_TEXT.finditer(t):
            name = m.group(1)
            if name.endswith('_'):
                continue                      # `kUniTypeISO8859_n` in prose
            if t.startswith('...', m.end()):
                continue                      # `kJSTabs... constants`: a family
            in_text.add(name)
    return sorted(documented | in_text), sorted(in_text - documented)


def constants_legacy(root):
    out = set()
    for f in all_pages(root):
        out.update(RE_CONST_LEGACY.findall(text_of(read(f))))
    return sorted(out)


def errors(root):
    page = read(os.path.join(root, 'notation', 'root', 'constants', 'error_codes.htm'))
    rows = {}
    for a, b in RE_ROW_PAIR.findall(page):
        rows[html.unescape(a).strip()] = html.unescape(RE_TAG.sub('', b)).strip()
    return [f'{k}\t{rows[k]}' for k in sorted(rows, key=str.lower)]


def functions(root):
    out = set()
    for f in glob.glob(os.path.join(root, 'functions', 'groups', '*', '*.htm')):
        t = title_of(read(f)) or ''
        m = RE_FUNC_TITLE.fullmatch(t)
        if m:
            out.add(m.group(1))
    return sorted(out)


def functions_legacy(root):
    out = set()
    for f in glob.glob(os.path.join(root, 'functions', '**', '*.htm'), recursive=True):
        out.add(os.path.splitext(os.path.basename(f))[0])
        out.update(RE_FUNC_LEGACY.findall(text_of(read(f))))
    return sorted(out)


def write(outdir, name, lines, newline_at_end):
    body = '\n'.join(lines) + ('\n' if newline_at_end else '')
    with open(os.path.join(outdir, name), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(body)
    print(f'  {name:28} {len(lines):5} entries')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--help-root', required=True)
    ap.add_argument('--out', default=HERE)
    ap.add_argument('--legacy', action='store_true')
    a = ap.parse_args()

    root = a.help_root
    if not os.path.isdir(os.path.join(root, 'commands')):
        sub = os.path.join(root, 'omnis')
        if os.path.isdir(os.path.join(sub, 'commands')):
            root = sub
        else:
            print(f'NOT A HELP FOLDER: {a.help_root} holds no `commands` folder')
            return 2
    os.makedirs(a.out, exist_ok=True)
    print(f'help: {root}, {len(all_pages(root))} pages')

    if a.legacy:
        write(a.out, 'omnis_command_table.txt', commands(root), False)
        write(a.out, 'omnis_constants_table.txt', constants_legacy(root), False)
        write(a.out, 'omnis_error_table.txt', errors(root), False)
        write(a.out, 'omnis_reserved_table.txt', RESERVED, True)
        write(a.out, 'functions.txt', functions_legacy(root), False)
        return 0

    consts, only_text = constants(root)
    write(a.out, 'omnis_command_table.txt', commands(root), True)
    write(a.out, 'omnis_constants_table.txt', consts, True)
    write(a.out, 'omnis_error_table.txt', errors(root), True)
    write(a.out, 'omnis_reserved_table.txt', RESERVED, True)
    write(a.out, 'functions.txt', functions(root), True)
    if only_text:
        print(f'\n  {len(only_text)} constant(s) found only in help TEXT, not on a constants page'
              f' -- check them if one looks like a typo of the help:')
        print('  ' + ' '.join(only_text))
    return 0


if __name__ == '__main__':
    sys.exit(main())
