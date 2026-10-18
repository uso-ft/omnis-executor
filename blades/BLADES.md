# BLADES — checks a script passes before it is run

The blades are small Python programs that read an Executor script as text and report what would go wrong in Omnis before anyone presses Execute: an unknown command, function, constant or notation token; a variable outside the closed set of `Executor.$execute`; a literal that never closes; an `If` without its `End If`; a header that does not match the run stamp; a jump line that points at nothing. Every script the Executor shipped with went through them.

They are a floor, not a verdict. A clean result says the text is well-formed against the Omnis help and the library. It does not say that the script does what it should — that is what reading it, the danger scan, the backup and the verdict of the run are for.

Python 3, no packages. Written by an AI (Claude, by Anthropic), like the rest of the Executor.

---

## Run them

```
python3 check_all.py --export <export> <script.txt>
```

- `<export>` is the **JSON export of the library the script runs against**: the folder holding its class folders (or the folder above it). Without it the library's own methods read as invented and the jump lines are not checked.
- When a script builds on what an earlier script made, export again after that run. Example 2 of the Executor only passes against an export of `execScratch` taken after example 1.
- Run them on the file **as it will be delivered** — not on pieces of it.

The first line of the output names what the vocabulary was built from:

```
vocabulary: Omnis help 10.22 (1904 pages), library exports: none
```

Then one block per blade, and the last line is the verdict: `CLEAN`, or `PROBLEMS FOUND -- do not deliver`.

| Prefix | Meaning |
|---|---|
| `->` | a failure: the script must be changed |
| `..` | a NOTE: read it, it does not fail the script |
| `NOTE` | something a blade did NOT check, and why |

Read the notes, not only the verdict.

---

## What is in the folder

| File | What it is |
|---|---|
| `check_all.py` | the runner: every blade on every file, one verdict |
| `check_*.py` | the fifteen blades, one rule family each; the docstring at the top of each says what it checks and what it cannot see |
| `check_signatures.py` | call sites against parameter counts, over a whole export: `python3 check_signatures.py <export> [script.txt]` (not part of `check_all`) |
| `probe_neg_*.txt` | the negative probes: each holds lines a blade MUST reject |
| `omnis_command_table.txt`, `omnis_constants_table.txt`, `omnis_reserved_table.txt`, `omnis_error_table.txt`, `functions.txt` | name lists from the Omnis help |
| `notation_vocab.json` | the notation tokens of the Omnis help, for `check_notation` |
| `vars_executor_v12_types.txt` | the variables of `Executor.$execute`, name TAB type — the closed set of `CONTRACT.md` §1.2. Do not edit |
| `build_tables.py`, `build_notation_vocab.py` | build the name lists and the vocabulary from YOUR Omnis help |
| `build_commands_functions.py` | lists the commands, functions and constants a library actually uses |

A missing data file stops `check_all` before the first blade: a rule that did not run is never reported as passed.

---

## Name lists and your Omnis version

The name lists and the vocabulary that come with the blades were built from the help of **Omnis Studio 10.22**. They hold names only — no text of the help. For another version, build your own from the help folder of your installation (where it is: `README.md`, "The Omnis help"):

```
python3 build_tables.py         --help-root <help folder>
python3 build_notation_vocab.py --help-root <help folder> [--export <library export> ...]
```

Both write beside themselves and replace the shipped files.

`--export` teaches the vocabulary the methods your own libraries define and call. Without it, a script that calls a method of a library you did not pass fails with `exists in NO source ... or a method of another library`. Pass the libraries your scripts call into; a token known only from library code is then reported as a NOTE, not a failure.

---

## Test the blades themselves

```
python3 check_all.py --selftest --export <the JSON export of Executor 1.0.0>
```

Runs every probe and compares what each blade found with what it must find, blade by blade. A probe that hits less means a rule was lost; one that hits more means a rule changed. Then it runs `check_danger.py --selftest`. Ends in `PASSED` or `n FAILED`.

Run it after changing a blade, and after rebuilding the name lists for another Omnis version — a new version may name things differently. The probes that check jump lines and generated bodies need the Executor's own export (the folder `src/` of the repository).

---

## For an AI writing scripts

- **With code execution:** unpack the blades, run `check_all.py` on the delivered file against the export the user gave you, and deliver only on `CLEAN`. Say which notes you saw and why they are harmless. A script that fails a blade is changed, not explained.
- **Without code execution:** you cannot run them. Say so in the delivery, so the user runs them before Execute.
- What the blades cannot judge: whether a property belongs on that object, whether the arguments are right, whether the logic holds. That needs reading.

---

Copyright (c) 2026 Udo Sonnabend (USO-FT). This text: CC BY 4.0. The blades and builders: MIT License. Source: https://github.com/uso-ft/omnis-executor
