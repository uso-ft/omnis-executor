#!/usr/bin/env python3
"""
Notation blade -- validates Omnis NOTATION in a script before it is delivered.

Usage:  python3 check_notation.py <script.txt> [more.txt ...]
        python3 check_notation.py -            (read one script from stdin)
        python3 check_notation.py --export <root> <script.txt>
        python3 check_notation.py --vocab <file.json> <script.txt>

VOCABULARY (rule 4)
-------------------
`notation_vocab.json` next to this file, built by `build_notation_vocab.py`
from the Omnis help (all four trees) and, optionally, the code of the
libraries whose JSON export it was given. Pass `--export <root>` as well: the
target library's OWN methods are read from the export, so a method added
yesterday is not reported as invented. Without the vocabulary the blade
refuses to run (BLADE UNUSABLE): a rule that did not run is never reported
as passed.

Lookup is CASE-INSENSITIVE, because Omnis resolves identifiers that way
(`$findname('$DUMMY')` finds `$dummy`). A spelling that differs from the
canonical one is a NOTE, not a failure: it runs, it just does not read like
the rest of the library.

Rules enforced
 0 QUOTES  a string literal that never closes. Omnis refuses the line at
          assign time and names nothing.
 1 DEREF  a navigation step that is navigated THROUGH needs `()`:
          `.$lib.$name`  -> `.$lib().$name`
          EXCEPTION `$cando` / `$canassign`: the whole point of these is to test
          a prefix WITHOUT executing it, so `.$first.$cando` is correct.
          NOT flagged: a terminal attribute read (`pRef.$lib`, `ref.$classtype`)
          -- brackets only when going through.
 2 OBJTYPE  `$objtype` collected into a list via `$makelist` yields a STRING;
          comparing it against a numeric kConst never matches. A NOTE, not a
          failure: transferring or displaying the value is fine.
 3 HASHHASH  `##` glued to a non-space character: Omnis rewrites `##x` to
          `## x`, so such a tag never reaches a parser. Use a single `#`.
 3b PADDING  two or more spaces OUTSIDE a string literal. Omnis normalises
          whitespace between arguments when it stores a method line, so
          `$add('a',      'b')` comes back as `$add('a','b')` and a read-back
          check reports expected/received. Alignment does not survive.
          Padding INSIDE a literal is untouched and stays allowed -- that is
          where formatting belongs (`jst(text,'-22')`).
 3c METHNAME a method addressed BARE after `$methods.`, e.g.
          `$classes.Tool.$methods.$stripComments`. A method name starts with
          `$`, so Omnis reads it as an attribute or a call of the GROUP, not
          as a member lookup -- it tries to RUN the method instead of
          referencing it. Write `$methods.//$stripComments//` or
          `$methods.$findname('$stripComments')`. Members with plain names
          (`$objs.scrEditor`, `$classes.Tool`) are unaffected.
 4 UNKNOWN  a `$token` that exists in NO source at all -- not in the help,
          not in the target library, not in the code the vocabulary was built
          from. That is a typo, an invention, or a method of a library the
          vocabulary does not know, and it is a FAILURE. Measured on the
          Executor library before it was switched on: zero false alarms.
          Weaker evidence is reported but does not fail:
            NOTE undocumented  the token is not in the help and known only
                 from library code. Usage is not evidence of existence: a
                 codebase can ship a typo (`$doesfilexist` for
                 `$doesfileexist` was found in shipped code).
            NOTE spelling      canonical form is spelled differently.
 5 FUNCTION  a lower-case `name(` on an expression line that is no Omnis
          function. There is no str(), for instance.
 6 VARDEF  `$type`/`$subtype`/`$sublen`/`$initval` beside a vardefs group,
          where `$objtype`... is meant. A NOTE.
 7 ARITY  the argument count of the everyday functions (pos, len, mid ...)
          and of `$assign`, which takes exactly one value.

Severity: findings prefixed NOTE are informational and do not fail the file.

Deliberately NOT checked (would produce false positives, and a noisy blade
gets ignored): whether a given attribute exists on a given item, argument
forms, and reference-chain side effects.
"""
import sys, re, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB_DEFAULT = os.path.join(HERE, 'notation_vocab.json')

