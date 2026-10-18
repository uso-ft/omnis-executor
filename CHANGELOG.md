# _Changelog - version history of Executor.lbs

Format: keepachangelog.com. Versions: semver.org (MAJOR.MINOR.PATCH, pre-release suffix in beta).
Newest first. Collect every change under Unreleased; on a release rename that heading to
the version and the date, raise Startup_Task.$version() and start a new Unreleased.
Sections per version: Added, Changed, Fixed, Removed, Known issues.
The build number is separate and automatic: library $userinfo, EXEC-BUILD=.


## Unreleased


## 1.0.0 - 2026-10-18


### Added

- The donation link (Stripe), shown in About and returned by Startup_Task.$donateLink().
- Version check: a script names the Executor version it was written for, in its header (RUNS-IN: EXECUTOR 1.0) and after the start of its jump block marker. A newer major version asks before a run and is reported once on a jump; a newer minor version, or one that cannot be read, writes a trace line. A script without a version runs as before.

### Changed

- Break if error is off in the factory settings.
- The execution log shows the verdict of each run in a column of its own, and scrolls sideways.
- Example 1 opens the method editor on each method while it builds: its lines are seen arriving.

### Fixed

- A row loaded from the log kept the selection and scroll position of the script before; it now opens at the top, cursor at the start.
- Clear emptied the last row of the log, even a row that had run; it now clears only an open draft row.
- After a jump, a click on a view radio could switch the radio but not the view; each radio now sets its view itself.

## 1.0.0-beta.2 - 2026-10-05


### Added

- Copy lines in the jump block: a line '# Copy' with a label and a payload copies the payload on a double-click and jumps nowhere.
- Shift-double-click on a jump line, or the button Show of the jump view, selects its line in the script.
- Jump links reach every class type, objects without a name by their ident ($objs.1017), and attributes: an attribute opens the Property Manager of its item.
- Break text on the console (Break if error): with a text, a run breaks only on an error whose code, text, line or location contains it.
- Donate-ware notice: Startup_Task._Donate, $donateLink() and $projectLink(), a SUPPORT block in $construct; About shows the donation link first.
- The run tour, in English and German: two rows in the log of a new installation, the English one in the editor on the first open. Execute on it changes nothing and says how to take the tour.

### Changed

- The vault a run opened for its backups is closed again at the end of the run. A vault opened by hand before the run stays open.
- A jump to a class or to its $methods opens its first method; toolbars, remote forms and remote menus opened their design before.
- A jump link that cannot open says why in the trace log, then rings the bell.
- Error handler: ignore list with code@text conditions (25216 is ignored only on lines that write method text). Ignored errors appear in the error log as rows 'ignored' and are not counted.
- The trace log carries the location of an error.
- Script parsing: the target analysis no longer resolves every token against every class of every open library (29 s -> 0.6 s).
- Snippets are kept in the folder execSnippets beside the library (was Executor_Settings/CodeSnippets).
- Target and source fields, the log and the title show a path short: Lib.Class, then the rest as given. The long forms are still read.
- Factory settings: the Script view, no automatic switch to the Jump view, every pane folded.
- The console opens with the cursor at the start of the script; the script is no longer selected.
- On the first start of a fresh copy (no settings stored yet) the console shows itself, with the run tour in the editor. Later it opens from the menu only.

### Fixed

- A jump to an object that is not there reports it instead of opening the first object of the class.
- A class name in another case (Lib.$classes.startup_task) is found.
- Target analysis: a library-first path ending in a call or a property (Lib.$classes.X.$userinfo.$assign(...)) gave the library as target.
- The notation browser opens at the current target or source when the field holds Lib.Class.
- A source picked in the notation browser is resolved quietly, like the target.
- The scratch library execScratch is opened, or created, when the console opens; nothing called it before, so a new installation had none.
- Executor.$execute is set to one neutral comment line when the console opens and when it closes: a script line naming a library that is no longer open broke the JSON export of Executor.
- A log stored without settings is loaded (a release copy ships the run tour that way).
- The execution log drew a row empty when its script was very long (about 40 000 characters); the Code column now shows the start of the script only.

### Removed

- The startup opener for Executor_Backups.lbs, a vault name no longer in use.


## 1.0.0-beta.1 - 2026-09-26


### Added

- Console with script editor, three views (Script, Split, Jump), result, trace and snippets.
- Contract for scripts: fixed signature and closed variable set v1.3 (Executor.$execute).
- Before a run: danger scan, target analysis, editors of the target classes closed.
- Backup of the target classes into the vaults execBackups/execBackup_<Library>.lbs, restore, structural seal.
- Execution log with header declaration, verdict, build number, manifest and run folder.
- Jump links with clipboard payload for line-level changes.
- Buttons Custom 1 and Custom 2 for your own code.
- Start guard, _Changelog and _License (MIT).

### Known issues

- ExecutorStore grows with the log, and every backup copies it.
- The run folders in execRuns are never cleaned.
