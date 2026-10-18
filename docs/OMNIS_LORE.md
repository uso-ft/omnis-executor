# OMNIS LORE — measured Omnis Studio behaviour

**What this is.** Facts about Omnis Studio that you would otherwise learn only by trying: behaviour the official help does not state, or states without warning. Every entry is a fact, the condition under which it holds, and the form that works.

**Tested with** Omnis Studio 10.22 on macOS 10.14.6 (Build 31896, 64 bit) and on Windows 10 Enterprise (Build 32066, 64 bit), as of 2026-10-18. Measured on macOS unless an entry names Windows. Other versions and platforms may behave differently.

**Scope.** Pure reference (signatures, constant groups, notation trees) is in the Omnis help and is not repeated. How to write scripts for the Executor is in `CONTRACT.md`. Class and method names such as `Tool.$edit` belong to `Executor.lbs`, which comes with this file, so every example can be looked up there.

**Marks.** No mark: measured. **(author)**: observed by hand in the IDE. **(help)**: stated in the Omnis help, not measured here.

> Omnis is an almost completely reflexive language — running code can read AND modify its own classes, methods, variables and objects, and then run what it has just written: a method whose text was assigned a moment ago can be called in the same run.

---

## 1. Notation and paths

### 1.1 The path

- **A path starts at `$root`, a library or a current-item shortcut** (`$clib`, `$cclass`, `$cinst`, `$ctask`). `Lib.$classes.X` and `$root.$libs.Lib.$classes.X` address the same class.
- **`$classes` is the generic group; Omnis answers with the typed one.** A window addressed as `$classes.X` reports `$windows.X` in `$fullname`, a code class `$objects.X`, a task `$tasks.X`, a schema `$schemas.X`. `$extobjects` reports itself as `$components`.
- **Nesting depth does not matter.** `$objs.container.$objs.obj.$methods.//$m//` resolves like a top-level path; `//name//` and `[path]` carry to any depth.
- **A trailing segment the item does not have invalidates the whole path.** `…$methods.//$m//.$methods` or `…$objs.obj.$objs` is clear, not a parent group. So a path that does not resolve can be shortened from the end, one `.$name` part at a time (`…$objs.obj.$objs` → `…$objs.obj`), and the first shorter path that resolves is the real item.
- **A path held in a string becomes a reference through square brackets.** `[#S1].$methodtext` reads the method whose `$fullname` is in `#S1`. `[#S1]().$…` works as well.

### 1.2 Members of a group

- **A method is addressed with `//name//` or `$findname`.** `$methods.//$m//` and `$methods.$findname('$m')` give the same item. Written bare, `$methods.$m` is read as a CALL of `$m` on the group: the bare form fails for every name that begins with `$`. The house form writes `//name//` for every method.
- **Other members resolve bare:** `$objs.scrEditor`, `$classes.Tool`, `$cvardefs.cResult`.
- **Omnis strips `//…//` around a plain identifier when a line is stored.** `$methods.//stepInto//.$modify(13)` is stored as `$methods.stepInto.$modify(13)`. A name with spaces does not survive a stored line at all. Inside a string literal, for example in `eval('…')`, everything survives.
- **Case: `$findname` ignores it in `$libs`, `$methods`, `$objs` and the variable groups (`$cvardefs` …), and respects it in `$classes`, in the typed class groups (`$tasks`, `$windows` …) and in `$itasks`.** `$classes.$findname('startup_task')` finds nothing when the class is `Startup_Task`, for every class type. A class name written directly in a path respects case as well. A leading `$` is part of a method's name.
- **`$findname` finds by name only.** An object without a name is found by its ident: `$objs.1017` or `$objs.$findident(1017)`. `$objs.$findname('1017')` finds nothing.
- **A method line is an item:** `…$methods.//$m//.$methodlines.3`. It answers `$lib()`, `$class()`, `$method()`, `$text`, `$name` and `$ident`; `$name` and `$ident` are both its line number, so `$methodlines.$findname('3')` finds the third line.

### 1.3 `$objs`

- **On a class, `$objs` holds the direct children only.** A window with 114 objects in three levels reports `$objs.$count` = 6. Nested objects are reached through their containers: `$objs.A.$objs.B`. To walk the tree, descend wherever `$objs.$count>0`; a structural test cannot go stale the way a list of container types can.
- **On a running instance, `$objs` finds a field at any depth by name.** `$cinst.$objs.dfResult` resolves a field three containers down; `$cclass.$objs.dfResult` does not.
- **`$objlink` records the static container of a class object.** 0 = top level; low 16 bits = the container's `$order`; high 16 bits = page or tab number in paged and tab panes, column and section in complex grids. 131079 = 0x00020007 = page 2 of the object with `$order` 7. The JSON export has it under `object.json` → `properties` → `objlink`.
- **Class notation and instance notation are separate.** Runtime properties exist only on the instance (`$vscroll`, `$firstvis`, `$lastvis`, `$contents`, `$hasfocus` on a multi-line entry); the class knows `$vertscroll`. The help has a page for each: `notation/root/libs/lib/windows/window/objs/…` for the class, `notation/root/iwindows/window/objs/…` for the instance.

### 1.4 `$fullname` and `$ident`

- **`$fullname` is a label, not an address.** It carries the typed group (`$windows`), and not consistently: in one run `$clib.$classes.X.$objs` came back as `$root.$libs.Lib.$windows.X.$objs` and `$clib.$classes.X.$cvardefs` as `$root.$clib.$classes.X.$cvardefs`. Do not feed it back as a path.
- **`$fullname` is the identity test for two references:** `If a.$fullname=b.$fullname`.
- **An object without a name has a `$fullname` all the same**, built from its type and ident: `…$objs.newwindow_radio_1017`. The JSON export names its folder the same way.
- **`$ident` means something different for every kind of item:** the position of a line, a number for a method, an identifier for a class. Unique only within a class: two open windows can carry the same value. On its own it never says what it belongs to.
- **Line or method, by relation:** `ref().$method().$fullname=ref().$fullname` → a method; `ref().$method()` empty → a class or an object; otherwise → a line of that method.

### 1.5 Brackets after a step: the `$name` rule

- **A step that is a method needs `()` before `.$name`.** `$lib().$name` is the library's name; `$lib.$name` is the literal `'$lib'`. The same holds for `$class()`, `$group()`, `$method()`.
- **A reference variable needs none:** `classRef.$name` is the class's name. `$ref.$name` inside `$sendall` and `$makelist` needs none either.
- **A reference held in a list cell or an instance variable needs `()`:** `list.[n].refCol().$name` is the object's name, `list.[n].refCol.$name` the column's. Only `$name` shows the difference; `$fullname`, `$classtype` and `isclear` go through the stored reference without brackets, so a test built on them passes while `$name` beside it answers wrongly.
- **Everything else is written without `()`:** `ref.$classtype`, `ref.$class`, `ref.$lib`, `ref.$objtype`.
- **`$group().$name` names the group an item belongs to,** and so its kind: `$libs`, `$windows` or `$classes`, `$methods`, `$objs`, `$cvardefs`. A group itself has no group and answers `unnamed_value`. The way up is `$class()`, not a second `$group()`.

### 1.6 Calling and referencing

- **`ref.$m` names the method, `ref.$m()` runs it.**
- **Evaluating a chain RUNS every `()` link except the last.** In `ctx.$a().$b().$c`, `$a()` and `$b()` are called. If a middle link does not exist, the next one raises; if it has side effects, they happen. Test the chain prefix by prefix with `$cando`, written without the brackets, before evaluating it.
- **A method reached through an expression, as an item:**
  - class method: `[expr].$class().$methods.$findname([expr].$name)`
  - method of an object, at any depth: `[expr].$obj().$methods.$findname([expr].$name)`
  - `[expr].$obj().$class` is true for the second kind. `[expr].$fullname` is invalid for an object's method, and `[expr].$method()` returns `$event`.

---

## 2. Item references

### 2.1 Testing a reference