# navigation steps: going THROUGH one of these to another $attribute needs ()
NAV = ('lib', 'class', 'obj', 'inst', 'method', 'group', 'wind', 'data',
       'first', 'last', 'next', 'prev')
# ... except when the next step only ASKS whether it could be done
NO_EXEC = {'cando', 'canassign'}

RE_DEREF = re.compile(r'\$(' + '|'.join(NAV) + r')\.\$(\w+)')
RE_MAKELIST = re.compile(r'\$makelist\s*\(([^)]*)\)')
RE_HASHHASH = re.compile(r'##(\S)')


def strip_comment(line):
    """Drop a trailing '## ...' comment so notation checks see code only.

    String literals of BOTH quote styles are masked first: a '##' INSIDE a
    literal is text, not a comment. Cutting there would leave everything
    after it unchecked -- a false CLEAN, not a false alarm.
    RE_LITERAL is defined below this function; the name is resolved at call
    time, so the order is fine.
    """
    masked = RE_LITERAL.sub(
        lambda m: "'" + "\x00" * (len(m.group(0)) - 2) + "'", line)
    i = masked.find('##')
    return line if i < 0 else line[:i]


# Both quote styles: Omnis embeds a single quote in "text" without doubling
# it, and spaces inside either kind of literal are kept. Order in the
# alternation does not matter: re scans left to right, so the delimiter that
# opens first wins, and a quote of the other kind inside it is consumed.
RE_LITERAL = re.compile(r"'[^']*'|\"[^\"]*\"")
RE_PADDING = re.compile(r'\S  +\S')
# `$methods.` followed by a bare $-name.  The standard GROUP methods and
# properties are legitimate there and must not be flagged.
GROUP_MEMBERS = {
    # standard group methods
    '$add', '$remove', '$first', '$next', '$count', '$findident', '$findname',
    '$makelist', '$sendall', '$sendallref', '$appendlist', '$insertlist',
    # generic properties, from help notation/misc/generic.htm -- they apply to
    # ANY item including a group, so `$methods.$attributes` is legitimate and
    # not a bare method name
    '$assign', '$ref', '$fullname', '$name', '$group', '$cando', '$canassign',
    '$canomit', '$attcount', '$attributes', '$isinherited', '$default',
    '$desc', '$ident', '$sublen', '$subtype', '$type', '$class', '$lib',
    '$classtype', '$order', '$objtype',
}
RE_METHNAME = re.compile(r'\$methods\.(\$[A-Za-z_]\w*)')

# --- rule 6: the generic property where the object-specific one is meant ----
# A variable definition carries its data type on $objtype / $objsubtype /
# $objsublen / $objinitval, not on $type / $subtype / $sublen / $initval.
# The generic ones exist, so rule 4 has nothing to object to -- $type of a
# var-def is the kind of ITEM, which is a reference. Copying variables with
# $ref.$type turns every one of them into kItemref: the names are right, the
# count is right, and every type is wrong.
# Help: notation/common/item_ivardefs/instvar.htm.
# A NOTE, not a failure: the same words are correct elsewhere, and only the
# nearby $lvardefs / $ivardefs / $cvardefs / $tvardefs makes them suspect.
VARDEF_GROUPS = ('$lvardefs', '$ivardefs', '$cvardefs', '$tvardefs')
VARDEF_WRONG = {'$type': '$objtype', '$subtype': '$objsubtype',
                '$sublen': '$objsublen', '$initval': '$objinitval'}

# --- rule 5: an undocumented FUNCTION name ---------------------------------
# Omnis functions carry no `$`, so rule 4 never looks at them: `str(x)` would
# pass and be rejected by the compiler. The names come from the help,
# harvested by build_notation_vocab.py.
# Only lines that carry an EXPRESSION are scanned, and only calls with
# something inside the brackets -- `ref()` is the dereference form on a
# reference variable, not a function.  A two-word command such as
# `If canceled (No refresh)` is recognised through the command table and left
# alone; without that check it reads as a call to `canceled(`.
EXPR_HEADS = ('Calculate', 'If ', 'Else If', 'While', 'Until', 'Do ',
              'Quit method', 'For ', 'Set reference')
