# The Executor Contract

This is the contract between a script and the Executor. It is written for whoever writes scripts: an AI first, the person who reads and runs them second. Give it to the AI at the start of every conversation.

Everything marked **must** is enforced by the tool, or its result depends on it. Everything else is how to write scripts that work the first time.

Contract for Executor 1.0.0 — 2026-10-18. Tested with Omnis Studio 10.22 on macOS 10.14.6 (Build 31896, 64 bit) and on Windows 10 Enterprise (Build 32066, 64 bit).

Every rule here holds since 1.0; the variable set of §1.2 is part of it. A later version marks what it adds or changes with the version it came in (*since 1.1*).

---

## 1. The interface

### 1.1 What a script is

A script is the body of one Omnis method, `Executor.$execute`. The console writes the text into that method, copies the method into a fresh instance of an empty object class, and runs the copy. A script therefore has exactly the parameters and local variables of `$execute`, and nothing else: no instance variables, no class variables, no state from a previous run.

A script is plain text. It carries no library and no classes of its own, and it makes no assumption about versions beyond what it states.

### 1.2 The variables — a closed set

A script **must** use only these names. There are two parameters and 45 locals.

**Parameters**

| Name | Type | Number |
|---|---|---|
| `targetRef` | kItemref | 1 |
| `sourceRef` | kItemref | 2 |

Both are real references: a write through `targetRef` changes the item it points to.

**Locals** — three of each kind, so values can be swapped without touching anything else:

| Names | Type | Use |
|---|---|---|
| `binary` `binary2` `binary3` | kBinary | `$classdata`, `cdif()` |
| `classRef` `classRef2` `classRef3` | kItemref | |
| `count` `count2` `count3` | kInteger 32 bit | |
| `flag1` `flag2` `flag3` | kBoolean | |
| `group` `group2` `group3` | kItemref | notation groups |
| `list` `list2` `list3` | kList | |
| `methodRef` `methodRef2` `methodRef3` | kItemref | |
| `n` `n2` `n3` | kInteger 32 bit | loop counters |
| `name` `name2` `name3` | kCharacter | |
| `objRef` `objRef2` `objRef3` | kItemref | |
| `ref` `ref2` `ref3` `ref4` | kItemref | the workhorse, four of them |
| `row` `row2` `row3` | kRow | |
| `text` `text2` `text3` | kCharacter | |
| `env` | kObject `Env` | the run folder |
| `files` | kObject `.FileOps.FileOps` | file handling (see §3.9) |
| `tools` | kObject `Tool` | the Executor's tool methods; one is public (below) |
| `result` | kCharacter | **the protocol** (§1.6) |
| `vars` | kRow | the extension surface (§1.3) |

**Types matter as much as names.**

- Every kItemref (`ref`, `classRef`, `group`, `objRef`, `methodRef` and their siblings) is filled with `Set reference`, never with `Calculate`. `group` is a reference to a notation group, not "a group of values".
- `flag1` to `flag3` are kBoolean. A number put into them collapses to YES or NO. Numbers go into `count`, `n` or `result`.

**`tools` — one public method.** Of the methods of `tools`, exactly one is part of this contract:

```
Do tools.$collectObjects(classRef.$ref,list) Returns count
```

It collects every object of a window class (or of one container in it, or of an instance) into `list`, recursively, foreground objects (`$objs`) and background objects (`$bobjs`), and returns the number of rows. `$objs` alone yields only the direct children of one level. The list is defined by the method; its columns:

| Column | Holds |
|---|---|
| `objRef` | a reference to the object |
| `objName` | `$name` |
| `objType` | `$objtype` |
| `level` | nesting depth, 0 = top level |
| `pageNo` | the page or tab number from `$objlink`, 0 if none |
| `isBkgnd` | kTrue for a background object (line, frame, label); those are often nameless |
| `isPreLeaf` | kTrue on a row whose children have no children of their own |
| `objPath` | the dotted path inside the class, `box.page.field` |

Pass only the first two arguments; the other two are the recursion's own. **Every other method of `Tool` is internal**: it may change or disappear in any version, and a script that calls one is written against this library, not against the contract.

### 1.3 More names: `vars`

When the set is not enough, add a column to the row `vars` and give it a name that says what it holds:

```
Do vars.$cols.$add('wrongBefore',kInteger,k32bitint)
Calculate vars.wrongBefore as 0
```

There are deliberately no numbered spares. A named column in `vars` makes the script readable.

### 1.4 The target — specific or generic

A script is one of two kinds.

- **Specific:** it sets its own target in its first code lines, with a fixed path: `Set reference targetRef to MyLib.$classes.MyClass`.
- **Generic:** it never assigns `targetRef` or `sourceRef` and never names a library. It works on whatever the operator puts into the Target and Source fields of the console.

The console decides by the **first occurrence**: the first path the code assigns to `targetRef` is the target. The code is the truth; no comment can contradict it.

