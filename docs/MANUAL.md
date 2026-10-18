# Executor — Manual

*This manual was written by an AI (Claude, by Anthropic) from the Executor's code and documents.*

Executor 1.0.0 · Omnis Studio 10.22 · CC BY 4.0

This manual says what each part of the Executor does. What the Executor is, how you work with an AI, and what happens in a run are in `README.md`; the rules for scripts are in `CONTRACT.md`. Most buttons and fields also explain themselves in a tooltip.

---

## 1. The menu

Menu **Executor**:

| Item | Opens |
|---|---|
| **Console** | the console, where scripts are edited and run |
| **Settings...** | markers, fonts and layout (section 10) |
| **Vaults...** | the backups, and restore from them (section 11) |
| **About...** | version, build, licence, project page and donation link |

The console shows itself only on the very first start of a new installation. After that it stays in the background until you open it from the menu.

---

## 2. The console at a glance

From top to bottom:

- **Target, Source, Title** — what the run works on, and the name of its log row (section 4).
- **The script editor** — the text of the script, with the view switch Script / Split / Jump (section 3).
- **The run options and buttons** — Execute and the switches that decide what happens around a run (section 5).
- **The panes** — Result, Trace Log, Error Log, Backup Log and Execution Log, each one can be folded (section 7).

The window title shows the version and the build: `Executor v1.0.0 (build <n>)`.

---

## 3. The script editor

| Element | What it does |
|---|---|
| **Script** / **Split** / **Jump** | Script: the text only. Split: the text above, the jump list below. Jump: the jump list only (section 8). |
| **Automatic View** | On loading from the log or a snippet, the view follows the content: a text without jump links opens in Script, a text that is only jump links in Jump, a mix in Split. Unchecked: only the three buttons change the view. Factory: off. |
| **Horizontal Scrollbox** | No line breaks: every line of the script stays on one line. Factory: off. |
| **A** / **A** (smaller, bigger) | The font size of the text fields and lists. |
| **SLOC / LOC / characters** | Source lines of code, lines of code and characters of the text. |
| **Find** (field, arrows, x) | Searches the script; **in Execution Log** goes on into the log when the script has no more hits. Each pane has its own find bar. |
| **Clear** | Empties the script text. The log row of a run stays; only an open draft row is cleared. |

Pasting a new text over most of the old one counts as a new script: target, source and title are read from it again (with **Overwrite Target/Source/Title automatically** on), and the view follows it (with **Automatic View** on).

---

## 4. Target, Source and Title

| Element | What it does |
|---|---|
| **Target** field | The item the run works on: a library, a class or an object. Written short, `Lib.Class`. A *generic* script works on whatever stands here. |
| **Source** field | A second item, for scripts that copy or compare. |
| **Title** field | The title of the log row and of the run folder. |
| **Target...** / **Source...** | Pick the item in a dialog. |
| **Show** | Opens the target or the source in its editor. |
| **x** | Clears the field. |
| **Overwrite Target/Source/Title automatically** | Target, source and title follow the script text: on leaving the editor, on a paste, on loading. Off: the fields keep what you typed, and the title of the row loaded before stays. Factory: off. |
| **Set Target/Source/Title from text** | Does the same once, by hand. A script that names no target gets a warning. |

A *specific* script names its own target in its first lines; the field then shows that target, and the run takes it from the code.

---

## 5. Running