RE_FUNCCALL = re.compile(r'(?<![\w$.])([a-z][a-z0-9_]{1,20})\s*\(\s*(?=[^)\s])')
CMD_TABLE = 'omnis_command_table.txt'


def load_commands():
    for cand in (os.path.join(HERE, CMD_TABLE), CMD_TABLE):
        if os.path.isfile(cand):
            return {l.strip() for l in open(cand, encoding='utf-8',
                                            errors='replace') if l.strip()}
    return set()
# commands whose argument is FREE TEXT, not an expression list: the spacing is
# the message itself and Omnis keeps it (`Send to trace log -  [expr]`).
FREETEXT = (
    'Send to trace log', 'OK message', 'Yes/No message', 'No/Yes message',
    'Working message', 'Prompt for input', 'Breakpoint',
)
RE_TOKEN = re.compile(r'\$[A-Za-z_]\w*')


class Vocab:
    """Every token known from any source, indexed lower-case.

    Case-insensitive on purpose: Omnis resolves identifiers that way, so
    `$SETEXECUTORVALUES` reaches the same method as `$setExecutorValues`.
    The canonical spelling is kept so a drifted spelling can be named.
    """

    def __init__(self):
        self.tier = {}        # lower-case token -> tier name
        self.canon = {}       # lower-case token -> canonical spelling
        self.libs = {}        # lower-case token -> libraries that use it
        self.funcs = set()
        self.cmdwords = set()
        self.loaded = False
        self.sources = []

    # Strongest evidence first; a later, weaker source never demotes a token.
    # `seen`: known only from library code the vocabulary was built from.
    PRIORITY = ['own', 'help', 'seen']

    def _add(self, tok, tier):
        k = tok.lower()
        old = self.tier.get(k)
        if old is None or self.PRIORITY.index(tier) < self.PRIORITY.index(old):
            self.tier[k] = tier
            self.canon[k] = tok

    def load_vocab(self, path):
        if not os.path.isfile(path):
            return False
        v = json.load(open(path, encoding='utf-8'))
        for t in v.get('help_member', []):
            self._add(t, 'help')
        for t in v.get('help_mention', []):
            self._add(t, 'help')
        self.funcs = set(v.get('functions', []))
        self.cmdwords = set(v.get('command_words', []))
        for t, libs in v.get('seen_in', {}).items():
            self._add(t, 'seen')
            self.libs.setdefault(t.lower(), libs)
        self.loaded = True
        self.sources.append(os.path.basename(path))
        return True

    def load_export(self, root):
        """The target library's own methods -- one .omh file per method."""
        n = 0
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                if f.endswith('.omh'):
                    name = f[:-4]
                    self._add(name if name.startswith('$') else '$' + name, 'own')
                    n += 1
        if n:
            self.sources.append(f"{os.path.basename(root.rstrip(os.sep))} "
                                f"({n} methods)")
        return n

    def classify(self, tok):
        """-> (tier, canonical) ; tier None means: found nowhere."""
        k = tok.lower()
        return self.tier.get(k), self.canon.get(k)


def code_only(line):
    """Strip a trailing '## ...' comment AND every string literal.

    A `$token` inside quotes is text, not a call: a call site inside a string
    literal proves nothing.
    Literals are blanked rather than removed so column positions survive.
    """
    masked = RE_LITERAL.sub(lambda m: "'" + "\x00" * (len(m.group(0)) - 2) + "'", line)
    i = masked.find('##')
    if i >= 0:
        line = line[:i]
    return RE_LITERAL.sub(lambda m: "'" + ' ' * (len(m.group(0)) - 2) + "'", line)


COMMANDS = load_commands()


RE_ADDMETHOD = re.compile(r"\$methods\.\$add\s*\(\s*'(\$\w+)'")


def self_created(text):
    """Methods this script creates -- they cannot be in the export yet.

    The `$methods.$add('$name')` literal is the declaration. The header is
    not asked: CREATES names classes only, and a script that adds methods to
    an open INSTANCE creates and modifies no class at all. A use spelled
    differently from the literal is not in the set, so a typo is still caught.
    """
    body = set()
    for line in text.split('\n'):
        for m in RE_ADDMETHOD.finditer(line):
            body.add(m.group(1))
    return body