There are two short forms, and each has its place:

- **`MyLib.MyClass`** — in the header lines and in commands that take a class: `Close design MyLib.MyClass`, `Save class MyLib.MyClass`. In notation it does not reach the class: Omnis refuses it or resolves only the library.
- **`MyLib.$classes.MyClass…`** — in notation and in the Target and Source fields, for everything below the library: `Set reference ref to MyLib.$classes.MyClass.$methods.//$m//`. Not `$root.$libs.MyLib.$classes…`; `$root.$libs.[name]` only when the library name is computed.

### 1.5 The header — the declaration a run is judged by

A script **must** open with this block:

```
# GENERATOR: <name> v<n> — YYYY-MM-DD HH:MM — <one line: what it does>
# CREATES:  <Lib.Class, ...>   or   nothing
# MODIFIES: <Lib.Class, ...>   or   nothing
# REMOVES:  <Lib.Class, ...>   or   nothing
# RUNS-IN:  EXECUTOR 1.0
```

- The Executor backs up every class named in `CREATES`, `MODIFIES` and `REMOVES` before the run, and afterwards compares the three lines with what really changed (§2).
- **Class names and nothing else**, as `Lib.Class`, separated by commas. No methods (`Lib.Class.$method`), no remarks, and no comma in anything that follows a name. A fragment that is not `Lib.Class` is skipped: that class is not backed up, and the verdict suffers.
- Write `nothing` explicitly. An empty line is not a statement.
- **`RUNS-IN` names the Executor version the script was written for**, major.minor: `EXECUTOR 1.0`. The console compares it with its own version, softly: the programmer decides.

| The script states | On Execute |
|---|---|
| nothing, or the form before 1.0 | nothing |
| the same or an older version | nothing |
| a version that cannot be read, or a newer **minor** | one line in the Trace Log and in the protocol; the run goes on |
| a newer **major** | a No/Yes with the bell, **No** as default; after Yes, that version runs without asking again |

- The GENERATOR line carries date **and** time. When versions follow each other minutes apart, the time is what tells them apart.
- **The GENERATOR name is the script's identity.** It names the file the script is delivered in (`demo_create_v2.txt`) and becomes the title of the log row, and with it the name of the run folder, when the console setting **Overwrite Target/Source/Title automatically** is on, or by **Set Target/Source/Title from text**. Otherwise the Title field keeps what stands in it. A changed script gets a new version and a new time: never deliver a corrected script under its old stamp. The author writes the stamp; a run never rewrites the header.
- **A script kept in a repository drops the version from its file name** (`demo_create.txt`, not `demo_create_v2.txt`): the repository keeps the history, the GENERATOR line the version.
- Keep the header short. Explanations go into a comment block below it.

### 1.6 The protocol — `result`

The first operative line of a script is its **run stamp**, with the same name and version as the GENERATOR line:

```
Calculate result as con('run ',#T,' — <name> v<n>',kCr)
```

Everything the script has to report goes into `result`, one finding per line, and the script ends with:

```
Quit method result
```

`result` is the record: it appears in the Result field and is stored with the log row and in `protocol.txt`. **An empty result is a failure**, not a success: the script did not run, or ran somewhere else. A script does not touch the clipboard; if it must, its header says `MODIFIES: clipboard`.

### 1.7 Layout

Indent block bodies with **three spaces** per level, never tabs. Omnis ignores indentation; it is for the person reading the script before running it.

```
If count=1
   Set reference ref3 to MyLib.$classes.MyWindow
   If isclear(ref3)
      Calculate result as con(result,'class not found',kCr)
   End If
End If
```

Text that a script **writes into a method** is not indented: Omnis derives the levels itself.

### 1.8 Two complete examples, with their real protocols

The two scripts below are the Executor's everyday work in miniature: one **creates** a class, the other **modifies** it, and both measure what they did. Both are idempotent: run a second time, they find nothing to do and say so. Run them in `execScratch.lbs`, the scratch library beside the Executor: the console opens it, or creates it, whenever the console opens, so every reader has it.

The protocols are real runs of exactly these scripts, as the console shows them (Executor 1.0.0, build 66; only the folder path is shortened). The console's own lines carry a tag in brackets; the lines between the blank lines, starting with the run stamp, are the script's `result`. Each script ends with a jump block (§4): optional for the run, and one click to what it touches.

#### Example 1 — create: `demo_create v2`

