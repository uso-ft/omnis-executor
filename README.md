# Executor for Omnis Studio

**AI-assisted code changes for Omnis Studio, with a human in between.**

The Executor is an interface between an AI (or another developer) and your Omnis libraries. It fixes one method signature and a closed set of variables. A script written against that surface is plain text: it carries no library, no classes and no version assumptions. You paste it into the console, read it, and run it. The Executor backs up what the script declares it will change, runs it, measures what really changed, and writes one log row that says whether the two agree.

Unlike an import of files, a script runs inside Omnis: it looks at what is there, builds on it, starts it, and every run is measured.

Version `1.0.0` · 2026-10-18 · MIT License (code) · CC BY 4.0 (texts) · Donate-ware

**▶ Demo video (10 minutes, no audio, subtitles): https://odysee.com/@uso-ft:8/omnis-executor:d**

The video hands the AI three files; it was made before the blades shipped. What an AI should get in full is listed in step 1 of [How you work with it](#how-you-work-with-it).

---

## Donate-ware

The Executor is free. The licenses grant every right, with or without a donation. If it saves you time or work, please consider supporting its development:

**https://donate.stripe.com/28EaEXg2E8SN1RR2RfeUU00**

Contact: uso-ft@sonnabend.ch · Project page: https://github.com/uso-ft/omnis-executor

---

## Caution — read this first

- The Executor **changes classes** of the libraries it is pointed at: methods, variables, objects and properties. **Read every script before you run it.**
- Before a run, the classes a script declares are copied into a vault. Restore from there.
- Point it at copies of your libraries, or keep them under version control (for example a JSON export in Git): a vault holds one backup per class, the state before the last run that changed it — not a history. No warranty: see `LICENSE`.
- **Do not kill the stack while stepping through a run** (option Step): end it with Continue. A killed run never reaches its commit: no manifest, no verdict, and the class it may already have changed is not saved. Its vault backup stays on hold until the next run, which finishes it the safe way by bringing back the older copy — so the vault then does not hold the state from just before the killed run.
- The Executor adds a line `EXEC-BUILD=…` to `$userinfo` of every library a run changes. Other content of `$userinfo` is kept.
- **`execRuns/` and the execution log hold your own code:** every script and its protocol. A protocol you attach to a bug report or paste into a conversation shares that code.
- Some functions call IDE libraries (marked `@IDE` in the code) or Omnis core tool methods via `$dotoolmethod` (marked `@CORE`); some add methods to instances at runtime (`@SELF`). Future Omnis versions may change their behaviour.

## Requirements

- Omnis Studio 10.22 (tested: Build 31896 on macOS, Build 32066 on Windows, 64 bit).
- macOS (tested: 10.14.6 Mojave) or Windows (tested: Windows 10 Enterprise). Other platforms are untested.

## Installation

1. Put `Executor.lbs` into a folder of its own. **Keep the file name** `Executor.lbs`: scripts address the library as `Executor.`
2. Open it in Omnis. It stops at once with a message and a Breakpoint: this is the **start guard**. Open `Startup_Task.$construct`, read the CAUTION block, and comment out the four guard lines at the top.
3. Close and open the library again. On this first start the console shows itself, with factory settings, in the Script view, with the **run tour** in the editor. Later it stays in the background until you open it: menu **Executor → Console**.

Beside the library, the Executor and its scripts create:

| Item | Made by | Holds |
|---|---|---|
| `execScratch.lbs` | the console, whenever it opens | a scratch library for trying things out |
| `execSnippets/` | the console | the scripts you keep and run again (snippets) |
| `execInput/<script>/` | the script that reads it, on its first run | what that script reads: you lay the files in, the script never changes them |
| `execExports/` | scripts that write files (example 1) | what scripts write |
| `execRuns/` | every run | the archive: one folder per run with `script.txt` and `protocol.txt` (never cleaned) |
| `execBackups/` | the backup before a run | the vaults, one library per source library: `execBackup_<Library>.lbs` |
| `execRelease/` | a release build (`scripts/tools/`) | the release output |

## How you work with it

The Executor is one half of a round trip. The AI writes, you read and decide, the Executor runs and reports, and the report goes back to the AI. It never runs anything by itself: a human decides at every step, not an agent acting on its own.

1. **Give the AI what it needs.** `CONTRACT.md` at the start of every conversation; `OMNIS_LORE.md` and `OMNIS_IDIOMS.md` when its scripts write Omnis notation (the lore holds measured Omnis behaviour the help does not warn about); the **Omnis help** of YOUR version (see below); a **JSON export** of the library it is to work on, so it knows the real class and method names and the line numbers; and, if it can run code, the folder `blades/` as a zip. Close the console before you export (see Known issues).
2. **Say what you want.** The AI writes a script: a header that declares what it will change, the code, its own read-back checks, and jump links to the places it touches.
3. **Read it, then run it.** Paste it into the console, set the target if the script is generic, press **Execute**. The danger scan warns before the first line runs; the backup is taken before it, too.
4. **Hand the result back.** With **Copy Result to Clipboard** on (the factory setting), the result is already on the clipboard when the run ends: paste it into the conversation. The AI reads its own checks and the verdict, and writes the next step or the fix.
5. **Export again after a larger change**, and give the AI the new export, so that names and line numbers still fit.

**The Omnis help** is the AI's best source for commands, functions and notation. Zip the help folder of your installation and give it to the AI as `omnis_HELP.zip`: on macOS `Omnis Studio <version>.app/Contents/MacOS/idehelp/omnis`, on Windows `C:\Program Files\Omnis Software\OS <version>\idehelp\omnis` (for Omnis 10.22: `OS 10.22 31896`). (The folder `jsidehelp` beside it is the subset for code that runs in the JavaScript client.) Every user zips his own licensed copy. No text of the Omnis help is shipped with the Executor; the blades (below) carry lists of names built from the help of Omnis 10.22, and build them anew from yours.

**The blades — checks before step 3.** In development every script went through a set of checks before it was run, and they ship with 1.0 in the folder `blades/`: Python programs (Python 3, no packages) that read a script as text and test it against the Omnis help and the JSON export — commands, functions, constants and notation known, variables in the closed set, literals closed, blocks balanced, header, run stamp and jump links well-formed. An AI that can run code runs them before it delivers; otherwise you run them: `python3 check_all.py --export <export> <script.txt>`. They come with name lists from the help of Omnis 10.22 and rebuild them from the help of your own version. How to run and read them: `blades/BLADES.md`. A clean result is a floor, not a verdict: the danger scan, the backup, the verdict and your own reading still decide.

**The Executor was built this way itself.** Apart from the layout of the console and the object class `Tool`, its code came from scripts written by an AI (Claude, by Anthropic): each one read by the developer before it ran, then run in the Executor, backed up and measured. The developer decided, tested and corrected.

## The run tour and the examples

A new installation explains itself. Its log holds five rows, none of them run yet:

- **The run tour**, in English and in German; the English one stands in the editor when the console first opens. It changes nothing. Switch to the **Jump** view and double-click the stations 01 to 34, one after the other: each opens the method editor at the line it is about, and its note stands in the Jump view. Press **Execute** on the tour, and it runs the very road it describes.
- **Three examples** (English), meant to be run in order, all on one window in the scratch library. Example 1 builds a real tool: a window that lists the Omnis libraries of a folder and makes their JSON export — the very material an AI works from. Example 2 changes the open window, and only the window, not its class: something to play with, and a look at itself. A button makes the changes permanent — outside a run, so without backup and verdict. Example 3 removes the class, and measures first: it counts what the Permanent button wrote into the class outside any run, closes every open window of the class and removes it. The backup of this run keeps the class as it was, Permanent included — the Vaults window brings it back.

In the repository the scripts lie in `scripts/`:

| Folder | Holds |
|---|---|
| `scripts/tour/` | the run tour, English and German |
| `scripts/examples/` | the three examples |
| `scripts/tools/` | scripts for your own libraries |

Each script says in its own comment block what it does.

## A first run

1. Menu **Executor → Console**.
2. Paste a script into the editor. Set the target (a library, class or object) if the script is generic; a specific script names its own target.
3. Read it. Then **Execute**.
4. Read the result and the new log row: verdict, errors, backups.

A script needs nothing but Omnis code: no header, no declaration, no setup. Paste a method body, press Execute, and it runs through without a question — the only dialog is the danger warning, and only when **Warn on danger** is on. At the end, one message shows the result. We still recommend the header: the backup takes the classes it names even where the code does not name them, and the verdict compares it with what really changed. An AI that has `CONTRACT.md` writes it anyway.

## What happens in a run

The script is written into the method `Executor.$execute` **line by line**, so a line Omnis refuses is reported by number instead of silently missing. A **danger scan** reads it: stage A finds a class chosen at runtime that is removed or overwritten, stage B a named class that is removed, or a class chosen at runtime that is changed otherwise. With **Warn on danger** on (the factory setting), stage A opens a dialog that can cancel the run, and stage B does too when **Backup before run** is off — a seatbelt against accidents, not a lock against intent. Open design editors of the classes involved are closed, and with **Backup before run** on (the factory setting), every class the script names, every class its header declares and the target class are **backed up** into the vault.

The script then runs in a **fresh instance** of an empty object class. Afterwards the changed classes are saved, and a snapshot of every class of every open library is compared with the one taken before: the **manifest** of what really changed. The header is compared with the manifest, and the run gets its **verdict**:

| Verdict | Meaning |
|---|---|
| `ok` | everything declared was seen, nothing else changed |
| `unproven` | nothing else changed, but a declared change was not seen |
| `extra` | a change the header did not declare |
| `conflict` | a change, although the header said `nothing` |
| `open` | the script has no header, so there is nothing to judge |

Last, the build number of each changed library is raised by one and kept as `EXEC-BUILD=` in its `$userinfo`, the backups are committed against the manifest (a class that did not change keeps its previous backup), `script.txt` and `protocol.txt` are written into the run folder, and a log row is sealed. The details are in `CONTRACT.md`; the run tour shows each step in the code.

## What a script can reach

Omnis writes Omnis. Omnis can look at itself and change itself while it runs. Through the notation, a script reads and writes the classes of any open library — the Executor's own included — the way the Omnis IDE does: it adds, renames and deletes classes, writes methods and their text, declares variables, adds objects and sets their properties. It reaches running instances as well: which windows are open, where the user has moved them, what their fields hold. So a script can look at the current state first and build on what it finds, rather than on what it assumes. In most mainstream languages a code generator works on source files and does not see the running program; Omnis, like Smalltalk or Lisp, keeps classes and their instances in one tree a script can walk.

Where it stops: properties Omnis only lets you read, things the notation does not expose, and method text that does not compile (the Executor reports such a line by number). Some roads exist only through IDE libraries or `$dotoolmethod`; the Executor marks the places where it takes them. `OMNIS_LORE.md` records what was measured, including the surprises.

## Writing scripts

The rules are in **`CONTRACT.md`**. In short:

- A script uses **only** the fixed variable set of `Executor.$execute` (two parameters, `targetRef` and `sourceRef`, and 45 locals). More names go into the row `vars`.
- A script is either **specific** (it sets its own target in its first lines) or **generic** (it works on whatever the target field names).
- A script opens with a **header** that declares what it creates, modifies and removes, as `Lib.Class`. The verdict is measured against it. Its line `# RUNS-IN: EXECUTOR 1.0` names the Executor version the script was written for; the console checks it softly (`MANUAL.md`, section 6).
- A script writes its protocol, including its own read-back checks, into `result` and ends with `Quit method result`.
- A script reads its input files from `execInput/<script>/` beside the library and never changes them. Of the Executor's tool methods it uses only the public one, `tools.$collectObjects`.
- A script may lay its own files into its run folder, beside `script.txt` and `protocol.txt`, through the object `env`; it names each file in its result.
- A script may end with a block of **jump links** (`## ===== JUMP LINKS 1.0 =====`, the version after the fixed start of the marker). A double-click in the Jump view opens the method at the line, the variable or the object named there. A jump line can also carry a small text payload after `#>`, which is copied to the clipboard on the double-click: this is how line-level changes are delivered for pasting by hand. A line `# Copy ## label #> text` carries a payload and no target: the double-click copies the text and jumps nowhere. Shift-double-click on a jump line selects that line in the script.

## Restoring

Window **Vaults** (menu Executor) lists the backups and restores a class from them. A vault holds one backup per class: the state before the last run that changed it.

## The console

What each part does, button by button, is in **`MANUAL.md`**.

- Three views: **Script**, **Split**, **Jump**.
- Result, trace and error log; the log keeps every run, and a row shows its own values.
- Snippets, find, markers.
- Buttons **Custom 1** and **Custom 2**: empty, for your own code.
- Settings: menu Executor → Settings.

## Known issues

- Tested on macOS 10.14.6 with Omnis Studio 10.22 Build 31896, and on Windows 10 Enterprise with Build 32066. The Executor was built on macOS.
- The execution log is kept inside the library (class `ExecutorStore`) and grows; every backup of that class copies it.
- The run folders in `execRuns/` are never cleaned.
- **JSON export with the console open:** the console writes each script into `Executor.$execute` and sets that method back to one neutral line when it opens and when it closes. A script line naming a library that has been closed since cannot be assigned again: the JSON export reports it and leaves the class `Executor` out. Close the console before a JSON export.
- **Omnis Studio 11** reopens at start the libraries that were open at shutdown. If that reopens a copy of the Executor whose start guard is still armed, set `openStartupTaskWhenRestoringOpenLibrary` (or `restoreOpenLibsAtStartup`) to false in the `ide` section of `config.json`.

## Changing the Executor itself

The Executor can change classes that are running while it runs. To change the Executor itself, work on a **copy** of the library under another name.

## Removing the Executor

There is no remove script in 1.0. Close the console and the library `Executor`, then delete by hand what lies beside it:

- `Executor.lbs`
- `execScratch.lbs`, `execSnippets/`, `execInput/`, `execExports/`, `execRuns/`, `execBackups/`, `execRelease/` — those that exist.

`execBackups/` holds the vaults, the only backups of the runs: keep it as long as you may want to restore a class. The lines `EXEC-BUILD=…` stay in `$userinfo` of the libraries a run changed.

## Feedback

Criticism, suggestions and bug reports are welcome: by mail to uso-ft@sonnabend.ch, or as an issue on the project page. A bug report helps most with:

- the protocol of the run (it is on the clipboard after the run) and the script;
- your Omnis Studio version, with its build;
- your platform: operating system and its version.

The protocol holds your code (see Caution).

## License

Copyright (c) 2026 Udo Sonnabend (USO-FT).

- **Code** — `Executor.lbs`, its JSON export, the scripts in `scripts/` (run tour, examples, tools), and the blades and builders in `blades/`: MIT License. See `LICENSE` (the same text as `Startup_Task._License`).
- **Texts** — this README, `MANUAL.md`, `CONTRACT.md`, `OMNIS_LORE.md`, `OMNIS_IDIOMS.md` and `blades/BLADES.md`: CC BY 4.0. See `LICENSE-docs`. You may share and adapt them, also commercially, if you name the author, link the source and the license, and say what you changed.
- **Code examples in the texts** may also be used under the MIT License, so you can copy them into your methods without an attribution in your code.

The changelog is in `CHANGELOG.md` (the same text as `Startup_Task._Changelog`).