def unterminated(line):
    """True when a line opens a string literal and never closes it.

    Walks the line once. A quote of either style opens a literal; inside it
    the SAME quote doubled is a literal quote and does not close. Outside a
    literal, '##' starts a comment and the rest is text. A line that is a
    comment from the start is not code and is never judged.
    """
    s = line.strip()
    if s.startswith('#'):
        return False
    i, q = 0, ''
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
            return False
        i += 1
    return bool(q)



def _arg_of(s, start):
    """the text between the bracket at `start` and its match, or None"""
    d = 0
    q = ''
    i = start
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
        elif c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d == 0:
                return s[start + 1:i]
        i += 1
    return None


def _top_commas(s):
    """commas at bracket depth 0, quotes respected"""
    d = 0
    q = ''
    n = 0
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
        elif c in '([':
            d += 1
        elif c in ')]':
            d -= 1
        elif c == ',' and d == 0:
            n += 1
        i += 1
    return n


def assign_arity(code):
    """True when an $assign is handed more than ONE argument.

    The pieces of a generated line passed straight to $assign --
    $text.$assign('a',chr(91),'b') -- where con() has to hold them together.
    Omnis refuses the line and names nothing. Measured on the Executor library
    before the rule was written: no $assign call with more than one argument,
    so the rule has no false alarm to trade against.
    """
    for m in re.finditer(r'\$assign\s*\(', code):
        arg = _arg_of(code, m.end() - 1)
        if arg is None:
            continue
        if _top_commas(arg) > 0:
            return True
    return False


# --- rule 7: argument count of the everyday functions -----------------------
# Rule 5 asks only whether the NAME is a function, so a pos() with four
# arguments passes it. Omnis does not refuse such a call at compile time in
# every case; the extra arguments change nothing or the line fails at run time.
# Only functions whose count is certain are listed, and each was measured on
# the Executor library before the rule was written -- 1,000+ calls, none
# outside the range below:
#   pos 190x2  len 204x1  low 71x1  upp 10x1  left 22x2  right 6x2
#   mid 165x3 65x2  isclear 124x1  isnull 13x1  not 60x1  strtok 13x2
# An EMPTY argument list is not judged (it turned up only where the scanner met
# prose), and variadic functions (con, pick, chr, trim, rxpos) are left alone.
FUNC_ARITY = {'pos': (2, 2), 'len': (1, 1), 'low': (1, 1), 'upp': (1, 1),
              'left': (2, 2), 'right': (2, 2), 'mid': (2, 3), 'isclear': (1, 1),
              'isnull': (1, 1), 'not': (1, 1), 'strtok': (2, 2)}
RE_ARITY = re.compile(r'(?<![\w$.])(' + '|'.join(FUNC_ARITY) + r')\s*\(')


def _literal_spans(s):
    """[(start, end)] of every quoted literal, doubled quotes kept inside"""
    out, q, i, a = [], '', 0, 0
    while i < len(s):
        c = s[i]
        if q:
            if c == q:
                if i + 1 < len(s) and s[i + 1] == q:
                    i += 2
                    continue
                out.append((a, i + 1))
                q = ''
        elif c in ("'", '"'):
            q, a = c, i
        i += 1
    if q:
        out.append((a, len(s)))
    return out


def func_arity(code):
    """[(name, given, (min,max))] for every call outside its certain range"""
    out = []
    lits = _literal_spans(code)
    for m in RE_ARITY.finditer(code):
        # A call INSIDE a literal is emitted text, and its doubled quotes
        # read as empty literals here, so pos('','',x) would count three
        # arguments. check_emitted judges emitted bodies with this same rule
        # after rebuilding them; here it is skipped.
        if any(a <= m.start() < b for a, b in lits):
            continue
        arg = _arg_of(code, m.end() - 1)
        if arg is None or not arg.strip():
            continue
        given = _top_commas(arg) + 1
        lo, hi = FUNC_ARITY[m.group(1)]
        if not lo <= given <= hi:
            out.append((m.group(1), given, (lo, hi)))
    return out