```
# GENERATOR: demo_create v2 — 2026-10-15 01:40 — creates the code class execDemo with three methods in execScratch
# CREATES:  execScratch.execDemo
# MODIFIES: nothing
# REMOVES:  nothing
# RUNS-IN:  EXECUTOR 1.0
#
# Example 1 of CONTRACT.md. Never overwrites: if execDemo exists already, it does nothing and says so.
# A second run therefore creates nothing, the manifest sees no change, verdict unproven. That is correct.

Calculate result as con('run ',#T,' — demo_create v2',kCr)
Calculate name as 'execScratch.execDemo'

Set reference classRef to execScratch.$classes.$findname('execDemo')
If not(isclear(classRef))
   Calculate result as con(result,name,' exists already - nothing done',kCr)
   Quit method result
End If

# act: the class, then three methods; every returned reference is checked
Set reference classRef to execScratch.$classes.$add(kCode,'execDemo')
If isclear(classRef)
   Calculate result as con(result,'FAILED: ',name,' was not created',kCr)
   Quit method result
End If
Calculate count as 0
Set reference methodRef to classRef.$methods.$add('$demoOne')
Calculate count as count+not(isclear(methodRef))
Set reference methodRef to classRef.$methods.$add('$demoTwo')
Calculate count as count+not(isclear(methodRef))
Set reference methodRef to classRef.$methods.$add('$demoThree')
Calculate count as count+not(isclear(methodRef))

Save class [name]

# measure: over a path resolved afresh, each method by name
Set reference classRef2 to $root.$libs.execScratch.$classes.$findname('execDemo')
Calculate n as 0
If not(isclear(classRef2))
   Set reference group to classRef2.$methods
   Calculate n as not(isclear(group.$findname('$demoOne')))+not(isclear(group.$findname('$demoTwo')))+not(isclear(group.$findname('$demoThree')))
End If
Calculate result as con(result,name,': class ',pick(isclear(classRef2),'there','MISSING'),', methods added ',count,' of 3, read back ',n,' of 3',kCr)
Quit method result

## ===== JUMP LINKS 1.0 =====
# Do execScratch.$classes.execDemo.$methods ## the class and its three methods
```

First run — the class is created:

```
run 01:40 - errors 0

[close   ]   1 class(es) in the text or the Target field (2 mention(s)), 0 editor(s) closed, 2 selected row(s) carried no class name
[backup  ]   the Target field holds a class, but this run reads its target from the text - nothing backed up or saved from it
[backup  ]   3 line(s) in the scan carried no class:
[backup  ]      class not found in any open library outside the vaults
[backup  ]      class name is an expression, not resolvable from text
[backup  ]      class not found, skipped: execScratch.execDemo
[backup  ]   nothing to back up — no target and no class in the text

run 01:40 — demo_create v2
execScratch.execDemo: class there, methods added 3 of 3, read back 3 of 3

[manifest]   1 Classe(s) changed
             added  execScratch.execDemo
             [build  ] execScratch -> 83  2026-10-15_01-40-05
[commit  ]   0 kept, 0 unchanged. 
[build   ]   Executor at 66
[verdict ]   ok

[folder  ]   <startup folder>/execRuns/2026-10-15_01-40-04_demo_create_v2/
```

Second run — nothing to do, and the protocol says so:

```
run 01:40 - errors 0

[close   ]   1 class(es) in the text or the Target field (2 mention(s)), 0 editor(s) closed, 0 selected row(s) carried no class name
[backup  ]   the Target field holds a class, but this run reads its target from the text - nothing backed up or saved from it
[backup  ]   backupClass: execDemo -> execBackup_execScratch, seal OK (m 3, v 0, o 0, om 0, b 0), saved [YES], no net was needed, the target name was free. folder saved [YES]. vault was CLOSED - opened now. held [execDemo] as [execDemo_prev]. 
[backup  ]   1 line(s) in the scan carried no class:
[backup  ]      class name is an expression, not resolvable from text

run 01:40 — demo_create v2
execScratch.execDemo exists already - nothing done

[manifest]   0 Classe(s) changed
[commit  ]   0 kept, 1 unchanged - previous vault copy back. execScratch.execDemo; 
[build   ]   Executor at 66
[vault   ]   execBackup_execScratch closed again: this run opened it
[unproven]   execdemo - declared, and the manifest did not see it
[verdict ]   unproven

[folder  ]   <startup folder>/execRuns/2026-10-15_01-40-17_demo_create_v2/
```

#### Example 2 — modify: `demo_stamp v2`