- **The test:** `$cando` on the path before resolving, `isclear` after.

  ```
  If [path].$cando
     Set reference ref to [path]
     If not(isclear(ref))
        ## a valid item
     End If
  End If
  ```

  Resolving is what raises, and `$cando` is the only test that runs before it. Over 34 kinds of item with a known answer both scored 34 of 34; `isnull` behaves exactly like `isclear`.
- **`$cando` itself can raise.** `Lib.$classes.TOOL.$cando` raised 25207 where the class is `Tool`; `Lib.$classes.tool.$cando` answered false without an error.
- **`$cando` answers yes for a property.** It says whether the notation applies, not whether the item has it.
- **`ref<>''` is not a test.** A reference set to a path, valid or not, never equals `''`. Only a reference filled from an empty method return (`Quit method ''`) equals `''`, and it is also `isclear`.
- **`ref.$lib` fails for everything outside a library** (`$root`, `$libs`, `$prefs`, `$extobjects`, `$sessions`, `$itasks`, `$constants`, external components). Not a validity test.
- **`ref.$class` is false for a library, for a `$cols` group of a local list and for everything outside a library.** Not a general validity test. It is the test for a HELD class reference: 1 while the class lives, 0 after it was removed, false on an empty cell and on `unnamed_value`.
- **`ref.$classtype` reads the same on a live and on a dead class reference** (`window`). Compared in an expression, `ref.$classtype*1>0` tells a class from items that are not classes (author); read into a character variable first, the constant has become its name and `*1` gives 0.
- **`isclear` tests the VALUE.** A reference to an integer variable holding 0 is `isclear`; so is a reference to a property whose value is 0 or empty. On a group, `isclear` can report empty while `$count` counts members: test a group with `$count`.

### 2.2 What a reference holds

- **`Set reference` on a PROPERTY path holds the property's value, not the property.** The item is named `unnamed_value`; a value of 0 or empty leaves the reference clear. Whether such a path "resolves" therefore depends on the value. To ask whether an item has an attribute, look the name up in `$attributes` (chapter 3).
- **A failed `Set reference` CLEARS the target.** It starts, empties the reference, then raises 25207 on the right-hand side; with the error handler continuing, the next line finds a clear reference, not the previous one.
- **`#NULL.$ref` as a marker.** `Set reference ref to #NULL.$ref` shows `#NULL` in the debugger; after a failed `Set reference` the same variable shows `NULL`. So the display tells whether the failing line ran. `Set reference ref to #NULL` is a different thing.
- **A reference can be clear and still have a `$fullname`.** `#NULL.$ref` points at `$root.$hashvars.#NULL`.
- **A method returning a list reference needs `.$ref` at the call too.** `Quit method list.$ref`, then `Set reference ref to inst.$m().$ref`. Without the second `.$ref` the caller gets a copy; `$add` on it raises nothing and the rows go nowhere. `Do inst.$m().$add(…)` reaches the list directly.
- **A reference set from such a call without `.$ref` is a snapshot.** Rows added to the list afterwards do not show through it; call the method again each time the list is read.
- **`Do ref Returns var` evaluates the referenced item** and puts its value into `var`.
- **`nam(field[,doitems=kTrue])`** returns a field's name; with `doitems` true it follows item references (help).

### 2.3 Held references

- **Whether a held reference survives a remove and re-add of its class depends on how it was made.** A list cell filled from `$classes.$findname(…).$ref` followed the name to the new class; a reference taken with `[path].$ref`, a copy taken with `().$ref` and a cell filled through `$sendall(…$ref…)` were dead. A dead class reference reads `$fullname` `Lib.$windows`.
- **Across anything that may remove a class, keep the name, not the reference.** Take `Lib.Class` while the reference lives and resolve it again afterwards.
- **`#NULL` passed to `$add` into an item-reference column stores `unnamed_value`,** and `If cell` is true on it. An omitted argument leaves the cell empty.

### 2.4 From a reference to its owners

- **`ref.$lib()` is the library that owns the item.** It works although the help does not list it (nor `$class()`, `$inst()`).
- **`$clib` is the library of the RUNNING method,** not of an item it was handed. A method that receives a reference and looks something up in a library takes the library from the reference: `Set reference lib to ref.$lib().$ref`.

---

## 3. Introspection

### 3.1 `$attributes`

- **`$attributes` lists everything an item understands: properties, groups and methods.** A window class has 133 entries, a window object 327, a schema column 22. The names carry the `$`: `$servertablename`, not `servertablename`. The groups (`$objs`, `$methods`) and methods such as `$add`, `$open` or `$select` are in the list as well.
- **To ask whether an item has an attribute, search the list:** `Do ref.$attributes.$makelist($ref.$name) Returns list`, then `list.$search(low(list.c1)=low(name),kTrue,kFalse,kFalse,kFalse)`.
- **`$attributes.$findname('$x')` returns the VALUE, not the attribute.** The item is named `unnamed_value`, and a value of 0 or empty comes back clear. So it cannot tell an attribute that is 0 from one that is missing.
- **A group in the list answers `$ref.$first.$cando`** (author): `$attributes.$makelist($ref.$name,$ref.$canassign,$ref.$first.$cando)`. `$next` does not walk `$attributes` (author).
- **`$att(n)` is the n'th of the item's `$attcount` attributes, counted from 1; `$att(n).$name` gives its name.** It is not the n'th row of `$attributes.$makelist($ref.$name)`: `$attcount` is larger than that list (103 to 57 on `$root`, 94 to 59 on a class, 64 to 24 on a method, 56 to 33 on a variable definition), and the order is not the same: on `$root` the names differ from row 2 on; on a class, a method and a variable definition rows 1 to 3 agree and the last row differs (rows in between not compared). `$att(n)` read without `.$name` gave NULL on `$root` and 0 elsewhere, for an `$att(1)` that is a method (`$add`) or `$activetask`; whether it returns the VALUE of a property is not measured.
- **`$chaincount` is 1 on every reference measured** — `$root`, a library, a class, a method, a method line, a variable definition, a path resolved from text, a reference set from another reference variable, a reference held in a list cell with and without `()`. **`$chain(n)` counts from 0: `$chain(0)` is the item itself, `$chain(1)` and higher return NULL and a clear reference.** None of the three raises an error. A reference with a chain longer than one has not been found.
- **Reading `$attributes` and `$makelist` on a class or an object does not change the class.** Neither `$moddate` nor the internal version moves.

### 3.2 The kind of an item

- **`$classtype` is filled only for classes and instances** (`object`, `window`, `task`, …). For groups, methods, objects and variable definitions it is empty.
- **`$group().$name` is the general kind** (1.5). It is empty for everything directly under `$root`.
- **A property resolves to its value** (2.2): `$fullname` is `unnamed_value`, `$class` and `$lib` are false. A path that arrives from outside and may run one step too far is checked for that.
- **A list column resolves and answers `$class` true, but has no group.** A local variable sits under `.$lvars.`: `…$methods.//$execute//.$lvars.list2.name` is the column `name` of the local list `list2`.

### 3.3 The type of a variable

- **A DEFINITION answers with `$objtype`, a LIVE variable with `$type`.**

  | asked | path | token |
  | --- | --- | --- |
  | type of a definition | `$cvardefs`, `$ivardefs`, `$lvardefs` | `$objtype` |
  | type of a live variable | `inst.[name].$ref`, `$lvars`, `$ivars` | `$type` |

  `$type` on a definition always says `itemref`; `$objtype` on a live variable is empty. On a live object variable write `ref.$type`, not `ref().$type`, which says `itemref`.
- **A live item-reference variable answers for its TARGET.** `ref.$type` says `list` or `char` for what it points at. Whether a variable IS a reference is answered by its definition: `$lvardefs.name.$objtype` is `itemref`.
- **`inst.[name]` reaches the value of a class or an instance variable from outside;** `inst.[name].$ref` a reference onto it; `classRef.$cvardefs.$findname(name)` the definition. `inst.cLog.$linecount` works directly. `$itasks.Lib.tVar` does not reach a task variable (25207).
- **`$cvars` is not a group.** `classRef.$cvars`, `inst.$cvars` and `$cvars.$sendall` come back empty or raise 25207. `$sendall` over `$cvardefs` works.

### 3.4 The type of a value