| Element | What it does |
|---|---|
| **Execute** | Runs the script: assign, danger scan, close editors, backup, run, manifest, verdict, log row. `README.md` describes each step. |
| **Assign to Executor** | Only writes the text into `Executor.$execute` and tests it line by line. Nothing runs. The small check box beside it shows whether the current text is assigned. |
| **Show Executor** | Opens `Executor.$execute` in the method editor. |
| **Backup before run** | Before each run, every class the script names, declares or targets is copied into its vault `execBackup_<Library>`. Factory: on. |
| **Close Target Classes** | Closes open editors of the classes involved before the run: assigning to a class with an open editor is very slow, and an open editor can write an old state back. Factory: on. |
| **Warn on danger** | The danger scan asks before a run that removes or overwrites a class chosen at run time (stage A), and — with Backup before run off — before other dangerous changes (stage B). All findings go into the Error Log either way. Factory: on. |
| **Copy Result to Clipboard** | After each run the result is on the clipboard, ready to hand back to the AI. Factory: on. |
| **Break to step** | Puts a Breakpoint on the first code line, so you can step through the script. End with **Continue**, never by killing the stack: a killed run leaves its backup on hold (README, Caution). |
| **Break if Error** + text field | Stops the run at an error. With the field empty, at every error that is not ignored; with a text, only at errors whose code, text, running line or location contain it (case-insensitive). Factory: off. |

---

## 6. The version check

A script can state the Executor version it was written for, as major.minor:

```
# RUNS-IN: EXECUTOR 1.0
...
## ===== JUMP LINKS 1.0 =====
```

The header line covers the code, the marker covers the jump lines. The console compares them with its own version. The check is deliberately soft: the Executor is a work tool, and the programmer decides.

| The script states | On Execute | On a jump |
|---|---|---|
| nothing (no header, an older form, a marker without a number) | nothing | nothing |
| a version that cannot be read | one line in the Trace Log and in the protocol; the run goes on | one line in the Trace Log, once |
| the same or an older version | nothing | nothing |
| a newer **minor** version (1.5 in a 1.0 console) | one line in the Trace Log and in the protocol; the run goes on | one line in the Trace Log, once |
| a newer **major** version (2.0 in a 1.0 console) | a Yes/No with the bell, **No** as default; after Yes, the same version runs without asking again | an Error Log row, a Trace Log line and the bell, once; the jump goes ahead |

"Once" holds until the script changes as a whole: a log row is loaded, a snippet, or a paste over most of the text.

---

## 7. The panes

Each pane folds open and shut with its title; the title shows how many rows it holds. Each has a find bar.

**Result** — the protocol of the last run: the console's own lines in brackets (`[backup  ]`, `[manifest]`, `[verdict ]` …) and, between them, the script's own `result`. `README.md` and `CONTRACT.md` explain how to read it.

**Trace Log** — notes of the console: the start of a run, a jump that could not open, a version note. **Clear trace log** empties it.

**Error Log** — one row per error of the run. A click shows the call stack below it; a double-click opens the method at the place of the error, and in the stack at that level. Rows of the danger scan and errors the ignore list let through are shown, but do not count as errors of the run.

**Backup Log** — the classes backed up by the run. A double-click opens the class. **Restore Selection...** brings every selected class back from its vault.

**Execution Log** — every run, newest at the bottom. Columns: Date, Title, Target, Verdict, Errors, Backups, Code.

| Element | What it does |
|---|---|
| click on a row | loads that run into the console: script, target, title, result and lists |
| Title column | can be edited in place |
| the four arrow buttons and the drop list | go to the first, previous, next or last run, or pick one |
| marker drop list | sets the marker of the current row; the markers are defined in Settings |
| **Keep in Log** | keeps the current text and its jump links as a row of its own, without running it. Otherwise the next text overwrites the open draft row at the bottom. |
| the delete button | deletes the selected rows, after asking. The open draft row is never deleted. |
| find **in all log fields** | searches every column of the log |

The log lives inside the library (class `ExecutorStore`), and every run folder in `execRuns/` holds `script.txt` and `protocol.txt` as plain files.

---

## 8. The jump view

A script may end with a block of jump links (`CONTRACT.md`, section 4). The Jump and Split views show it as a list: one row per link, with its note.