```
# GENERATOR: demo_stamp v2 — 2026-10-15 01:40 — stamps a description on every method of execDemo that does not carry the stamp yet
# CREATES:  nothing
# MODIFIES: execScratch.execDemo
# REMOVES:  nothing
# RUNS-IN:  EXECUTOR 1.0
#
# Example 2 of CONTRACT.md. Run demo_create v2 first.
# The class is named once in the code (Set reference targetRef); everything else follows from targetRef.
# Measured: the same question before and after, over all methods; the method count is the control.
# A second run finds nothing to do: before 0, the manifest sees no change, verdict unproven. That is correct.

Calculate result as con('run ',#T,' — demo_stamp v2',kCr)
Set reference targetRef to execScratch.$classes.execDemo
Calculate name2 as targetRef.$lib().$name
Calculate name3 as targetRef.$name
Calculate name as con(name2,'.',name3)
Close design [name]

Calculate text as 'stamped by demo_stamp v2'
Do vars.$cols.$add('total',kInteger,k32bitint)
Do vars.$cols.$add('missingBefore',kInteger,k32bitint)
Do vars.$cols.$add('missingAfter',kInteger,k32bitint)
Calculate vars.total as 0
Calculate vars.missingBefore as 0
Calculate vars.missingAfter as 0

# measure and act: one question, asked of every method
Set reference group to targetRef.$methods
Set reference ref to group.$first()
While not(isclear(ref))
   Calculate vars.total as vars.total+1
   If ref.$desc<>text
      Calculate vars.missingBefore as vars.missingBefore+1
      Do ref.$desc.$assign(text)
   End If
   Set reference ref to group.$next(ref)
End While

Save class [name]

# measure again: the same question, over a path resolved afresh from the names
Set reference group2 to $root.$libs.[name2].$classes.[name3].$methods
Calculate count as 0
Set reference ref2 to group2.$first()
While not(isclear(ref2))
   Calculate count as count+1
   If ref2.$desc<>text
      Calculate vars.missingAfter as vars.missingAfter+1
   End If
   Set reference ref2 to group2.$next(ref2)
End While

Calculate result as con(result,name,': ',vars.total,' method(s), without the stamp before ',vars.missingBefore,', after ',vars.missingAfter,kCr)
If count<>vars.total
   Calculate result as con(result,'CONTROL FAILED: ',count,' method(s) read back, ',vars.total,' before',kCr)
End If
Quit method result

## ===== JUMP LINKS 1.0 =====
# Do execScratch.$classes.execDemo.$methods ## the methods this script stamps
```

First run — three methods stamped:

```
run 01:41 - errors 0

[close   ]   1 class(es) in the text or the Target field (1 mention(s)), 0 editor(s) closed, 0 selected row(s) carried no class name
[backup  ]   the Target field holds a class, but this run reads its target from the text - nothing backed up or saved from it
[backup  ]   backupClass: execDemo -> execBackup_execScratch, seal OK (m 3, v 0, o 0, om 0, b 0), saved [YES], no net was needed, the target name was free. folder saved [YES]. vault was CLOSED - opened now. held [execDemo] as [execDemo_prev]. 
[backup  ]   3 line(s) in the scan carried no class:
[backup  ]      class name is an expression, not resolvable from text
[backup  ]      class name is an expression, not resolvable from text
[backup  ]      class reached by an expression, not resolvable from text

run 01:41 — demo_stamp v2
execScratch.execDemo: 3 method(s), without the stamp before 3, after 0

[manifest]   1 Classe(s) changed
             changed  execScratch.execDemo
             [build  ] execScratch -> 84  2026-10-15_01-41-14
[commit  ]   1 kept, 0 unchanged. kept execScratch.execDemo; 
[build   ]   Executor at 66
[vault   ]   execBackup_execScratch closed again: this run opened it
[verdict ]   ok

[folder  ]   <startup folder>/execRuns/2026-10-15_01-41-13_demo_stamp_v2/
```

Second run — nothing to do:

```
run 01:41 - errors 0

[close   ]   1 class(es) in the text or the Target field (1 mention(s)), 0 editor(s) closed, 0 selected row(s) carried no class name
[backup  ]   the Target field holds a class, but this run reads its target from the text - nothing backed up or saved from it
[backup  ]   backupClass: execDemo -> execBackup_execScratch, seal OK (m 3, v 0, o 0, om 0, b 0), saved [YES], no net was needed, the target name was free. folder saved [YES]. vault was CLOSED - opened now. held [execDemo] as [execDemo_prev]. 
[backup  ]   3 line(s) in the scan carried no class:
[backup  ]      class name is an expression, not resolvable from text
[backup  ]      class name is an expression, not resolvable from text
[backup  ]      class reached by an expression, not resolvable from text

run 01:41 — demo_stamp v2
execScratch.execDemo: 3 method(s), without the stamp before 0, after 0

[manifest]   0 Classe(s) changed
[commit  ]   0 kept, 1 unchanged - previous vault copy back. execScratch.execDemo; 
[build   ]   Executor at 66
[vault   ]   execBackup_execScratch closed again: this run opened it
[unproven]   execdemo - declared, and the manifest did not see it
[verdict ]   unproven

[folder  ]   <startup folder>/execRuns/2026-10-15_01-41-27_demo_stamp_v2/
```

#### Reading a protocol