- **Omnis has no function that reports the type of a value.** Test the outcome instead: put a sentinel into the variable, read over it, and check whether the sentinel survived.

  ```
  Calculate info as '###UNREAD###'
  Calculate info as lib.$userinfo
  If info='###UNREAD###'
     ## the read raised: the value is not character
  End If
  ```

- **A `Calculate` that raises leaves the target at its PREVIOUS value.** It neither clears it nor stops the method. A loop that reads foreign values needs the sentinel inside the loop, or each failure reports its neighbour's value. Reading a binary `$userinfo` into a character variable raises 125282.
- **A constant read as text is its name without the `k`, in lower case.** `$objtype` collected with `$makelist` yields `pushbutton`, `multilineentry`, `bobj`, not `kPushbutton`. Compare numerically: `$makelist($ref.$objtype*1)`, `node.$objtype*1=kEntry`. In a direct expression `ref.$objtype=kEntry` compares correctly.
- **The JSON export names types differently.** Its `kComplexGrid` is `grid` as a live `$objtype`, not `complexgrid`. A table derived from the export does not match the running class one to one.

---

## 4. Groups

- **`$objs`, `$methods`, `$cols`, `$classes` are groups, not lists.** No `$line`, no `$linecount`. Walk with `$first()` and `$next(ref)`, size with `$count`; `$sendall` and `$makelist` work on them. Use `$first()` for the first member, not `.1`.
- **`$add` returns a reference to the new member** for `$methods`, `$objs`, `$methodlines`, the variable groups, `$cols` and `$classes`. Keep it: `Set reference ref to grp.$add(…)`, or chain straight off the call: `….$add(…).$name`.
- **`$add` on a variable group is find-or-add.** A name that exists already returns the existing definition; `$count` stays the same. So an unchanged `$count` does not mean `$add` failed.
- **A name that is taken is changed by Omnis.** `$objs.$add` of a second `grbLog` creates `grbLog1`; a later lookup by name finds the old one. Use the reference `$add` returned, and check `ref.$name` when the name matters.
- **A group shrinks while it is walked.** Removing members with a cursor, or with `$sendall(…$remove($sendallref))`, skips members. Remove the current first member until none is left:

  ```
  While not(isclear(grp.$first()))
     Do grp.$remove(grp.$first())
  End While
  ```

  and check `grp.$count=0` afterwards.
- **That loop never ends when a member refuses removal:** `$first()` keeps answering the same one. Where that can happen (system classes, 5.4), walk a list of names taken once, with a bound, and count what `$findname` no longer finds rather than the calls made.
- **In a nested `$sendall`, the condition of the OUTER one sees the outer item.** In `$libs.$sendall($ref.$classes.$sendall(…),pos('execBackup_',$sendallref().$name)<>1)` the second argument tests the library, although the message holds a `$sendall` over `$classes`.
- **`$isa(rClass)` is true for the class itself and for every subclass, at any depth** (help). A `$sendall` filtering on `$ref.$isa(cls)` collects `cls` and everything derived from it.

---

## 5. Classes

### 5.1 Creating a class

- **`$classes.$add(type,name[,folderIdent])` creates a BARE class.** Everything else is set afterwards: `$superclass`, `$desc`, `$designtaskname`, and `$external`, which must be kTrue for an object class to be offered as the subtype of an object variable. Without it the class is simply not offered; nothing reports why. A copy of a class needs the same: carry all properties, not only methods and variables.
- **`$classes.$add` refuses a name that is a notation identifier, silently.** Refused: `$methods`, `$classes`, `$objs`, `$modify`. Accepted: `$myclass`, `flag`, `#S1`. The refusal shows only later, as 101201 "Unable to find class" at `Save class`.
- **A new window class has one method already:** `$classes.$add(kWindow,'X').$methods.$count` is 1.
- **Every library made by `Create library` carries an empty class `Startup_Task`** (author). A library that must never start code removes it right after creating it.
- **`$name` of an object in a class is assignable:** an object can be renamed in place. `$fieldstyle` can be cleared on a class, although the help forbids clearing it at runtime.

### 5.2 Folders

- **A folder is a class of type `kFolder`.** Folder names share the library-wide uniqueness of class names, so a folder is found by name alone. `$findname` finds a class inside a folder: the namespace is flat. A folder has no `$classdata`.
- **`$parentfolder` can be assigned afterwards, also on `kSystemtable` classes.** A folder tree can be built flat and hung in later. At top level `$parentfolder` reads empty; a freshly created class reads 0. `$classes.$findident(id)` finds a folder by its ident.
- **Omnis creates the folder "System Classes" on the first `$classes.$add(kSystemtable,…)`,** with ident 275 in every library. Class counts compared between libraries must leave `kFolder` out on both sides.

### 5.3 Properties

- **What `$classdata` carries:** methods and `$userinfo`. Not `$desc`, `$version`, `$vcsrevision` or `$parentfolder`; a copy made through `$classdata` loses them. All four can be written by code.
- **`$version` of a class is CHARACTER.** `$vcsversion` does not exist; the property is `$vcsrevision`. A library has `$vcsbuilddate`, `$vcsbuildersname`, `$vcsbuildnotes` and no `$version`.
- **`$superclass` holds `Name` or `Lib.Name`.**
- **`$disksize` is the size in bytes, on the library and on a class.** On an open library it equals the size of the file. `len($classdata)` returns 0. There is no `$size`.
- **`$userinfo` of a class holds structured data:** a whole list survives `Save class` and reopening the library (author). A method has no `$userinfo`. A variable definition has one; it is saved with the class, survives a restart and is in the JSON export.
- **Class-variable VALUES are saved with the class** (author). A runtime assignment to a class variable persists; a default set in `$construct` does not correct a stale value.

### 5.4 Renaming and removing

- **A class can be renamed and then referred to again by its new name** in the same library; a new class can take the old name beside it.
- **`$cvardefs.$remove(ref)` works, and `Save class` keeps the removal.**
- **A system class cannot always be removed.** `$classes.$remove` took `#BFORMS`, `#COLORS`, `#DFORMS`, `#EXTCOMPLIBS` and refused `#ICONS`, silently; the refused attempt still changes `#ICONS`.
- **A `$classes.$remove` without `Save class` survived closing and reopening the library.**

### 5.5 Saving, dates and editors