def check(path, text, vocab=None):
    probs = []
    seen = set()
    reported = set()
    lines = text.split('\n')
    if vocab is not None:
        for tok in self_created(text):
            vocab._add(tok, 'own')

    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if line.startswith('#'):
            continue
        code = strip_comment(raw)

        # --- 0 the literal must CLOSE --------------------------------------
        # `If pos('Calculate raw as '''''',t)` carries six quotes where five
        # are needed, so the literal never closes and Omnis refuses the line
        # at assign time. RE_LITERAL ends a literal at the FIRST quote of a
        # doubled pair and cannot count them; unterminated() knows the two
        # rules Omnis has -- a doubled quote inside a literal is one quote,
        # and a `##` outside a literal ends the line.
        for fn, given, (lo, hi) in func_arity(code):
            want = str(lo) if lo == hi else f"{lo} or {hi}"
            probs.append(
                f"line {n}: {fn}() takes {want} argument(s) and this call "
                f"passes {given} -- rxpos() is the one with more (rule 7)")

        if assign_arity(code):
            probs.append(
                f"line {n}: $assign takes exactly ONE value and this call "
                f"passes several -- the pieces need a con() around them "
                f"(Omnis refuses the line and names nothing)")

        if unterminated(raw):
            probs.append(
                f"line {n}: the string literal is never closed -- count the "
                f"quotes. Inside a literal a quote is written twice, so the "
                f"text '' is written as ''''  (Omnis refuses the line, "
                f"silently, at assign time)")

        # --- 1 DEREF -------------------------------------------------------
        for m in RE_DEREF.finditer(code):
            step, nxt = m.group(1), m.group(2)
            if nxt in NO_EXEC:
                continue
            key = (n, step, nxt)
            if key in seen:
                continue
            seen.add(key)
            probs.append(
                f"line {n}: '.${step}.${nxt}' needs the dereference brackets "
                f"-> '.${step}().${nxt}'  (() dereference rule)")

        # --- 2 OBJTYPE in $makelist ---------------------------------------
        for m in RE_MAKELIST.finditer(code):
            inner = m.group(1)
            if '$objtype' in inner and not re.search(r'\$objtype\s*\*\s*1', inner):
                probs.append(
                    f"NOTE line {n}: '$objtype' collected via $makelist arrives as a "
                    f"STRING. Harmless when it is only transferred or displayed; if this "
                    f"column is ever COMPARED against a kConst, force it with '$objtype*1'")

        # --- 3 '##' glued to a non-space char ------------------------------
        for m in RE_HASHHASH.finditer(raw):
            if m.group(1) in "#'\"),=":
                continue
            probs.append(
                f"line {n}: '##{m.group(1)}' -- Omnis inserts a space "
                f"('## {m.group(1)}'), the tag never survives; use a single '#'")
            break

        # --- 3b alignment padding outside a literal -------------------------
        masked = RE_LITERAL.sub(
            lambda mm: "'" + "\x00" * (len(mm.group(0)) - 2) + "'", raw)
        i = masked.find('##')
        if i >= 0:
            masked = masked[:i]
        stripped = masked.lstrip('\t').rstrip()
        if (RE_PADDING.search(stripped)
                and not stripped.startswith(FREETEXT)):
            probs.append(
                f"line {n}: two or more spaces outside a string literal -- "
                f"Omnis normalises them away when it stores the line, and the "
                f"read-back check then reports expected/received")

        # --- 3c method addressed bare after $methods. -----------------------
        for mm in RE_METHNAME.finditer(code_only(raw)):
            if mm.group(1) in GROUP_MEMBERS:
                continue
            probs.append(
                f"line {n}: '$methods.{mm.group(1)}' addresses a method bare -- "
                f"Omnis reads a $-name there as a call on the group and tries "
                f"to RUN it. Write $methods.//{mm.group(1)}// or "
                f"$methods.$findname('{mm.group(1)}')")
            break

        # --- 6 generic property on a variable definition ---------------------
        if any(g in raw for g in VARDEF_GROUPS):
            for wrong, right in VARDEF_WRONG.items():
                if re.search(r'(?<![\w$])' + re.escape(wrong) + r'\b', code_only(raw)):
                    probs.append(
                        f"NOTE line {n}: '{wrong}' beside a vardefs group -- a "
                        f"variable definition carries its data type on "
                        f"'{right}'. '{wrong}' is the generic property of the "
                        f"ITEM and answers about the reference, not the "
                        f"variable")
                    break

        # --- 5 undocumented function name ------------------------------------
        stripped = raw.strip()
        if (vocab is not None and vocab.funcs
                and stripped.startswith(EXPR_HEADS)):
            body = code_only(raw)
            for mm in RE_FUNCCALL.finditer(body):
                word = mm.group(1)
                if word in vocab.funcs or word.lower() in reported:
                    continue
                # `Calculate x as (a+b)`, `For n from (a) to (b)`: a word of
                # the command syntax, followed by a space, is not a call.
                # `lst(` without a space is still judged.
                if word in vocab.cmdwords and body[mm.end(1)].isspace():
                    continue
                # `If canceled (No refresh)` and friends are commands
                two = ' '.join(stripped.split()[:2])
                if two in COMMANDS or stripped.split()[0] in COMMANDS:
                    if stripped.split()[1:2] == [word]:
                        continue
                reported.add(word.lower())
                probs.append(
                    f"line {n}: '{word}(' is not a documented Omnis function. "
                    f"Check the spelling against the help; there is no str(), "
                    f"for instance -- con() and jst() convert on their own")

        # --- 4 UNKNOWN token ------------------------------------------------
        if vocab is not None and vocab.loaded:
            for tok in RE_TOKEN.findall(code_only(raw)):
                if tok.lower() in reported:
                    continue
                tier, canon = vocab.classify(tok)
                if tier is None:
                    reported.add(tok.lower())
                    probs.append(
                        f"line {n}: '{tok}' exists in NO source -- not in the "
                        f"Omnis help, not in this library, not in the code the "
                        f"vocabulary was built from. Typo or invention -- or a "
                        f"method of another library: rebuild the vocabulary "
                        f"with build_notation_vocab.py --export <that library>")
                    continue
                if tier == 'seen':
                    reported.add(tok.lower())
                    src = ','.join(vocab.libs.get(tok.lower(), []))
                    probs.append(
                        f"NOTE line {n}: '{tok}' is undocumented -- known only "
                        f"from {src}. Usage is not evidence of existence: a "
                        f"codebase can ship a typo. Confirm before relying on it")
                elif canon and canon != tok:
                    reported.add(tok.lower())
                    probs.append(
                        f"NOTE line {n}: '{tok}' resolves (Omnis is "
                        f"case-insensitive) but the canonical spelling is "
                        f"'{canon}'")

    return probs