- **`run 01:40 - errors 0`** — start time, and the Omnis errors counted during the run.
- **`[close]`** — the classes the console found in the text and in the Target field, and how many of their design editors it closed. "Selected rows without a class name" are open windows that edit no class (the Property Manager, for example); the number depends on your screen, not on the script.
- **`[backup]`** — what went into the vault. `vault was CLOSED - opened now` means the run opened the vault for its backup. `held [execDemo] as [execDemo_prev]` means the previous vault copy was set aside until the commit decides. The lines "carried no class" are places where the text scan could not name a class: a class that does not exist yet (example 1, first run), and every **computed name** — `Close design [name]`, `Save class [name]`, `$root.$libs.[name2]…`. The console reads only the literal text; it cannot evaluate an expression before the run. That is the price of naming the class once and computing the rest, and the reason the header must name every class literally.
- **The script's own lines** — from the run stamp to the blank line. This is `result`, and the only part the script writes.
- **`[manifest]`** — what really changed: `added`, `changed` or `removed`. The indented `[build]` line under it is the build number of the changed library (§2, step 8).
- **`[commit]`** — the vault's decision per held copy: `kept` (the class changed, the fresh copy stays) or `unchanged` (it did not, the previous copy comes back).
- **`[build]`** — the build of the Executor itself.
- **`[vault]`** — a vault this run opened is closed again at its end. A vault opened by hand before the run stays open.
- **`[verdict]`** — the header compared with the manifest (§2). A line like `[unproven]` before it names the class that caused the verdict.
- **`[folder]`** — the run folder with `script.txt` and `protocol.txt`.

**Why `unproven` is correct in the second runs.** The header declares a change; the run made none, because there was nothing left to do. The Executor cannot know that "nothing to do" was the intended outcome — it only sees that a declared change did not happen, and says so instead of claiming success. The script's own line tells the reader why. Read both together: the verdict says what the tool measured, the script's protocol says what the script found.

---

## 2. What happens around a script

The header matters because the Executor checks it. On Execute, the console:

1. writes the text into `Executor.$execute`, line by line, and reports the first line Omnis refuses;
2. runs a **danger scan** over the assigned method: a class chosen at runtime that is removed or overwritten opens a dialog; a named class removed, or a generic one changed otherwise, is a note in the error log;
3. closes open design editors of the classes the code names;
4. **backs up** every class of the header, and the target class, into a vault beside the library;
5. takes a snapshot of every class of every open library, runs the script in a fresh instance, saves the named classes, and takes a second snapshot. The difference is the **manifest**: what really changed;
6. compares header and manifest, the **verdict**: `ok` (all declared seen, nothing else), `unproven` (something declared was not seen), `extra` (a change not declared), `conflict` (a change although the header says `nothing`), `open` (no header);
7. keeps the fresh backup of a class that changed, and the previous one of a class that did not;
8. adds `EXEC-BUILD=<n> <stamp>` to `$userinfo` of every library that changed;
9. writes `script.txt` and `protocol.txt` into a run folder and seals a log row.

What follows for the script:

- **Declare every class you change.** An undeclared change reads `extra` or `conflict`. A declared class that did not change reads `unproven`: the line was refused, the change had no effect, or the class was not saved.
- **Close what you modify.** Put `Close design Lib.Class` near the top for every class in `MODIFIES`. The console closes editors of classes named in the code, but not of classes named only in the header. An open editor makes a rebuild very slow and can write an old state back.
- **Save what you change.** End with `Save class Lib.Class` for every class changed through notation. Notation changes live in memory until saved; the snapshot compares dates on disk, so an unsaved change is invisible, and a hard kill loses it.
- **Name the library in the text.** The console reads the script as text before it runs, and finds a class only where it stands literally: `Lib.$classes.Class…` in a code line, `Close design Lib.Class`, `Lib.Class` in the header. A class reached only through a variable (`ref2.$classes.$findname('Tool')`) cannot be seen before the run; a bare class name that exists in two open libraries is reported as ambiguous and is not backed up. A class that is changed but neither named in the code nor in the Target field is invisible to the manifest.
- **Do not change the running Executor.** A method that is on the call stack while the script runs cannot be rebuilt safely. To change the Executor itself, work on a copy of the library under another name.

---

## 3. Laws for writing

Omnis is reflexive: code can read and change classes, methods, variables and objects, and many of the traps below are silent. Each law was paid for.

### 3.1 Measure, do not assert

A script reports what is the case afterwards, read back over a path that is not the one it wrote through. It does not report what it intended. A loop that prints its own counter prints the same number whether or not anything worked.

The test before delivery: *what would this result say if the change had not worked?* If the answer is "the same", it is not a measurement.

1. **Measure before.** "31 changed" means nothing without knowing how many were wrong to begin with. On a second run the before-count must be zero.
2. **Act.**
3. **Measure after**, over a freshly resolved path, not through the reference that did the writing.

Where it fits, add a **control**: something that must not have changed. Keep measurement values in `vars` under speaking names. Compare, do not only count: "17 of 17" once reported a copy in which every type was wrong.

- **Count results, not attempts.** A loop that counts its own `$assign` calls reports them whether they took or not, and an assignment through a reference that has died does nothing and says nothing. Collect the items again afterwards and ask each one.
- **Every label names the condition beside it.** `pick()` is zero-based, and a label phrased the other way round inverts without a sound. If `isclear` is in the `pick`, the label says "missing" or "gone": `pick(isclear(classRef2),'there','MISSING')`.
- **A NULL slips through `<>`.** `If a<>b` is never true when one side is NULL, so the failure branch is skipped and a NULL passes as equal; `|isnull(a)` does not help. Write the equality as the `If` and the failure in `Else` (lore 8.1).