- **`$moddate` is the time of the last write to disk.** A change made by notation stays in memory, and `$moddate` stays put, until something saves the class. A class has no "modified" flag; nothing reports unsaved state.
- **`Save class` writes only what is pending.** On an unchanged class it leaves `$moddate` as it was, so saving everything that might have changed is safe.
- **The command `Close design` neither saves nor discards a pending change.**
- **Opening a class in an editor and closing it again by hand saves the class,** even with nothing changed: `$moddate` and the internal version move. A design window also writes its layout (`$left`, `$top`, `$width`, `$height`, the objects' positions) into the class when it is closed (author). A run-time instance does not.
- **A library's `$userinfo` is writable by notation, and survives a hard kill of Omnis without any save** (author). There is no `Save library` command.
- **A class has no `$modify`.** `X.$modify()` and `X.$methods.$modify()` do nothing, silently. `X.$methods.$first().$modify()` opens the method editor on the first method, `X.$methods.//name//.$modify(n)` on line n of that method.

---

## 6. Methods and method text

### 6.1 Methods

- **A method whose name starts with `$` is public, one without `$` is local to its class** (author). A local method is called from inside the class only: `Do method name`.
- **`$order` of a method is read-only.** Methods are reordered by creating them again in the wanted order; a new method takes the next `$order`.
- **`$methods.$add(<method reference>)` does not copy a method.** The reference is taken as a NAME, an empty method called `1` appears, and the call returns a live reference with no error. A method is copied by creating it by name and carrying `$methodtext` and `$lvardefs` across.
- **A method of an object on a window class behaves like a class method:** `$methods.$add`, `$lvardefs.$add` and `$methodtext.$assign` work the same. A freshly placed object answers `$methods.$count` with 1, an empty `$event` that the JSON export does not show. `$lvardefs.$remove(ref)` works on such an `$event` as well (measured only with no locals present).
- **The method of a menu line without a name cannot be reached.** In a menu class of a real library it read `$name` `0`; `objRef.$methods.$findname('0')` found nothing, and a reference to it kept in a list did not resolve later (25207 `…$menus.<menu>.$objs.$methods.0`). The menu line itself was reachable through its own reference (`jsonfix v2` 11:10, `v3` 13:12). Give menu lines a name.
- **Calling a method that does not exist returns empty, without an error.** Calling a method with more arguments than it declares drops the extra ones, without an error; a parameter that gets no argument arrives empty.
- **A parameter is a local variable that arrives filled.** It may be assigned.

### 6.2 The model: lines

- **Omnis checks method text line by line; there are no blocks.** A body whose last line opens an `If` and never closes it is accepted and stored. It fails when it RUNS: E108105 "If or Else command with no matching End If".
- **A line is refused for one of five reasons:** an invalid command, a variable not defined in the method's scope (by far the most common), an invalid calculation, an invalid function or invalid arguments to one, invalid notation.
- **A literal path is checked when the line is compiled; the same path through a reference is not.** `Do Lib.$classes.X.$methods.//$y//.$methodlines.3.$modify()` is refused; `Do ref.$modifiy()` — a typo — is accepted and does nothing at run time.
- **`$methodtext` carries no indentation.** Lines are separated by `kCr` alone, and the text has no trailing `kCr`. The JSON export (`.omh`) equals `$methodtext` once its leading tabs are removed and `CR LF` is read as `kCr`.

### 6.3 Writing method text

- **There are three write operations, each atomic in its own unit:**

  | operation | unit | on refusal | test |
  | --- | --- | --- | --- |
  | `m.$methodtext.$assign(text)` | the whole body | body and locals unchanged | `Returns flag` |
  | `m.$methodlines.$add(line)` | one line, appended at the end | nothing created, `$count` unchanged | `isclear(ref)` |
  | `line.$text.$assign(text)` | one existing line, where it stands | old line unchanged | `Returns flag` |

  One invalid line refuses a whole `$methodtext.$assign`, and the flag does not say which. To find it, send the same text line by line into a throwaway method.
- **`$methodtext.$assign` answering YES means the text compiles, not that it changed anything.** A `replaceall` that matched nothing still assigns successfully. Compare `$methodlines.$count` before and after against the expected difference.
- **`$methodtext.$assign('')` removes all local variables of the method** (Omnis ST/PF/1528). `$methodtext.$assign('#')` empties the body and keeps them.
- **Nothing can be inserted in the middle.** `$methodlines` has no `$addbefore` and no `$addafter` (help). A line in the middle is changed with `line.$text.$assign`, removed with `m.$methodlines.$remove(line)` (author); `line.$text.$assign('')` leaves an empty line standing.
- **A method never has zero lines.** Removing the last line empties it: `$count` stays 1, so a loop `While $count>0 … $remove` never ends. A method is emptied with `$methodtext.$assign('#')` and one `$remove` of the first line. The next `$methodlines.$add` FILLS that empty line instead of appending, so the first add reads 1 → 1.
- **A method just made by `$methods.$add` accepts `$methodlines.$add` at once.** Its `$methodtext` reads empty.
- **Read the lines with `$first()` and `$next()`.** An index (`$methodlines.[n]`, `.2`) returns the same text on a method with lines; on an EMPTY method `[1]` returns empty and raises "Unrecognized numeric identifier", and `[1].$text.$assign` is refused.
- **A `$methodlines` reference used after `$remove` may no longer add reliably** (author). Resolve the group again before adding.

### 6.4 What Omnis changes when it stores a line

- **Four normalisations:**
  1. Several spaces before `##` collapse to one, one pair per pass (3 → 2 → 1).
  2. Commands and variable names take Omnis's own spelling; `##x` becomes `## x`.
  3. Clause defaults are appended: `For n from 1 to 3` is stored as `For n from 1 to 3 step 1`.
  4. Several spaces between arguments collapse to one. In free message text (`OK message`, `Send to trace log`, `Working message`) the spaces are kept.
- **So the stored text is no test of whether a line was accepted.** Kinds 1 and 4 change the middle of a line: a correctly stored line with aligned arguments fails both an equality and a prefix comparison. The write operation's own answer is the test (6.3).
- **`//name//` around a plain identifier is removed** when the line is stored (1.2).

### 6.5 Refusals and the error channel

- **A line naming a library that is not open cannot be assigned** (author): `OtherLib.$classes.X` with `OtherLib` closed is refused. The same line, written while the library was open, stays in the method and is refused again whenever the text is assigned anew (JSON export, 11.5).
- **Every refused write raises a collectable error,** with the line: `Error when assigning to method text / Unrecognized variable name, item name or attribute [<path>.$methodlines.<n>]`. Without an error handler only the bare NO, or the clear reference, is visible.
- **One error per CALL, however many lines in it are guilty.**
- **Reading or self-assigning a line can raise 25207 without a refusal.** `Calculate text2 as ref.$text` raised `Problem with notation uebersichtClassList.className When evaluating className …` for some lines, and `ref.$text.$assign(ref.$text)` raised it for lines holding `$cwind.$objs.efText.$ref`; none of them was refused: 176 refusals came with exactly 176 rows 25208, the 17 rows 25207 stood beside them (`jsonfix v3` over a library of 30 073 lines). The cause is open.
- **A line holding `#???` is refused when assigned to itself.** `Do line.$text.$assign(line.$text) Returns flag` answers NO and raises 25208 "Error when assigning to method text / Unrecognized variable name, item name or attribute", one error per refused line; the old line stays. The same text with `# ` in front is taken. A valid line assigned to itself is taken, so the self-assignment separates the broken lines of a method from the sound ones.
- **An assignment THROUGH AN INSTANCE VARIABLE raises an error and succeeds.** `Do iRef.$methodtext.$assign('#')` stores the line correctly and logs "Attempt to use an instance or task variable when no instance exists". The code is 25216. Reading through an instance variable, and the same assign through a local reference, a class variable or `$cinst`, raise nothing.
- **WRITING a line that names an instance variable raises 25216 as well, and the line arrives.** This holds for a class without an open instance AND for the methods of an open instance.

### 6.6 Variables and parameters of a method

- **`$lvardefs.$add(name,type,subtype,length,isParam)`: the parameter flag is the FIFTH argument.** A kTrue in the fourth slot is taken as a length; the variable becomes a plain local and arguments never bind.
- **The subtype is the bare constant:** `kCharacter,kSimplechar,100000000`, `kInteger,k32bitint,0`, `kBoolean,'',0`, `kItemref,'',0`, `kFieldreference,0,0,kTrue` for a field-reference parameter. An empty subtype refuses `kCharacter` and `kInteger`; the constant's name in quotes is refused as well. The same arguments hold for `$cvardefs.$add` and `$ivardefs.$add`.
- **A refused add answers NO and returns a clear reference.**
- **`$lvardefs.$add` is find-or-add and does not correct a type:** adding an existing name with another type leaves the old definition. Change a type by removing the variable and adding it again.
- **`$parmno` follows the order of creation and cannot be written.** `$lvardefs.$remove` renumbers the rest. Reordering parameters means removing and adding them again; removing every variable removes the parameters as well.
- **`$lvardefs.$makelist` is in declaration order, parameters interleaved with locals.** Tell a parameter by `$parmno`, never by position.
- **Removing a variable definition leaves its lines standing, the name shown as `#???`.** `methodRef.$lvardefs.$remove(methodRef.$lvardefs.$findname('lText').$ref)` and the same form on `$ivardefs` of a class without an instance remove the definition (count 2 → 0); the method keeps its line count, and `Calculate lText as 'a'` reads `Calculate #??? as 'a'`, `Calculate iInstText as lText` reads `Calculate #??? as #???`. Lines that name no removed variable are untouched. Such a method no longer passes the JSON export (11.5).
- **A removed TASK variable is not shown as `#???`: its lines read `$ctask.<name>`.** Measured for all four kinds in one library (a window with design task `Startup_Task`, no instance open; `jsonfixtest_setup v1`): a local, an instance and a class variable become `#???`; `Calculate tTest as 't'` becomes `Calculate $ctask.tTest as 't'`, in a method of the task itself and in a method of the window. Such a line is TAKEN when assigned to itself and passes the JSON export; it fails only when it runs. Neither the self-assignment nor the export finds it.
- **Renaming a variable definition carries every code reference with it, not comments.** `$lvardefs.$findname('a').$name.$assign('b')`: the lines using `a` read `b` at once; a comment naming `a` keeps it.
- **A definition's type is on `$objtype`, `$objsubtype`, `$objsublen`, `$objinitval`, `$parmno`** (3.3); `$objtype` reads as a word (`char`), so compare `$objtype*1`.
- **Omnis refuses a body naming a variable the method does not have.** Variables and parameters are added before the text that uses them.

---

## 7. Execution

### 7.1 Evaluation and flow

- **Omnis has no short-circuit evaluation. Every term of an expression is evaluated, always** — in `&`, `|`, `pick()`, `con()` and every other function. `pick(1,2/0,'1')` raises "divide by zero" although index 1 selects `'1'`. A term that may fail needs its own `If`.
- **`Break to end of loop` leaves the loop.** `Jump to start of loop` goes on with the next pass.
- **`Next` is no loop command.** It belongs to the command group Finding data and locates the next record of a find table (help). A command checker passes it, because the name is valid.
- **`Send to trace log` writes to the Omnis trace log** in the IDE, not to a trace pane of your own window.
- **The runtime ignores `Breakpoint`.**
- **A branch holding only comments gives the debugger no line to stop on** (author). `Do 1` is a no-op that makes one.

### 7.2 Errors

- **`Load error handler <class>/<method> (from,to)` installs a handler for a range of error codes.** The handler reads `#ERRCODE` and `#ERRTEXT` and ends with `SEA continue execution` (resume after the failing line) or `SEA repeat command`. The command is reversible (7.4).
- **25207 is an unresolvable notation path, 125207 an unknown custom attribute** ("Unrecognized custom attribute") — the code of a method called on an item that does not have it.
- **A raised `Calculate` leaves its target at the previous value** (3.4). A raised `Set reference` clears it (2.2).

### 7.3 Changing code that runs

- **A method on the call stack must not be rebuilt** (author). The methods waiting below the running one need their way back into it. A method the run calls only later, and an unchanged method on the stack, do not matter. To change a method that is on the stack, run the change from another library.
- **The criterion is the stack, not the class.** A class in use can be changed as long as no method on the stack is touched: the tooltips of a window's objects were written from that running window.
- **An open instance runs the CURRENT method text of its class.** A line rewritten through the class with `$text.$assign` answered on the instance's very next call, without reopening it.
- **An open design editor slows a rebuild of its class to unusable** (author): it follows every change live. Close it first.

### 7.4 Reversible blocks

- **What is SET inside `Begin reversible block … End reversible block` is restored when the carrying method ends,** also when the stack is killed. The block encloses the setting, not the work:

  ```
  Begin reversible block
     Calculate $cinst.$norefresh as kTrue
  End reversible block
  ## … the work; $norefresh is restored when this method ends
  ```

- **In a window's `$construct`, the block is undone when the WINDOW closes** (author).
- **`Calculate x.$prop as v` is reversible, `Do x.$prop.$assign(v)` is not** (author). Not every command is reversible (help); `Load error handler` and `Disable cancel test at loops` are.
- **The first write inside the block decides** (author): at method end the variable returns to its value before that first write.
- **The restore is an `$assign`** (author). A class with a method `$set` and a counterpart named `$set.$assign`, taking a parameter, gets `$set.$assign(<old value>)` called at the end of any method that did `Calculate inst.$set as …` in a reversible block — a teardown hooked to a method's exit. The counterpart receives the OLD value.

### 7.5 Variables across scopes

- **In a code class method, task and instance variables need their prefix:** `$ctask.tVar`, `$cinst.iVar`. A bare `tVar.$start()` fails.
- **`ClassName.cVar` compiles only inside methods of that class.**
- **Class and instance variables of an open instance are reachable from outside** (author): `Lib.$classes.X.$insts().$first().cVar`. `Set reference r to inst.cVar` gives a COPY; changes to it never reach the variable. `Set reference r to inst.cVar.$ref` reaches it.
- **`$cinst` is the instance whose method runs.** Another window's objects are reached through its class: `Lib.$classes.X.$insts().$first().$objs.name`.
- **A `kObject` column added to a row at run time instantiates on its first method call:** `row.$cols.$add('store',kObject,'Class')`, then `row.store.$m()`.
- **An INSTANCE has no variable definitions of its own.** `inst.$ivardefs` is not a group, and `$add` on it is not taken. The value of an inherited variable survives such a refused `$add` of the same name.
- **A variable added to the CLASS under a running instance is there at once.** The running window writes and reads it, a method of the class compiles the bare name, and a class variable is shared with a window opened later.
- **A method that exists only in the instance cannot use an instance variable.** The bare name is refused at the assign (25208); `$cinst.iX` is assigned but fails at the call with 25227 "Unrecognized inherited variable".

### 7.6 The call stack: `sys(192)` and its neighbours

- **`sys(192)` returns the call stack as a list; row 1 is the method running now.** Its columns, all of them:

  | column | remark |
  | --- | --- |
  | `classitem` | the class; `.classitem().$name` gives its name |
  | `object` | a NUMBER for instance methods, 24599 for window methods, 24597 for a button event; what the number means is open |
  | `method` | – |
  | `line` | the line number. A column called `lineno` does not exist and reads empty without an error |
  | `linetext` | the text of that line |
  | `params` | – |
  | `methoditem` | the method as an item; empty for a method that lives only in the instance |
  | `inst` | – |

- **`sys(85)` and `sys(185)` exist in 10.22** (author). For an instance method a number stands between class and method.
- **`sys()` read INSIDE an argument of a method call already sees the called method** (author). Read it in a `Calculate` of its own first. In a command it sees the line itself.

---

## 8. Expressions and functions

### 8.1 NULL

- **`#NULL` propagates through any calculation, and `not(#NULL)` is `#NULL`.** An `If` on `#NULL` is not true, so a NULL test cannot simply be negated. `$colcount` of an undefined list is `#NULL`: keep the empty positive branch and act in `Else`.

  ```
  If someList.$colcount
  Else
     Do someList.$define()
  End If
  ```

- **A `<>` test with a possibly NULL term always takes the `Else` branch,** even when the values are equal; `|isnull(x)` does not help, the whole OR is NULL. Write the EQUALITY as the `If` and the failure in `Else`.
- **In `pick()`:** a NULL index counts as 0; a NULL selected value comes through as NULL; a NULL in a branch not selected leaves no trace.

### 8.2 Strings

- **`con()` joins strings. `+` is arithmetic:** `'a'+'b'` is 0.
- **`pick(index,v0,v1,…)` is 0-based,** so `pick(cond,ifFalse,ifTrue)` — the FALSE value first.
- **`low()` and `upp()`**, not `lower()`. `mid(s,start)` runs to the end. `rpos()` finds the last occurrence. `replace` replaces the first occurrence, `replaceall` all. `asc(string,position)` takes two arguments; with one, the line is refused.
- **Quotes.** Inside a single-quoted literal a quote is written twice: `'# test ''x'' quote'` is `# test 'x' quote`. A literal delimited by double quotes holds single quotes as they are: `"$assign('# hi')"`. Text that must contain quotes can also be built with `chr(39)`: `con('Calculate x as ',chr(39),chr(39))`.
- **`split(text,kCr)` keeps empty lines in the middle.**
- **`jst()`:** `jst(x,8)` pads to 8 with the value on the LEFT; `jst(x,'-8')` puts it on the RIGHT. `jst(x,'-')` with no width returns `x` trimmed (author). For dates and times the format starts with `D:` or `T:`; `D:` on `#T` gives nonsense without an error. The letters are single and repeat their output (`'D:yyyy'` is the year four times):

  | letter | | letter | |
  | --- | --- | --- | --- |
  | `y` / `Y` | year, 4 / 2 digits | `w` / `V` | weekday name, long / short |
  | `C` | century | `H` / `h` | hour 24 / 12 |
  | `M` / `m` / `n` | month: number / short name / full name | `N` | minute |
  | `D` / `d` | day: number / with suffix (`29th`) | `S` / `A` | second / am-pm |

  Numbers are zero-padded. A sortable file-name stamp: `con(jst(#D,'D:y-M-D'),'_',jst(#T,'T:H-N-S'))` → `2026-08-29_10-13-36`.

### 8.3 Square brackets

Three different mechanisms share the character.

- **In a command argument, `[expr]` substitutes the value of any expression:** `Save class [con($clib().$name,'.Tool')]`.
- **In a notation path, `[x]` substitutes a VARIABLE, not an expression:** `group.[n]`, `ref.[seg]`. `ref.[val(seg)]` is refused by the compiler; `$root.$libs.[$clib.$name]` resolves to nothing without an error. Compute into a variable on the line before.
- **Inside a string literal, `[expr]` is evaluated when the string is built** — in `Calculate`, in `OK message`, and when a line is assigned as method text. `'a [x] b'` does not stay literal. A literal opening bracket is detached from the literal: `con('a ','[','x] b')` or `chr(91)`; the closing `]` alone is harmless.

### 8.4 Regular expressions

- **`rxpos(rx,str,igncase,words,mchlen[,captureRow])` uses PCRE2.** It returns the 1-based position (0 = no match) and sets `mchlen`. Parameter 3 ignores case when kTrue, parameter 4 matches whole words. All matches are found by searching again after `position+mchlen`. Forms that ran: `\b`, `\s`, `(?:…)` with alternation, `(?<n>…)`, `(?P<name>…)` read as `captureRow.name`, look-ahead, `[^#\w$]|$`, `^` on `mid(str,offset)`.
- **`rxreplace` and `rxreplaceall` do not exist in Studio 10.x.**

### 8.5 Names

- **`flag` is command grammar** (`If flag true`). A local called `flag` can be declared and written, but `If flag` is refused, and one such line makes `$methodtext.$assign` refuse the whole body.
- **Thirteen names cannot be used for custom notation:** `$add`, `$assign`, `$canassign`, `$chaincount`, `$default`, `$findname`, `$ident`, `$isinherited`, `$makelist`, `$name`, `$ref`, `$serialize`, `$wind` (help). Any other custom method with the name of a standard one overrides it.
- **Variable names:** Unicode letters, digits, U+80 to U+FF and `_`; not a digit first; no `.` `$` `&` `(` `)` `[` `]` `#` or space (help). There is no reserved-word list for variables.
- **A class name may hold almost any character,** so it cannot be found by whole-word search. Treat the code separators as boundaries; `[\w$]+` is a practical token pattern.

---

## 9. Lists

- **`$define(a,b)` takes VARIABLES; `$cols.$add('name',type,subtype,length)` takes a string.** `$define` borrows name and type from variables that must exist in scope, or the line is refused. A list is extended by columns with `$cols.$add`. `$define()` plus one `$cols.$add` per column builds a list with fresh columns.
- **`$cols.$add` with an EMPTY subtype creates no column, silently,** for `kInteger` (needs `k32bitint`) and `kNumber` (needs `kFloatdp`). Every later access to the column raises 25207. `kBoolean` and `kItemref` accept `''`.
- **`$define` clears a list, `$redefine` keeps its lines.** A list reused for a second measurement with `$redefine` carries the first one's rows.
- **`list.$search(kFalse)` deselects every line** (author). It does not leave `$line` alone: deselect first, then set `$line` and `$selected`.
- **`$remove(kListDeleteSelected)` removes every selected line.** In a list shown in a field the line the user clicked is selected as well.
- **A row and a column by index, inside an expression:** `list.[n].col`, `list.[row].[col]`. The column number is the definition order; in a headed list whose columns the user may drag (`$candragdisplayorder`), the display order differs.
- **A list field's `$calculation` may call an instance method,** once per drawn line: `con(style(kEscBmp,$cinst.$icon(list.mark)),' ',list.c1)`. The method reads its row by index and leaves the `$line` of every displayed list alone.

---

## 10. Windows, fields and events

### 10.1 Objects in a window class

- **`$objs.$add(type,top,left,height,width[,invisible,disabled])`** — top before left, height before width, and no name: `Set reference ref to cls.$objs.$add(kEntry,131,12,22,300)`, then `ref.$name.$assign('efFind')`. `$objs.$add(objectRef)` copies an existing object.
- **On a tab pane, every `$add` takes the PANE NUMBER first:** `tabpane.$objs.$add(pane,kSubwindow,top,left,height,width)`, then `$classname`; `$bobjs.$add(pane,type,…)` likewise. Without it the generic signature produces the wrong object. `kSubwindow` is 13.
- **The tab strip:** `$tabcount` is assignable; `$tabcaption` is the caption of the CURRENT tab, so set `$currenttab` to each tab in turn and assign its caption. `$alltabcaptions` is read-only. `$multirow` takes effect only when switched on AFTER the tabs are set, and `kDefaultPanes` never wraps. In the class, `$panenumber()` and `$getpaneinfo()` read 0 and empty.
- **A headed list box becomes editable only when `$maxeditchars` is set** on the object (author). Which columns may be edited is decided in `evHeadedListEditStarting` (`pColumnNumber`).
- **`$tooltip.$assign(text)` on a design object stores plain text.** An open window has its own copies of the objects: a tooltip written into the instance object shows at once, one written into the class only when the window is opened again.
- **Whether a handler can fire is decided by a property, not by its body.** An `evDragBorder` handler on an object with `$dragborder` false never runs.
- **`$edgefloat` compared numerically:** `$edgefloat*1=kEFposnClient*1`. A docked pane takes its height from the one sibling floating `kEFposnClient`.

### 10.2 Geometry

- **A field has no OS window of its own.** `$hwnd` and `$framehwnd` of a field, and of a tab pane, group box or subwindow, report the design coordinates. Only the top-level window has a real handle; its own `$top`/`$left` are screen coordinates.
- **An object's position in the window is the sum of `$top`/`$left` up the container chain, plus each container's inset,** which notation does not expose:

  | container | left inset | top inset |
  | --- | --- | --- |
  | subwindow | 2 | 2 |
  | scrollbox | 1 | ~1 |
  | paged pane | 2 | ~2 |
  | group box with title, standard font | 2 | 7, plus ~4/3 px per point of title font size |
  | tab pane, tabs at the bottom | 3–4 | 5 |
  | tab pane, tabs at the top | 4 | 35 |

  `$tabstyle` does not change it; `$taborient` does. A group box's own properties count only once `$fieldstyle` is cleared.
- **`$container()` skips intermediate containers** and lands on the window or subwindow; `$fullname` still holds every step. A background object (`kBobj`) reports absolute coordinates.
- **`mouseover(kMItemref)` over an empty area of a window returns the window.** Over a complex grid it returns the grid, never a cell.
- **Complex grid:** `$setrowheight(iSz,row,size,curve,duration)` always animates; several calls in one method overlap unless the rows are set from the LAST to the first. `iSz` is `kGridRowSizeCollapse`, `kGridRowSizeExpand` or `kGridRowSizeToggle`. `$getrowheight` does not exist in the desktop client (author); the online page mixes in JavaScript-client members.

### 10.3 Multi-line entry fields

- **`$linecount` and `$vscroll` work without `$vertscroll`** (author). `$vscroll=0` shows the first line.
- **`$linecount` counts DISPLAY lines, soft wraps included** (author). It changes with the field's width and does not match the number of `kCr`. With `$horzscroll` kTrue nothing wraps, and a display line is a text line.
- **`$firstvis`, `$lastvis`, `$firstsel`, `$lastsel`** count characters or lines of the content (help). They exist on the instance only (1.3).
- **Selecting a whole field when a window opens scrolls it to the END.** `Queue keyboard event com-A` after `Queue set current field` does. Setting `$firstsel` 0, `$lastsel` to the length and `$vscroll` 0 in `$construct`, after a queued `Queue set current field`, ends the same way: all selected, scrolled to the end (author; which of the two scrolls is not separated). `Queue click field (0,0)` in `$construct` leaves the cursor at the start of the text with nothing selected (author, macOS).

### 10.4 Events and focus

- **A window opened at a stored size gets no `evResized` for it** (author). Layout work from `evResized` must also run in `$construct`, where floated fields already have their floated size.
- **Dragging a window's edge sends ONE `evResized`, at the end of the drag** (author).
- **A pushbutton that can take the focus makes the edited field get `evAfter` BEFORE the button's `evClick`.** Whatever the field does on `evAfter` has happened when the button runs.
- **`Queue set current field` on an invisible field does nothing** (author).
- **A radio button can change its value without `evClick`.** With a method editor in front, the first click on a radio of the window behind only brings the window to the front, and the radio keeps its value. The next click on the radio changes its value and sends `evBefore` and `evAfter`, but no `evClick`; clicked once the window is in front, the same radio sends `evClick`, `evBefore`, `evAfter`. Measured with a trace line in the radio's `$event` (2026-10-14). Code that must follow every change of a radio reacts to `evMouseUp` as well, and guards itself against running twice: `On evClick,evMouseDown,evMouseUp` with `If cView<>2` before the work (`ExecutorConsole.rbViewJump`).
- **A field event goes to the field's `$event`, then to the window instance's `$control`, then to the task's `$control`,** when the field has no `$event`, does not handle the event, or passes it on (help).
- **An object added to an INSTANCE works with its own `$event`:** `instobj.$methods.$add('$event')`. Without a method its click reaches no handler, not even `$control`, until the object has been looked at in the editor (author).
- **`$norefresh` held over a change that resizes fields shows their text stretched** until the new size is drawn (author, macOS).

### 10.5 Timers and synthetic keys

- **`$useseconds` kFalse: `$timervalue` is in milliseconds** (help). `#CT` counts ticks of 1/60 s since system start and wraps after about 414 days: build differences with `abs()`.
- **Timer events do not fire while the debugger holds the context** (Go from the method editor). Started from a menu, code returns to the idle loop and timers fire.
- **After synthetic key events into an IDE window, an object timer starves** until a real event arrives. An open 4GL window kept offscreen keeps timers serviced. Worker objects do not help: their callbacks run on the main thread.
- **Two notations for keys.** Editor shortcuts (`Cmnd+Shift+Opt+X`) and `Queue keyboard event` strings (`shift-com-x`) differ in names, separator and order; a wrong string is a runtime error. Modifier bits: 65536 Cmnd/Ctrl, 131072 Shift, 262144 Opt/Alt; the Mac Control key has none. F1–F12 are codes 1–12.
- **Synthetic keys do not reach every window.** The Property Manager never receives them; the method editor does. One key per settled, focused window state: a second key while the first is still rebuilding the window is lost. A modal message right after queueing keys can swallow them.
- **The icon dialog is `$root.$promptforicon(libRef,iconid)`** (help); it returns the chosen id, nothing on cancel.

### 10.6 Colours

- **The fill of a field is `$forecolor`, and only with `$backgroundtheme` kBGThemeNone** (author). `$backcolor` shows only between the dots of a `$backpattern`.
- **A field style can lock colours and fonts** (author): `$hasbackgroundtheme`, `$hastextcolor`, `$hasfontsize`.
- **A pushbutton shows a colour with `$buttonstyle` kUserButton and `$forecolor`** (author).

---

## 11. Libraries, the IDE and the help

### 11.1 Opening libraries

- **Opening a library constructs its startup task.** A copy of a library opened normally runs its own startup code. `Open library (Do not close others,Do not open startup task) [path]` opens it without; `,[name]` gives it a session name of its own, also beside an open library of the same file name. `Create library` needs no option, but the new library carries an empty `Startup_Task` (5.1).
- **The Studio Browser opens a library WITH its startup task** (author), unless Cmnd and Shift are held while it opens (author).
- **`Open library` on a library that is already open does nothing and says nothing** (author). Check `$root.$libs` first.
- **A startup task halts at `Breakpoint` in every design version;** only a runtime runs through (author).
- **Studio 10.22 does not reopen at start a library that was open at shutdown,** unless it lies directly in `startup/` (author). Libraries in subfolders of `startup/` are not opened at start (author). Studio 11 reopens them, controlled by `restoreOpenLibsAtStartup` and `openStartupTaskWhenRestoringOpenLibrary` in the `ide` section of `config.json` (help); the `config.json` of 10.22 has neither entry (author).
- **`Save class [Lib.Class]` saves into a library opened under a session name:** `Save class [con(name,'.Startup_Task')]`.
- **`$prefs.$defaultname` of a library cannot be assigned by notation** (25207), and reading it returns empty although the export has it.
- **The `kLibFlag…` constants do not exist in 10.22;** `$root.$libs.$add(…,kLibFlagDoNotOpenStartupTask)` is refused with 25208. The online help describes Studio 11.

### 11.2 `$findandreplace`

- **`classRef.$findandreplace(find,replace[,ignCase=kTrue,wholeWord=kFalse,regExp=kFalse,clearLog=kFalse])` works on one CLASS.** `#NULL` as the replacement only finds; the Find log fills all the same. It returns a row: `Status`, `FoundCount`, `ReplaceErrorCount`.
- **It reaches properties as well as method text:** an object's `$name` and `$dataname` are found and replaced.
- **`FoundCount` counts log entries, not occurrences:** a line holding the word twice is one entry.
- **A replace count lower than the find count can be complete.** Renaming a variable definition carries the code lines with it (6.6), so those lines are never "replaced". The check is: nothing left under the old name, everything under the new one.
- **With the Find dialog open, a class-wide call routes its log into the dialog, and Omnis becomes very, very slow** (it does not hang). `$root.$prefs.$alloweditifnotcheckedout` must be kTrue. Instances and design editors of the classes touched must be closed: `$insts().$sendall($sendallref.$close())`, with the brackets. An open editor of another class is not in the way.

### 11.3 The IDE

- **An open method editor shows lines arriving live.** After `methodRef.$modify(1)` every `$methodlines.$add` appears at once, and the editor's block check runs along: while an `If` is open, the error count in red changes until its `End If` arrives (author). Take the `$methodlines` reference after opening the editor.
- **`Working message` is not visible beside open method editors** (author). Progress shows in the title of a window that stays in view.
- **`OK message` text holds about 255 characters** (author); `//` breaks a line, `[…]` is evaluated when the message shows.
- **Fields added to a window INSTANCE at run time appear at once:** `instRef.$objs.$add(…)`, properties assigned, `instRef.$redraw()`. Such a field has no methods.
- **`$openonce` on a class with an open instance brings it to the front without running `$construct`.**
- **Instance methods open in the method editor as "Temporary Methods"** (window title), each with a blue dot (author). Edits there are not saved; breakpoints set by hand do not hold; a `Breakpoint` command in the code does stop. Switching to the class design leaves the mode.
- **A temporary instance method opens at a line only through `$cinst.$methods.//name//.$modify(n)`,** and not while it is the method running (author). `$cmethod.$fullname` of an instance method is no usable path.
- **A variable changes scope by dragging it between the panes of the variable window,** when its name occurs once (author). The code keeps working.
- **`$root.$runapplescript(script,&result,&error)` works in 10.22,** 0 on success (macOS).
- **A name search over all classes of all libraries,** `$libs.$sendall($ref.$classes.$sendall(…))`, takes about 40 ms per call with the vaults open. Collect the names once and test with `pos()`.

### 11.4 Measuring time

- **Method-level counters:** `$root.$prefs.$collectperformancedata` (`kCPDnone`, `kCPDmarkedClasses`, `kCPDallMethods`), on a class `$collectperformancedata` kTrue (with `kCPDmarkedClasses`), on a method `$callcount` (only 0 assignable), `$totalexecutiontime`, `$minexecutiontime`, `$maxexecutiontime` in milliseconds. Collecting costs almost nothing.
- **Run times vary by more than ten times with the session's state.** The same sweep took 30 s, 12 s after a restart, then 7.3 → 3.2 → 2.0 s in a fresh session; in a worn session it stays high. Compare only within one run, and restart Omnis before a measurement that matters.

### 11.5 JSON export

- **`$root.$exportjson(libRef,outPath,&errors,&warnings)` writes the library INTO `outPath`,** with no subfolder of its own (the Studio Browser adds one). A folder that already holds a tree is updated, not replaced: one folder per library, made first.
- **On Windows, `outPath` must not end in the separator** (author, 10.22). `C:\…\execExports\Lib\` fails with 23455 `Parameter 2 of $exportjson() must be the pathname of an existing folder`, although `FileOps.$createdir` made that folder the line before; the same path without the trailing `\` exports. On macOS both forms export. Write `outPath` without a trailing separator; a file inside it is then `con(outPath,sys(9),'library.json')`.
- **A method line that does not survive tokenise → untokenise fails the export** (23470): `$exportjson` returns kFalse with one error row per line. Every case seen is a line that does not compile in the session of the export, and would be refused if it were assigned anew (author): `If flag` (lore 8.5), `Print report (iReportList)` with the variable unknown, calls on an external object that is not loaded; lines holding double-quoted strings together with constants of an external component (`kOWEB…`, `kAV…`) failed as well, and which of the two is to blame is not separated, most likely the constants of a component that is not loaded. A line naming a library that is not open fails the same way: the export reports it, leaves that class out and writes the others (author). So the self-assignment of 6.5 should find these lines before the export does; measured only for `#???` lines.
- **A `#???` line (a removed variable, 6.6) fails the export with 23470, one error row PER LINE.** Six such lines in one method gave six rows; the error text is `See find and replace log: Invalid method line - tokenizing and untokenizing the method line does not result in the same text: <the line as stored>`. The text names neither class nor method; the first column of the row, read by position, held `1`. Turning each of those lines into a comment frees the export of that library.
- **A 23470 failure still writes the WHOLE tree.** The tree of `jsonfix_probe v1` step 3 (export NO, six 23470 rows) holds the broken class beside the five other classes and the system classes (whether these were all the classes of the library was not recorded), and its method file carries the six lines as stored, `Calculate #??? as 'a'`. "Export failed" here means "reported", not "missing". Such a tree does NOT import again (below).
- **A missing superclass writes NOTHING.** A class whose superclass lies in a library that is not open fails with 23452 `Cannot export class because its superclass '<Lib.Class>' is not available`, one row per such class; the target folder stays empty, not even `library.json` (`jsonfix v2` on a library with eight such classes, 11:10).
- **An `End If` whose `If` has been commented does not stop the export.** Omnis checks line by line (6.2); the orphan fails only when the method runs.
- **A class-variable definition's `$userinfo` travels in the export,** as does the library's `$userinfo` (`library.json` → `properties` → `userinfo`).
- **An export of a library opened without its startup task can raise 25216 and still return kTrue with no error rows;** the tree was complete. Seen once on a sample library; then 25216 on each of three calls on a scratch library opened without its startup task: two returned kTrue with no error rows, the third kFalse with rows of its own (23470). The 25216 does not mark a failed export; the cause is open. Seen again on a copy of the Executor opened without its startup task: two exports in a row from the same open library, each with one 25216, both kTrue with no error rows; the first tree imported again into a library whose classes, stored log and start guard read back as built, and which passed a smoke test.
- **A library never gives freed space back to its file.** Studio 10.22 has no Compact in the IDE.
- **`$root.$importjson(jsonFolder,newLibPath)` builds a library from a JSON tree.** It returns kTrue, writes the file and does NOT leave the library open. A library rebuilt this way carries no dead space: 7 710 720 → 686 080 bytes. A third argument, an error list, is accepted as well; the method is reported with 2 to 5 parameters.
- **A tree with a `#???` line does not import.** `$importjson` returns kFalse and writes NO file; the error list has four columns, the first the path of the file, then the code and the text: `…/wImportBroken/methods.json 23522 Error setting method text: $probe (Unrecognized variable name, item name or attribute)`, with the line on the next line of the text. The same import reported 23476 `Internal error: Invalid attribute passed to getExporterValue() or setImporterValue():287` for `wJsonExport/objs/hlLibs/object.json`, a headed list box of another class; whether that row alone would stop an import is not separated (`jsonimport_probe v1`, 11:58). So a library is rebuilt from JSON only after its broken lines are commented (`jsonfix`).
- **A tree with ONE class imports.** Every class folder deleted but one, `library.json` kept: `$importjson` returns kTrue, the new library holds that class with its methods and the 17 system classes, also when the folder `System Classes` was deleted as well. The class carries an empty `New Method` beside its own (Omnis adds it to every new class). A class can therefore be rebuilt from a partial tree, through a library of its own.

### 11.6 Constants

- **`$root.$constants` holds about 2000 constants,** in named groups: `Do $root.$constants.$makelist($ref,$ref.$name) Returns list`. `$constant('kName')` reads one value. The group lists are in the help under `notation/root/constants/`.

### 11.7 The help

- **The unpacked help is the primary source.** `commands/groups/<group>/<command>.htm` for commands; `notation/root/libs/lib/windows/window/objs/<type>.htm` for class properties, `notation/root/iwindows/window/objs/<type>.htm` for instance properties; `notation/root/constants/` and `notation/root/hashvars/`. `notation/misc/generic.htm` holds the generic members (`$cando`, `$canassign`, `$attributes`, …), which no walk of the notation tree reaches.
- **`notation/…` and `functions/…` are separate trees with different members.** `FileOps.$deletefile` is only under `functions/groups/fileops/`. Finding nothing in one tree proves nothing.
- **Two help folders ship:** `idehelp` (all commands, functions and notation) and `jsidehelp`, its subset for code that runs in the JavaScript client (125 of 517 commands, 320 of 326 functions); pages present in both are the same.
- **`$lib()`, `$class()`, `$inst()` work and are not in the help** (2.4).
- **The help pages of an object type mix in JavaScript-client members** (10.2, `$getrowheight`).

---

## 12. Files

- **There are two `FileOps`.** The static function group works on the file SYSTEM: `FileOps.$createdir`, `$doesfileexist`, `$deletefile`, `$filelist`, `$splitpathname`, `$getfileinfo`, `$readentirefile`, `$writeentirefile`, `$rename`, `$movefile`, `$copyfile`, `$parentdir`, `$selectdirectory`. An object variable of subtype FileOps works on ONE open file: `$createfile`, `$openfile`, `$readcharacter`, `$writecharacter`, `$readfile`, `$writefile`, `$closefile`, `$isopen`, `$getlasterror`, `$setposition`, `$getfilesize`. A method of one called on the other raises 125207.
- **The static methods return an ERROR CODE, 0 = success.** `$createdir` answers 101215 when the folder exists. Ask the file system afterwards (`$doesfileexist`) rather than reading the return as a flag.
- **`FileOps.$deletefile(path[,deleteContents=kFalse,recursive=kFalse])` deletes for good** — no trash (help). It deletes folders too: empty ones directly, full ones with `deleteContents`, subfolders with `recursive` as well.
- **`$createfile` does not create a missing folder.** Create it with `FileOps.$createdir` first.
- **Text written with `$writecharacter(kUniTypeUTF8,…)` reads back unchanged** with `$readcharacter(kUniTypeUTF8,…)`, `kCr` line ends included (macOS).
- **`FileOps.$copyfile(from,to)` copies the file of an OPEN library on macOS,** completely; the target must not exist yet.
- **On macOS the save dialog of `FileOps.$putfilename` does not show its prompt text** (author). Windows not measured.
- **`FileOps.$getfilename` with a LIST as first argument, and `FileOps.$isdirectory` / `$isfile`, came with Studio 11.1** (help); 10.22 does not have them. The filter is pairs of description and pattern, separated by `|` (help).

---

Copyright (c) 2026 Udo Sonnabend (USO-FT). This text is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/): you may share and adapt it, also commercially, if you name the author, link the source and the license, and say what you changed. Code examples in this text may also be used under the MIT License, without attribution in your code. Source: https://github.com/uso-ft/omnis-executor