| Action | What it does |
|---|---|
| single click | selects the row |
| **double-click** | opens the target: a method at a line, a class, its design, an object, a variable (the variable pane of its kind opens; the variable itself is not selected), or an attribute (the Property Manager opens; find the attribute there yourself, it may be on another tab). A link that cannot open says why in the Trace Log and rings the bell. |
| **Shift**-double-click, or **Show** | selects the line of that link in the script |
| a row with a payload (`#>`) | the double-click also copies the payload to the clipboard: jump, select the lines the note names, paste |
| a **Copy** row | copies its payload and opens nothing |
| a row `=== … ===` | a heading, nothing to open |

| Option | What it does |
|---|---|
| **Fix jump line** | every row has the same height. Off: each row fits its text. Factory: off. Sometimes the rows lose their fit to the text; clicking this box twice (on, off) lays them out again. |
| **Fix jump list** | in Split, the list keeps its height while the text changes. Off: it grows with the number of links, up to three quarters of the editor. Factory: off. |

---

## 9. Snippets and Custom buttons

**Load Snippet...** opens a `.txt` file from `execSnippets/` (beside the library) into the editor. **Save to Snippets...** saves the current text there. Snippets are your own collection of scripts and pieces you use again.

**Custom 1** and **Custom 2** are empty buttons for your own code: open the console class and write into their `$event` methods.

---

## 10. The Settings window

Menu **Executor → Settings...**, or the settings button of the console.

| Group | What it does |
|---|---|
| **Markers** | the markers of the Execution Log: icon, id and description. Double-click a row to change its icon; id and description are edited in place. **+** / **-** add or remove a marker at the end. **Save Icons** saves the list — until then every change stays in this window. **Set default icons...** puts back the factory list (after asking; saved only with Save Icons). |
| **Fonts** | **Change Fontstyles...** opens the `#STYLES` system class of the Executor. |
| **Layout** | **Reset Layout to default values** puts every pane and divider back where it started, for when the layout has got out of hand. |
| **Close** | asks first if marker changes are not saved. |

The console's options (section 5) and the panes' state are kept between sessions in `ExecutorStore`.

---

## 11. The Vaults window

Menu **Executor → Vaults...**

A vault is a library `execBackup_<Library>.lbs` in `execBackups/`, beside the Executor. It holds one backup per class: the state before the last run that changed it — not a history.

| Element | What it does |
|---|---|
| upper list | the vaults that are open. Select one or more to list their classes. |
| **Open Library...** | opens another vault from disk |
| lower list | the classes of the selected vaults, with the index entry of each backup. Select one or more. |
| **Filter out #-System classes** | hides the `#` system classes |
| **Restore Selection...** | puts the selected classes back into their library |
| protocol field | what the last restore did |

The Backup Log of the console (section 7) restores the classes of one run the same way.

---

## 12. Files beside the library

| Item | Holds |
|---|---|
| `execScratch.lbs` | a library for trying things, opened or created whenever the console opens |
| `execSnippets/` | your snippets: the scripts you run again (section 9) |
| `execInput/<script>/` | what a script reads; made by that script on its first run, which then lists the files to lay in. The script never changes them. |
| `execExports/` | what scripts write (example 1) |
| `execRuns/` | the archive: one folder per run with `script.txt` and `protocol.txt`, never cleaned |
| `execBackups/` | the vaults (section 11) |
| `execRelease/` | the output of a release build |

Each item appears when something first needs it. `README.md` has the same list under Installation, and under Removing the Executor what to delete.

---

## 13. Clicks at a glance

| Where | Click | Double-click | Shift-double-click |
|---|---|---|---|
| Jump list | select | open the target (and copy the payload) | select the line in the script |
| Execution Log | load the run | — | — |
| Error Log | show the stack | open the place of the error | — |
| Stack | — | open the method at that level | — |
| Backup Log | select | open the class | — |
| Settings, marker list | select | change the icon | — |

---

Copyright (c) 2026 Udo Sonnabend (USO-FT). This text is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Source: https://github.com/uso-ft/omnis-executor