Where a result cannot be read back (a colour on screen), or measuring would cost more than the change, the script says so in its header. An exception that is written down is one the reader can see.

### 3.2 References

- **The reference law.** An argument for a kItemref parameter travels as `.$ref`. The bare name passes the evaluated value (a method item becomes its name), and nothing complains.
- **References are perishable.** After every change to the target, fetch references afresh before using them again.
- **Instance names are not class names.** Omnis names an instance `<classname>_<n>` (`MyWindow_840`), so `$root.$iwindows.$findname('MyWindow')` never finds it: no instance is called that. Use `$findname` with the instance name itself (kept from `$name` when the instance was opened), or walk `$root.$iwindows` and compare the class of each instance.
- **A path into a window's objects** resolves by name on an instance and by tree on a class. On an instance write it short, `$cinst.$objs.myField`, which also finds a field three containers down (if its name is unique in the window). On a class, `MyLib.$windows.W.$objs…`, write every container.

### 3.3 Groups are not lists

`$methods`, `$methodlines`, `$objs`, `$cols`, `$classes`, `$lvardefs`, `$attributes`, `$libs` have `$count`, `$first`/`$next`, `$findname`, `$sendall` — and no `$linecount`, no `$line`. A list property on a group compiles, runs and returns empty.

### 3.4 Brackets and comments in literals

- **Square brackets are evaluated** inside a string literal when the string is built. Build a literal bracket with `chr(91)` and `chr(93)`.
- Text written into a method line must not contain `##` directly followed by a character: Omnis rewrites `##x` to `## x`.

### 3.5 Writing method text

- **A new body is written line by line** with `$methodlines.$add(text)`, checking each returned reference with `isclear()`. A bulk `$methodtext.$assign` only says NO and never which line failed; line by line names the line.
- **An existing body can be rewritten in bulk.** A refused `$methodtext.$assign` is atomic and changes nothing.
- **One existing line** is rewritten in place with `$methodlines.[n].$text.$assign(text)`, which is also atomic. Capture its return flag; do not compare the text read back, because Omnis normalises stored lines.
- There is **no insert** in the middle: only `$add` (at the end), `$remove`, and rewriting a line in place.
- **Clear a method** with `$methodtext.$assign('#')`, never `''`: the empty string removes its local variables.
- **A method never has zero lines.** `$count` stops at 1. A loop `While count>0` that removes lines spins forever. Rebuild by appending first and removing after, and bound every removal loop.
- **Walk the lines** with `$first()`/`$next()`. `[n]` on an empty method raises an error that lands in the error count.
- **Read before you rewrite.** A full rewrite reads the current text first, so hand corrections are not erased.
- **YES means "compiles", not "changed".** A `replaceall` that matched nothing assigns successfully. Report `$methodlines.$count` before and after, with the expected difference beside it. When a rewrite replaces a block of lines, put `kCr` around the block and around the text (`con(kCr,text,kCr)`), so it cannot match the tail of a longer line, and require the old block to occur exactly once.
- **Code written into a method runs in THAT method.** Every variable the written lines use must be a variable of the target method; what the script itself has is irrelevant. Declare the parameters and locals first, then write the body: Omnis refuses a line that names a variable the method does not have. In `$lvardefs.$add(name,type,subtype,length,isParam)` the parameter flag is the fifth argument, and `$add` is find-or-add: it keeps an existing definition with its old type, so a type is changed by removing the variable and adding it again (lore 6.6).
- A written line that **calls another method**: check that the method exists before writing the call. Nothing else will notice until the line runs.

### 3.6 Signatures and parameters

- The signature of a method lives in its parameter definitions (`pvardefs`), not in the body. Optional parameters end in `_opt`: Omnis never complains about a missing argument, it just passes an empty one.
- **kFieldreference parameters take no literal values.** Omit trailing arguments, leave middle ones empty (`,,`), or pass `#NULL`. A literal `0` breaks the call.
- Whoever adds a parameter to an existing method checks every call site.

### 3.7 Classes as a whole

- **Copy a class** with `$classdata`: `Do newClass.$classdata.$assign(oldClass.$classdata)`. The target keeps its name.
- **An existing window class with content** silently ignores `$classdata.$assign`: the flag says YES, nothing arrives. Object classes and fresh classes of any type accept it. For windows: rename the old class aside, add a new one under the original name, fill it, check it, then remove the old one.
- **Identity test:** `cdif()` on two `$classdata` binaries; error code 8095 means identical. It only works between copies of one origin; a rebuilt class never reaches it.
- **Create a library** with `Create library (Do not close others) [path],NAME`. Without the option, every other open library is closed. An existing file at the path is overwritten.
- **Save class** makes notation changes permanent (see §2). It needs an existing class; a removal does not need one.