def take_opt(args, flag):
    if flag in args:
        i = args.index(flag)
        val = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
        return val
    return None


def main():
    args = sys.argv[1:]
    vocab_path = take_opt(args, '--vocab') or VOCAB_DEFAULT
    export_root = take_opt(args, '--export')
    own = take_opt(args, '--own')     # methods a generating script adds (check_emitted)

    vocab = Vocab()
    vocab.load_vocab(vocab_path)
    for tok in (own or '').split(','):
        if tok.strip():
            vocab._add(tok.strip(), 'own')
    if export_root:
        if os.path.isdir(export_root):
            vocab.load_export(export_root)
        else:
            print(f"NOTE --export '{export_root}' is not a directory -- "
                  f"the library's own methods were NOT loaded")

    if not args or args[0] == '-':
        files = [('<stdin>', sys.stdin.read())]
    else:
        files = []
        for a in args:
            if os.path.isfile(a):
                files.append((a, open(a, encoding='utf-8', errors='replace').read()))
            else:
                print(f"skip (not a file): {a}")

    if not vocab.loaded:
        # Loud on purpose. A missing vocabulary used to turn rule 4 off with a
        # NOTE and end in "clean" -- a check that did not run, reported as
        # passed.
        print(f"BLADE UNUSABLE: no vocabulary at {vocab_path} -- rule 4 "
              f"(unknown tokens) cannot run. Build it: python3 "
              f"build_notation_vocab.py --help-root <your Omnis help folder>")
        return 2
    if not export_root:
        print("NOTE no --export <root> given -- the library's own methods are "
              "unknown to rule 4; they may be reported as invented")

    bad = 0
    for name, text in files:
        probs = check(name, text, vocab)
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
    vs = f", {len(vocab.tier)} tokens known" if vocab.loaded else ", rule 4 OFF"
    print(f"\n{len(files)-bad}/{len(files)} clean (notation{vs})")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