### 3.8 Global switches and checkout

- **Temporary global settings go into a reversible block.** `Calculate x.$prop as v` inside `Begin reversible block` / `End reversible block` is undone when the method ends, even if the run is killed. `Do x.$assign(v)` is **not** reversible.
- **Checkout.** A class shown as not checked out, in a library with a VCS build date, under the preference `$alloweditifnotcheckedout` = false, cannot be edited — and `$classdata.$assign` returns YES anyway. Open it for the run: `Calculate $root.$prefs.$alloweditifnotcheckedout as kTrue` in a reversible block.
- **Close the Find and Replace dialog of the IDE before `$findandreplace`.** With the dialog open, a class-wide call writes its log into the dialog, and the run becomes very, very slow. Close the instances and design editors of the classes searched as well (lore 11.2).
- **Reading another library's classes** from code in library X needs `$ignoreexternal` = kTrue on **X**, the reading library. The list of libraries is never filtered, so a library can be listed and still show no classes.

### 3.9 Names and externals

- Omnis resolves names **case-insensitively**. A local `fileOps` hides the external `FileOps`. Never give a variable the name of an external or a function group.
- **FileOps has two faces.** The static functions (`FileOps.$doesfileexist`, `$splitpathname`, …) are called on the group; the file-handle methods (`$openfile`, `$closefile`, …) on the object `files`. They share no methods.
- **Never name a variable `flag`.** It is command grammar (`If flag true`): a local of that name can be declared, but `If flag` is refused, and one such line makes a whole `$methodtext.$assign` refuse (lore 8.5).
- **Library names are fragile** across sessions: a restored session takes the file name. Resolve by path when in doubt.
- **A library named in the code must be open when the script is assigned.** A line naming a library that is not open is refused at the assign: the console names the line, and nothing runs. A guard such as `If isclear(targetRef)` after `Set reference targetRef to OtherLib.$classes.X` is therefore never reached for a closed library. A script that wants to say so itself looks the library up by name, `Set reference ref to $root.$libs.$findname('OtherLib')`, tests `isclear(ref)`, and works through `ref` from then on.

### 3.10 Run it twice

Every script must survive being run twice. The second run finds nothing to do and says so (§1.8).

- A **guard** asks whether the work is done, and it reads content: a marker in the method text, the value of a property. A line count is no guard; it moves for other reasons.
- A test that recognises the new state must match exactly the lines the script changes. Count its hits in the current text before relying on it: a new text that also stands elsewhere in the method makes a correct second run report a failure.
- Guard against the target state, not the source state: the column that makes a list ten columns wide is added under `If list.$colcount<10`.

### 3.11 Check before delivering

The blades (`blades/BLADES.md`) read a script as text and report what Omnis would refuse or silently get wrong: unknown commands, functions, constants and notation, variables outside the closed set, unclosed literals, unbalanced blocks, a header that does not match its run stamp, jump lines that point at nothing.

- **With code execution:** run `python3 check_all.py --export <export> <script.txt>` on the file **as it will be delivered**, against the export of the library the script runs against. Deliver only on `CLEAN`. Read the `..` notes and say why each one is harmless; a failure is fixed in the script, not explained away.
- **Without code execution:** say so in the delivery, so the user runs them before Execute.
- A clean result is a floor. What the blades cannot judge — whether a property belongs on that object, whether the arguments are right, whether the logic holds — needs §3.1: measure it in the script.

### 3.12 Files a script reads: `execInput/<name>/`

What a script **reads** from disk lies in a folder `execInput/<name>/` beside the library, where `<name>` is the GENERATOR name without its version: `execInput/release_build/`. What a script writes goes into its run folder (`env`) or into a folder of its own beside the library (`execExports/`, `execRelease/`).

- **A script never changes, moves or deletes its input.** Run twice, it must find the same files (§3.10).
- **The script makes the folder itself**, on its first run, when the folder is missing, and then stops with the list of the files to lay in. The console makes no `execInput` folder.
- The script computes the path itself, from the path of the open Executor library: `con(mid(sys(10),1,rpos(sys(9),sys(10))),'execInput',sys(9),'<name>',sys(9))`.

---

## 4. Jump links and payloads

A script, or a delivery of small changes, may end with a block of jump links. In the console's Jump view each line becomes a link; a double-click opens the item named there (a single click only selects the row).

```
## ===== JUMP LINKS 1.0 =====
# === The loop ===
# Do MyLib.$classes.MyClass.$methods.//$myMethod//.$modify(12) ## the loop that was changed
# Do MyLib.$classes.MyClass.$methods.//$myMethod//.$lvardefs.total ## the new local
```

- The block **must** start with the marker `## ===== JUMP LINKS`, followed by the Executor version and the closing signs: `## ===== JUMP LINKS 1.0 =====`. The console finds the block by that fixed start, so an older console still finds a newer block. A jump line above it is never seen. The version is checked like `RUNS-IN` (§1.5), but on a jump nothing stops: a version that cannot be read or a newer minor is a Trace Log line, a newer major an Error Log row and the bell, each once; the jump goes ahead.
- The block is the **last thing in the script**, after `Quit method result`. Comments after a `Quit` do not run, and everything from the marker to the end of the text is read as the block.
- Each jump line is a comment that starts with `# Do `, followed by the target, then ` ## ` and a short description. A line holding `===` and no target becomes a heading in the list (`# === The loop ===`). Blank lines are skipped.
- A `$` in a method name is escaped as `//$name//`.
- Always the short library form (`MyLib.$classes…`).

| Target | Form | Opens |
|---|---|---|
| a method, at a line | `MyLib.$classes.C.$methods.//$m//.$modify(12)` | the method editor at line 12 (`$methodlines.12` works as well) |
| a class | `MyLib.$classes.C` | its first method; its design if it has no method |
| the method editor of a class | `MyLib.$classes.C.$methods` | the same |
| the design of a class | `MyLib.$classes.C.$objs` | the design |
| a class, instance or task variable | `MyLib.$classes.C.$cvardefs.name` / `$ivardefs.name` / `$tvardefs.name` | only the variable pane of its kind; the variable itself is not selected |
| a local variable or parameter | `MyLib.$classes.C.$methods.//$m//.$lvardefs.name` | the method, at Locals or Parameters; the variable itself is not selected |
| an object | the full container path, `MyLib.$classes.W.$objs.box.$objs.field` | the design, the object selected if it has a method |
| an object without a name | its `$ident`: `MyLib.$classes.W.$objs.1017` | as above |
| a method of an object | `MyLib.$classes.W.$objs.box.$objs.field.$methods.//$event//.$modify(2)` | the method at the line |
| an attribute | the item's path and the attribute: `MyLib.$classes.W.$objs.field.$text` | only the Property Manager, on the item; find the attribute there yourself, it may be on another tab |

Write the **whole path** down to the item. "Go to the method and change the variable `x`" is not a jump link.

- **The description says what to check there**, not what the target is.
- **The target must exist when the link is opened.** Names age; after a rename the old link dies. A link that cannot open writes the reason into the trace log and rings the bell.
- **The line number is part of the work.** `1` is honest when the script finds the line only at run time. When the script builds the method itself, the author knows where the cursor belongs and writes that line.
- An object without a method opens its class design, but the object is not selected. The Property Manager is fed only when its panel is visible.
- Shift-double-click on a row selects its line in the script.

**Payloads.** A jump line can carry text after `#>`. On the double-click the text is copied to the clipboard, and the reader pastes it at the place the link opened. This is how line-level changes are delivered for pasting by hand.

```
# Do MyLib.$classes.C.$methods.//$m//.$modify(12) ## 1/2 select 1 line (12), paste #> Calculate x as 1\nCalculate y as 2
```

- The description says **how many lines to select** before pasting. The text between ` ##` and `#>` is the heading of the row in the Jump view: a number and a few words. The substance goes after `#>`.
- `\n` separates lines of the payload; the Jump view shows them as line breaks. No tabs, and no indentation needed: the method editor indents `If` … `End If` itself when the lines are pasted. A payload may also be a whole text block, with blank lines and `- ` bullets.
- The payload must not contain ` ##` or a second `#>`: the line is split at the first ` ##`, the payload taken from the first `#>`.
- **A payload line is one physical line**, however long. Deliver it in a file, never inside wrapped prose: a line broken by a chat window or an editor fails at the paste, not at the click.
- **Replay it before delivering.** Split at the first ` ##`, take what follows `#>`, turn every `\n` into a line break, and compare the result with the text that is meant to arrive.
- Inside one method, deliver changes **from the bottom up**, so the line numbers of the next change are still right.
- Count lines against the current state of the method, not against an old export.

A **Copy line** carries a payload and no target. The double-click copies the text and opens nothing:

```
# Copy ## the new description #> Reads the vault index and returns one row per class.
```

---

## 5. Further reading

- **`MANUAL.md`** — what each part of the console does, button by button.
- **`OMNIS_LORE.md`** — measured Omnis behaviour that the official help does not state or does not warn about. Recommended whenever a script writes notation.
- **`OMNIS_IDIOMS.md`** — patterns that work.
- **`blades/BLADES.md`** — the checks a script passes before it is run (§3.11).
- The Omnis Studio help and the online manuals remain the reference for commands, functions and notation.

---

Copyright (c) 2026 Udo Sonnabend (USO-FT). This text is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/): you may share and adapt it, also commercially, if you name the author, link the source and the license, and say what you changed. Code examples in this text may also be used under the MIT License, without attribution in your code. Source: https://github.com/uso-ft/omnis-executor
