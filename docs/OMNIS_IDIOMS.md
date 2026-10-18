# Omnis idioms — patterns from working code

How working Omnis code does the recurring things. Every pattern below was read out of working, checked code; the call sites are real. Sections 1 to 18 come from `Executor.lbs`, which ships with this file (§8 names its own source); every later part names the library it comes from. `spread` = number of distinct methods the pattern occurs in. Spread, not raw count, is the signal: twenty hits inside one method is one decision, five hits across five methods is a house rule.

This file is for writing code that reads like the rest of the library. It is not a language tutorial — for what a token means, see the Omnis help; for measured behaviour, see `OMNIS_LORE.md`.

---

## 1. Walking an object group

Groups are walked with `$first()` / `$next(current)`, never by index. The loop guard is `not(isclear(ref))` — an exhausted `$next()` yields an unset reference, not zero.

```
Set reference node to pNode.$objs.$first()
While not(isclear(node))
    ...
    Set reference node to pNode.$objs.$next(node)
End While
```

`$bobjs` (background objects: lines, frames, labels) is a **separate group** and needs its own identical loop. Code that walks only `$objs` silently misses them. Background objects are usually nameless.

## 2. Descending a class tree

`$objs` yields exactly one level. There is no flat view of a class, so recursion is mandatory. The recursion condition is **structural, not type-based**:

```
If node.$objs.$count>0
    Do $cinst.$collectObjects(node,pList,lvl+1,path)
End If
```

Asking `$objs.$count>0` cannot go stale when a new container type appears, and it avoids `$objtype`, whose string form is ambiguous. Do not hardcode a list of container types.

## 3. Optional parameters carry recursion state

The **absence** of an optional parameter marks the entry call, which is where the output list gets defined and cleared. A recursive call always passes them explicitly, even at level 0.

```
If isnull(pLevel_opt)
    Do pList.$define()
    Do pList.$cols.$add('objRef',kItemref)
    ...
    Do pList.$clear()
    Calculate lvl as 0
Else
    Calculate lvl as pLevel_opt
End If
```

## 4. Building a list

Two forms, both in use:

```
Do list.$define(ref,version,moddate)            ## from existing variables
```
```
Do pList.$define()                              ## empty, then columns by hand
Do pList.$cols.$add('objName',kCharacter,kSimplechar,255)
Do pList.$cols.$add('level',kInteger,k32bitint)
Do pList.$clear()
```

`$cols.$add` takes `(name, type [, subtype [, length]])`. Character columns carry `kSimplechar` plus a length; integers carry `k32bitint`; `kItemref`, `kBoolean`, `kRow`, `kList` take no subtype. When the return value is not wanted, the house form is `Returns #F`.

## 5. Redefining a variable: remove, then add

Adding a variable that already exists fails. The idiom is unconditional remove followed by add — idempotent, and correct on both the first and the hundredth run.

```
Do [#S1].$remove([#S1].$findname('targetRef').$ref)
Do [#S1].$add('targetRef',kItemref) Returns #F
```

Note `.$ref` on the `$findname` result: `$remove` needs the item, not a copy. `[#S1]` is square-bracket substitution — the bracketed expression is evaluated and the result used as notation.

## 6. Turning a string path into a reference

Square brackets evaluate; `.$ref` binds. This is how a computed path becomes something you can navigate.

```
Calculate path as con(ref.$class().$fullname,'.$objs.',relPath)
Set reference ref to [path].$ref
```
```
Quit method $libs.[library].$classes.[pClassName].$ref
```

## 7. Guarding a reference

Three distinct guards, used for three distinct reasons:

```
If pfRef.$objectpath.$cando          ## does this accessor exist at all?
If not(isclear(node))                ## is this reference bound?
If classRef.$methods.$findname(name) ## is there such a member?
```

`$cando` is the only one of the three that does **not** execute the prefix — that is its whole purpose. Everywhere else, evaluating a reference chain executes its intermediate `()` links.

## 8. Re-resolving a reference after it has travelled

From the masterstudio framework, kept in `Tool.$cleanUpRef`. A reference that was not passed cleanly comes back as a **copy** of the instance — visible as an instance name starting with underscores (`____42134_EntityCtr`). The fix is to re-resolve from the object's own path.

The path is not an Omnis property. The object class keeps it itself, and `$cleanUpRef` asks for it in two ways: the method `$objectpath()` where the class has one, the instance variable `iObjectpath` otherwise, each tested with `$cando` first. An object class that wants this idiom has to carry one of the two and fill it when the instance is made:

```
If len(objectPath)
    Set reference pfRef to [objectPath].$ref
End If
```

Same shape appears after a `$remove`: the surviving references are stale, so re-resolve rather than reuse.

## 9. `$container()` is not the parent

`$container()` **skips** intermediate containers and jumps to the enclosing window or subwindow. For the true one-level-up owner, go through the group:

```
If pRef.$group().$obj().$class      ## owner is a Container field or Subwindow
    Set reference ref to pRef.$group().$obj()
Else If pRef.$group().$wind().$class ## owner is a window
    Set reference ref to pRef.$group().$wind()
End If
```

`$group().$name` also tells you which group a reference came from (`'$objs'` vs `'$bobjs'`).

## 10. Querying all libraries — nested `$sendall`

The house search is a nested `$sendall` whose second argument is the filter, collecting into a list, then sorting to pick a winner. No loop.

```
Do $libs.$sendall($ref.$classes.$sendall(list.$add($ref,$ref.$version,$ref.$moddate),upp($ref.$class().$name)=upp(pClassName)))
If list.$linecount
    Do list.$sort($ref.version*1,kTrue,$ref.moddate,kTrue)
    Quit method list.1.ref
End If
```

Inside `$sendall`, `$sendallref` (or `$ref` in the older form) is the current item. `*1` forces a numeric sort on a value that may be text.

## 11. Failure channels

The library separates three severities and never mixes them:

| situation | form |
|---|---|
| expected miss, user should notice | `Sound bell` |
| programming error, must stop | `Breakpoint` then `OK message` |
| recoverable, nothing to do | `Do 1 ## <reason>` |

`Do 1` is a deliberate no-op. Omnis has no empty branch, so the reason for doing nothing goes in the comment — and it always does:

```
Do 1 ## can't assign, debugging purpose only
Do 1 ## Setting $height for kComplexgrid makes no sense here
```

A `Breakpoint` immediately before an `OK message` is intentional: it stops in the debugger during development and is harmless at runtime.

## 12. Error handler installation

Loading the error handler is wrapped in a reversible block, so it is unloaded automatically when the method exits.

```
Begin reversible block
    Load error handler Startup_Task/$handleError
End reversible block
```

The same wrapper is the flicker guard for display work:

```
Begin reversible block
    Calculate $cwind.$norefresh as kTrue
End reversible block
```

Executor.lbs no longer uses this guard: held over a change that resizes fields, `$norefresh` shows their text stretched until the new size is drawn (`OMNIS_LORE.md` 10.4).

Reversible means: whatever is set inside is restored on method exit. Use it for anything you would otherwise have to remember to undo.

The full behaviour is `OMNIS_LORE.md` 7.4, and two things there are worth knowing before writing one of these: `Calculate x.$prop as v` is reversible while `Do x.$assign(v)` is NOT, and the restore captures at the FIRST write inside the block, not at the last.

## 13. Method exit

Methods have a single fall-through exit at the bottom, and guarded early exits above it. The bottom exit returns the empty/false value, so a caller that gets nothing knows the search failed.

```
    If <found>
        Quit method <result>
    End If
End If
Quit method ''
```

Boolean-returning methods use `Quit method kTrue` / `Quit method kFalse`, not 1/0.

## 14. Event handling on window objects

```
On evClick
    Process event and continue
    Do $cinst.$handleExpand($cfield)
```

`Process event and continue` lets Omnis complete the default behaviour first; without it the field's own state is not yet updated when your code runs. Object logic delegates to a window-class method rather than being written in the object — `$cinst.$something($cfield)` is the house shape.

## 15. Object state stored in `$userinfo`

`$userinfo` is the per-object scratch slot the library uses to remember things across events (here: the height a container had before it collapsed).

```
Calculate minHeight as $cfield.$container().$minHeight
Calculate lastExpandedHeight as $cfield.$userinfo
If isclear(lastExpandedHeight)
    Calculate lastExpandedHeight as minHeight
End If
Calculate toHeight as max(minHeight,lastExpandedHeight)
```

Note `isclear()` as the "never set" test on a scalar — that use is sound. (As a *group* emptiness test it is not; a group is empty when `$count` is 0, `OMNIS_LORE.md` chapter 4.)

## 16. Assigning through a chain

Two equivalent forms are in the code. Prefer the `.$assign()` form when the chain is navigated; `Calculate` is used when the target is a plain property.

```
Do $cfield().$container().$height.$assign(toHeight)
Calculate $cfield.$height as $cfield.$height-diffHeight
```

## 17. Text scanning

Method text is scanned with `pos` / `mid` / `con`, line by line, after splitting on `kCr`:

```
Calculate lines as split(pText,kCr,kTrue)
For loop from 1 to lines.$linecount step 1
    Calculate oneLine as lines.[loop].C1
    If pos('##',oneLine)
        Calculate oneLine as mid(oneLine,1,pos('##',oneLine)-1)
    End If
    ...
End For
```

`replaceall` is used to reduce a string to a shape before comparing:

```
Calculate shape as replaceall(shape,'0','d')
```

Two things that bite here, both already paid for: `$methodtext` carries **no indentation**, so multi-line patterns containing tabs never match; and a caller may already have stripped comments (`$stripComments`) before handing text on — check before stripping again.

## 18. Comments carry the contract

Every non-trivial method in this library opens with a comment block stating purpose, parameters, return value, and — most valuably — *why* the implementation is shaped the way it is. This is not decoration: it is where the measured behaviour lives, and it is the reason a rebuild was avoidable in five past cases. Write new methods the same way, and **read the first comment line before building anything** (`library_api.md` lists them all).

---

# Variants and additions — from the Omnis Support `notation` library (c. 2000)

The sections above are the Executor house style. Below is what a second, independent, much older codebase does differently or does at all. Where the two disagree, both forms are recorded: a disagreement between two working codebases is information, not an error to resolve.

## 19. Group iteration — the older `Do … Returns` form

Omnis Support writes the same loop as §1 with a different call convention and a bare truth test instead of `isclear`:

```
Do List.$first() Returns itemref
While itemref
    Calculate ListLineValue as itemref.Col
    Do List.$next(itemref) Returns itemref
End While
```

Both forms work. Prefer the Executor's `Set reference node to …$first()` with `not(isclear(node))`: it states that the variable is a reference, and it does not rely on an unset reference evaluating false. Recognise this form when reading old code.

Note also `itemref.Col` — an item reference to a **list line** is used exactly like `List.2`, so columns are addressed straight off the reference.

## 20. Why item references exist — the measured reason

`wHOWTO_3` benchmarks it directly: 1000 iterations assigning `$forecolor` through the full path `$cinst.$bobjs.1017.$forecolor` against the same assignment through a reference set once. The path is re-resolved on every single evaluation.

```
Set reference MyRef to $cinst.$bobjs.1017
For num from 1 to 1000 step 1
    Do MyRef.$forecolor.$assign(kGreen)
End For
```

The rule that follows: **any path evaluated more than twice in a loop should be a reference.** Measure with `#CT` (ticks) if in doubt — the library does.

## 21. `$attributes` — the runtime replacement for the help

This is the single most useful thing in the Support library. Any item's complete property set, with assignability and the **description text**, is available at runtime:

```
Calculate AttList as $cinst.$attributes.$makelist($ref.$name,$ref.$canassign,$ref,$ref.$desc)
Calculate AttList as $cclass.$attributes.$makelist($ref.$name,$ref.$canassign,$ref,$ref.$desc)
```

`$ref.$desc` returns the same one-line description the Property Manager shows. So when the help is ambiguous about whether a property exists on a given item, or whether it can be assigned, this answers it **for the actual object, in the actual Omnis version** — which the help cannot. `$cinst.$attributes` and `$cclass.$attributes` give different sets; ask the one you mean.

Two things the list is not (`OMNIS_LORE.md` 3.1):

- **It is not only properties.** Groups (`$objs`, `$methods`) and methods (`$add`, `$open`) are in it as well, and every name carries its `$`.
- **`$attributes.$findname('$x')` returns the VALUE, not the attribute.** The item is `unnamed_value`, and a value of 0 or empty comes back clear, so it cannot tell an attribute that is 0 from one that is missing. To ask whether an item has an attribute, search the list: `Do ref.$attributes.$makelist($ref.$name) Returns list`, then `list.$search(low(list.c1)=low(name),kTrue,kFalse,kFalse,kFalse)`.

## 22. `$makelist` and `$appendlist` on any group

Every group answers `$makelist`, so a group becomes a list in one line:

```
Do $classes.$makelist($ref.$name,$ref.$classtype) Returns List
Do $windows.$makelist($ref.$name,$ref.$classtype) Returns List
Do $components.$makelist($ref.$name) Returns List
```

`$appendlist` adds rows to an **existing** list, target list first:

```
Do $tasks.$makelist($ref.$name,$ref.$classtype) Returns List
Do $files.$appendlist(List,$ref.$name,$ref.$classtype,$ref.$moddate)
```

**Constraint, stated in the library's own comment:** `$appendlist` cannot add new columns to the target list. The extra `$ref.$moddate` above has nowhere to go. Define the widest shape first with `$makelist`, then append.

## 23. `$ref` vs `$sendallref` inside `$sendall`

The old library uses `$ref` as the current item inside `$sendall`; the Executor uses `$sendallref`. **`$ref` is ambiguous** (author): in `$sendall(myList.$search($ref.c1='XY'))` it can mean the item of the `$sendall` or the line of the list being searched. `$sendallref` means the item of the `$sendall` and nothing else.

```
Do $cinst.$objs.$sendall($ref.$forecolor.$assign(kGreen),$ref.$objtype=kPushbutton)   ## old
Do containerTree.…$objs.$sendall($sendallref.$visible.$assign(kTrue),$sendallref.$objtype=kScrollbox)   ## current
```

Write `$sendallref` in new code. `$ref` inside `$sendall` still appears throughout the older library. On its own, in the arguments of `$makelist` or `$search`, `$ref` is the item being listed or searched, and there it remains the correct token.

## 24. Passing a reference into a method

A field-reference parameter is valid **only inside the receiving method**. To outlive the call it must be copied into an item-reference variable:

```
Do method PassItemRef ($cfield)
    # inside:
    Do pRef.$forecolor.$assign(kRed)
    Set reference lReference to pRef     ## required to keep it
```

This is the same failure family as the copy-instead-of-reference case in `OMNIS_LORE.md` 7.5: a reference that is not explicitly bound does not survive.

---

# Runtime introspection — asking Omnis instead of the help

The help documents this on one page that is easy to miss: `notation/misc/generic.htm`, "Generic". It lists the properties and methods that apply to **almost any item**, including any property and any method reached by notation. This is the most direct answer to "does this exist here, can I assign it, what does it take" — and it answers for the running version, which the help cannot.

## 25. The generic introspection surface

| token | what it gives |
|---|---|
| `$desc` | the item's description — the same line the Property Manager shows |
| `$cando` | is this notation attribute implemented for this item, **without executing it** |
| `$canassign` | can the item's value be altered, in the current context |
| `$attcount` | number of built-in attributes belonging to the item; more than `$attributes.$makelist` lists (`OMNIS_LORE.md` 3.1) |
| `$attributes` | the group of built-in **and custom** attributes |
| `$att(n)` | the n'th of the `$attcount` attributes, from 1; `$att(n).$name` is its name. Not the order of `$attributes` (`OMNIS_LORE.md` 3.1) |
| `$minparms` / `$maxparms` | minimum / maximum parameter count **when the item is called as a function** |
| `$type`, `$subtype`, `$sublen` | the item's data type |
| `$isinherited` | is this attribute inherited from the superclass |
| `$default` | reach a built-in attribute that a custom attribute has overridden |
| `$canomit` | may this attribute be left out of the notation |
| `$chaincount` / `$chain(n)` | walk the reference chain of a reference variable, says the help. Measured: `$chaincount` is 1 on every reference tried, `$chain(0)` is the item itself, `$chain(1)` and up return nothing — no use found (`OMNIS_LORE.md` 3.1) |
| `$fullname`, `$group`, `$class`, `$lib`, `$inst`, `$obj`, `$method`, `$wind` | where the item sits |

`$minparms`/`$maxparms` are the point: they only make sense for something callable, so **methods are items too**, and a method's arity is readable at runtime.

## 26. Reference a method, do not call it

```
Do ref.$objs.$add.$desc         ## reads the description of the $add METHOD
Do ref.$objs.$add().$desc       ## CALLS $add with no arguments first — mutates
```

The brackets are the difference between asking about a method and running it. For a method that adds, removes or assigns, that difference is destructive. Use `$cando` when even resolving the prefix would be unsafe: `$cando` is the one test that does not execute what it tests.

```
If not([testExpr].$cando)   ## term cannot be evaluated here → chain is unsafe
```

`Tool/$prototypeExprIsSafe` builds the prefix **without** the trailing bracket pair for exactly this reason, then `$cando`-tests each growing prefix.

## 27. Enumerating attributes — four things that bite

From `NotationBrowser/$appendNodes`, which is working code and states each of these in its own comments:

```
If itemRef.$first.$cando                       ## true ONLY for groups → group vs leaf
    Calculate list as itemRef.$makelist($ref.$name,$ref.$canassign,kTrue,$ref.$ref)
Else If itemRef.$attcount>1
    Calculate list as itemRef.$attributes.$makelist($ref.$name,$ref.$canassign,$ref.$first.$cando,$ref.$ref)
    Do list.$add('$desc',itemRef.$desc.$canassign,kFalse,itemRef.$desc.$ref)
    Do list.$add('$userinfo',itemRef.$userinfo.$canassign,kFalse,itemRef.$userinfo.$ref)
    Do list.$search($ref.name='$attributes',kTrue,kFalse,kTrue,kTrue)
    Do list.$remove(kListDeleteSelected)
End If
```

1. **`$first.$cando` is the group test.** True only for groups, so it separates a group from a leaf without knowing either one's type.
2. **`$next` does not work with attributes.** The `$first`/`$next` walk of §1 fails here; you must go through `$makelist`.
3. **`$desc` and `$userinfo` are often missing from the makelist** and have to be added by hand.
4. **`$attributes` appears inside its own makelist** and has to be removed, or the tree recurses into itself.
5. **Groups and methods are in the list too** (§21). The `$first.$cando` column marks the groups; nothing in the list tells a method from a property.

## 28. The complete vocabulary

`#NULL.$attributes` enumerates attributes with no item to anchor to — the global list rather than one object's:

```
Calculate AttList as #NULL.$attributes.$makelist($ref.$name,$ref.$canassign,$ref,$ref.$desc)
```

Per-item forms, all from `wHOWTO_32`:

```
$cinst.$attributes            ## the open instance
$cclass.$attributes           ## the class
$root.$attributes             ## the root
ref.$objs.$attributes         ## a group
ref.$objs.Col2.$attributes    ## one object inside it
```

These return **different sets**. Ask the one you mean.

---

# From a large application library (live code only)

The library is twenty years old and roughly half of it is unreachable from any menu. What follows comes only from the 505 methods that a menu, task or toolbar can actually reach, with the post-`Quit method` snippet store excluded, because it was never executed.

## 29. Filtering a list without copying it

`$filter` restricts a list to rows matching an expression; `$unfilter` restores it. The rows are not removed, so this is cheaper and reversible.

```
Do iList.$filter(pos(pSearch,$ref.C2)>0)   ## by expression
Do iList.$filter(iList.$selected)          ## by selection
Do iList.$unfilter()                       ## restore
```

Prefer this to `$search` + `$remove` when the full list is still needed afterwards. `$search` + `$remove(kListDeleteSelected)` is destructive; the Executor uses that form throughout because it never needs the rows back.

## 30. Cloning a list definition

Copying columns from one list to another, complete with type, subtype and length, is one statement:

```
Do #L1.$cols.$sendall(#L2.$cols.$add($sendallref.$name,$sendallref.$coltype,$sendallref.$colsubtype,$sendallref.$colsublen))
```

Note the `$col*` family — `$coltype`, `$colsubtype`, `$colsublen` — read off a column item, distinct from the `$type`/`$subtype`/`$sublen` of a variable definition. The Executor uses the latter via `.c1()`; both work, and mixing them is a common source of empty values.

To capture a definition as data rather than apply it:

```
Calculate columns as pfOriginalList.$cols.$makelist($ref.$name,$ref.$coltype,$ref.$colsubtype,$ref.$colsublen)
```

## 31. Marking a task as IDE tooling

```
Do $ctask.$isIDE.$assign(kTrue)      ## in the startup task's $construct
If not(wRef.$task().$isIDE)          ## everywhere a sweep must skip the tools
```

Any tool library that walks `$iwindows` and changes state needs this, or it disables itself halfway through. Set it once in `$construct` of the startup task; test it in every global sweep.

## 32. Walking open window instances

```
Set reference wRef to $iwindows.$first()
While wRef.$class
    ...
    Set reference wRef to $iwindows.$next(wRef.$ref)
End While
```

The guard is `wRef.$class` — an instance always has a class, so this is the "still a valid instance" test, the `$iwindows` counterpart to §1's `not(isclear(node))`. Note `$next(wRef.$ref)`, not `$next(wRef)`.

`$topwind` gets the frontmost window directly, without the walk:

```
Set reference classRef to $topwind.$class
Calculate #S1 as $topwind().$name
```

## 33. Opening a class instance

```
Do iTools.$classRefOfName('ToolEditXMLTags').$open('*')
Do iTools.$classRefOfName('ToolEditXMLTags').$open('*',kWindowNormal)
Do $cinst.$class().$open('*',kWindowStack,pObjRef,,,kTrue) Returns ref
```

`'*'` as the instance name lets Omnis generate a unique one — the right default unless you intend to reuse a named instance. Later parameters are the window mode and then the parameters passed to `$construct`; empty positions are left blank, as in the third line.

## 34. Prepared SQL statements

```
Set reference iStatementRef to iSessionRef.$newstatement()
Do statement.$prepare() Returns #F
```

`$newstatement` comes off the session; `$prepare` then `$execute` then `$fetch`.

---

# Parallel trees and lists — from the Performance Analyzer

395 methods, 3061 code lines. Small, but it contains the most complete treatment of one problem in the whole set: **keeping a tree control and the lists behind it in step**, including two trees synchronised with each other. Every pattern below is from `Result/$buildVisualTree`, `wResultViewer/doubleClickTree`, `wResultComparison/synchronizeClickFromTo` and `Result/$applyDifferencesToTrees`.

## 35. Build a tree from flat parallel lists, not from a nested structure

Three flat lists — library, class, method — each holding its parent's key as a column. The hierarchy is produced at build time by searching the child list for the parent's key, not stored as nesting:

```
Do pTreeObj.$clearallnodes()                       ## blank slate first

Do pTreeObj.$add(con(kTreeSpace,"Overall"),TreeIdent,DataRow) Returns OverallNode

Set current list iTreeResultLibraryList
For each line in list from 1 to #LN step 1
    Do DataRow.$assignrow(iTreeResultLibraryList,kTrue)
    Calculate TreeIdent as TreeIdent+1
    Do OverallNode.$add(con(kTreeSpace,iTreeResultLibraryList.Library),TreeIdent,DataRow) Returns LibraryNode

    Do iTreeResultClassList.$search($ref.Library=iTreeResultLibraryList.Library,kTrue,kFalse,kTrue,kTrue)
    Set current list iTreeResultClassList
    For each line in list (Selected lines only) from 1 to #LN step 1
        ...
    End For
    Set current list iTreeResultLibraryList     ## restore before the outer loop continues
End For
```

The join is `$search` on the child list by the parent key, then `For each line in list (Selected lines only)`. That is the Omnis equivalent of a nested loop join, and it is why the lists must be **pre-sorted by the same key order** — see §37.

`Set current list` is a global. Restore it explicitly after every inner loop, or wrap it:

```
Begin reversible block
    Set current list iTreeResultLibraryList
End reversible block
```

## 36. A node carries its row — `$add(text, ident, row)`

```
Do parentNode.$add(con(kTreeSpace,text),TreeIdent,DataRow) Returns Node
Calculate Node.$tag as con('L:',lib,'_C:',cls,'_M:',meth)   ## stable search key
Calculate Node.$iconid as kMethodIcon
```

Three things get attached to every node, and each answers a different question later:

| | what it is for |
|---|---|
| `$rowdata` | the data row passed to `$add`, read back with `Calculate row as Node.$rowdata` |
| `$tag` | a **composite string key** identifying the node independently of position |
| `$ident` | the numeric identity, incremented as the tree is built |

`$rowdata` is the actual parallelism: the tree does not point *into* the list, it carries a copy of the row. Change the list and the tree does not follow — rebuild it.

Note `con(kTreeSpace, text)` on every display string, and `$setcolumnalign(n,kRightJst)` for numeric columns.

## 37. Sorting by an expression built at runtime

```
Calculate SortEval as con(nam(iTreeResultClassList),'.$sort($ref.Library,0,',pSortFields,')')
Do eval(SortEval)
```

`nam(var)` yields the variable's own name, so the list can be sorted by a criterion passed in as a string (`'$ref.PercentOfTotal,1'`). The parent key columns come **first** in the sort, so the `$search`-and-iterate join of §35 walks each parent's children contiguously.

This is `eval()` of a constructed string, with everything that implies. It is here because the sort criterion is a user choice; do not reach for it when the criterion is known at write time.

## 38. Finding the matching node in a second tree

Two independent strategies, used for two different situations.

**By tag**, when the trees were built from the same key scheme:

```
If SearchNode.$tag=Tag
    # WORKAROUND: First node doesn't locate properly
    Set reference ToNode to SearchNode
Else
    Do pToTree.$findnodetag(SearchNode,Tag,kTrue) Returns ToNode
End If
```

The comment records a measured Omnis defect: **`$findnodetag` does not locate the node it is given as the starting point.** The guard tests the start node's tag by hand before searching. Anyone writing `$findnodetag` without that check loses exactly one node, silently — the hardest kind of bug to find.

**By name path**, when only display names are shared:

```
Do prTo.$findnodename(0,parentNodeName,kTrue,kTrue) Returns ref
Do prTo.$findnodename(ref,nodeName,kTrue,kTrue) Returns ref
```

`0` as the start means "from the root". Search for the parent first, then for the child **within** that result — a two-step walk, not one search on a joined string.

## 39. Reentrancy guard that cannot be forgotten

Synchronising tree A to tree B fires tree B's events, which would synchronise back. The guard is a flag set inside a reversible block:

```
If not(iSynchronizeTreeIsRunning)
    Begin reversible block
        Calculate iSynchronizeTreeIsRunning as kTrue   ## prevent reinvoking this method
    End reversible block
    ...
End If
```

The reversible block resets the flag on method exit — **on every path**, including early `Quit method` and error exits. A hand-written `Calculate flag as kFalse` at the bottom is one `Quit method` away from a permanently stuck flag. This is the best use of `Begin reversible block` in the whole set.

## 40. Tree navigation vocabulary

```
Do treeRef.$currentnode() Returns Node       ## the selected node
Do treeRef.$setcurrentnode(nodeRef)          ## select one
Do Node.$nodeparent() Returns Parent         ## up one level
Set reference firstChild to Node.$first()    ## down one level; empty = leaf
Do treeRef.$nextnode(firstChild,kFalse) …    ## next sibling; kFalse = do not descend
Calculate lvl as Node.$level                 ## 1-based depth
If Node.$isexpanded                          ## current display state
Do ref.$expand()  /  Do ref.$collapse()
Do treeRef.$clearallnodes()
```

Two derived tests worth naming, both used repeatedly here:

```
If Node.$first()                             ## has children -> not a leaf
If treeRef.$nextnode(firstChild,kFalse)      ## has MORE THAN ONE child
```

And the descent to the single leaf beneath a node:

```
While firstChild
    Set reference Node to firstChild
    Set reference firstChild to firstChild.$first()
End While
```

## 41. Which tree event you are in

```
Switch pEventCode
    Case evTreeCollapse,evTreeExpand
        Calculate nodeName as pNodeItem().$name
        Calculate parentNodeName as pNodeItem.$nodeparent().$name
    Case evClick
        Calculate nodeName as prFrom.$currentnode().$name
        Calculate parentNodeName as prFrom.$currentnode().$nodeparent().$name
End Switch
```

The node comes from a **different place** depending on the event: `pNodeItem` on expand/collapse, `$currentnode()` on click. Reading `$currentnode()` in an expand handler gives the previously selected node, not the one being expanded.

---

# Interposition and SQL diagnostics — from the SQLMonitor

266 methods, 1805 code lines. Small, and it contains two techniques that appear nowhere else in the set: a **transparent object wrapper**, and **bulk injection into another library's classes**. Both are how a monitoring tool attaches to an application it does not own.

## 42. `Do redirect` — the transparent wrapper

```
Do redirect iRealDAMStatementObjRef Returns status
```

The command forwards the *current* call — same method name, same parameters — to another object, and hands back its return value. The wrapper class implements the same method names as the real object; each one does its own work and then redirects:

```
Calculate iCT as #CT
Do redirect iRealDAMStatementObjRef Returns status
Calculate iCT as abs(#CT-iCT)                       ## elapsed ticks around the real call
```

The help documents it under commands → calculations: it redirects execution from a custom property to any other public method, `$crecipient` is the recipient, and the flag is set if the recipient exists and handles the property. That is the whole decorator pattern in one command — no manual parameter forwarding, so the wrapper does not break when the wrapped method's signature changes.

Use it whenever you need to observe or time calls to an object you cannot modify.

## 43. Interposition by superclass replacement

The wrapper still has to get between the application and the real object. The tool does it by **inserting a subclass into the inheritance chain**:

```
Duplicate class SqlLogSessionTemplate/[className]
Do $clib.$classes.[className].$superclass.$assign(iOccurencesList.vorkommen)
```

`Duplicate class <source>/<newname>` clones a template; the clone is then reparented to the *original* superclass the application used. Every reference in the application to the old superclass is rewritten to the new class, so the application inherits its original behaviour **through** the logging layer and nothing in its own logic changes.

Overridden methods get `Do inherited` prepended so the original behaviour still runs:

```
Do ref.$methodtext.$assign(con('Do inherited ',marker,line,kCr,kCr,ref.$methodtext))
```

## 44. Rewriting classes in another library — the four things that bite

```
Calculate allWindows as sys(194)                              ## all windows, IDE included
Calculate instWindows as $iwindows.$makelist($ref.$name,$ref.$title)
If allWindows.$linecount>1|instWindows.$linecount>1
    ...
    Close other windows
End If

Begin reversible block
    Calculate $root.$prefs.$alloweditifnotcheckedout as kTrue
End reversible block

Do ref.$class().$findandreplace(rx,replacement,kTrue,kFalse,kTrue)
```

1. **`$findandreplace` cannot replace in an open window.** Everything must be closed first — `sys(194)` lists all windows including the IDE's, `$iwindows.$makelist` the runtime ones. The tool checks both and asks before closing.
2. **`$root.$prefs.$alloweditifnotcheckedout`** must be true to touch classes that are not checked out. In a reversible block, so it is restored.
3. **`#NULL` as the replacement means FIND ONLY.** The help is explicit: `$findandreplace(cFind,cReplace[,bIgnCase=kTrue,bWholeWord=kFalse,bRegExp=kFalse,bClearLog=kFalse])` — *if `cReplace` is `#NULL`, finds all instances of `cFind`; otherwise replaces them.* It returns a row of status information. So in the injection code the edit is already done by `$methodtext.$assign()`; the following `$findandreplace(marker,#NULL)` is a **search** whose purpose is to list the touched places in the Find log. Note `bClearLog` — the log accumulates across calls unless you ask for it to be cleared.
4. **The Find dialog hangs** (recorded as ST/FR/175 in the code). The tool opens it deliberately at the end and warns the user to close it before doing anything else:
   ```
   Standard menu command 14000 {Find And Replace}
   ```
   `Standard menu command <n>` invokes an IDE menu command by number.

`$findandreplace` accepts regular expressions with **named groups**:

```
Calculate rx as '^\.(?<DAM>.*DAM)\.(?<SESS>[^.]*SESS)$'
```

And the whole sweep runs as one `$sendall` per case, filtered by a type column, with `&` or `+` chaining two operations per item:

```
Do list.$sendall(list.ref().$methodtext.$assign(…)&list.ref().$class().$findandreplace(…),list.typ=5)
```

## 45. SQL diagnostics on the statement object

```
If iStmtRef.$state=kStatementStateClear
    Quit method kFalse
End If
Calculate sql as iStmtRef.$sqltext()
...
If iStmtRef.$errorcode<>kDAMNoError
    Calculate errorcode as con(iStmtRef.$errorcode,' / ',iStmtRef.$nativeerrorcode)
    Calculate errortext as con(iStmtRef.$errortext,' / ',iStmtRef.$nativeerrortext)
End If
... iStmtRef.$rowsaffected , iStmtRef.$rowsfetched
```

Two error layers, always paired: `$errorcode`/`$errortext` is Omnis's view, `$nativeerrorcode`/`$nativeerrortext` the database's. Log both — they disagree often enough that either alone is misleading.

`$state` guards against using a cleared statement. `$rowsaffected` and `$rowsfetched` are the outcome counters, and both belong in any SQL log.

Detecting a dropped connection rather than a query error:

```
If sessRef.$isConnectionBroken(stmtRef.$ref)|err=kSessionStateLoggedOff|err=kSessionNotLoggedOn|err=kSessionLogonFailed
    Do sessRef.$reLogon
End If
```

## 46. Wrapping a statement: what works, and what Omnis says does not

This is the hardest-won material in the set, because the answer is largely negative and it took a support case to settle.

### The two properties

A list or row defined from an SQL class carries:

| | |
|---|---|
| `$statementobject` | the statement **object** in use by the schema or table instance |
| `$statementobjref` | the statement **object reference** in use by it |

Both are in the help under `notation/misc/list_defined_from_sql_class`. What is not documented is that **`$statementobjref` is assignable**:

```
Quit method pfTableInstance.$statementobjref.$assign(iRealDAMStatementObjRef)
```

Note *what* is assigned: the **real** DAM statement, not the wrapper. That direction is the whole point — see below.

**Assigning `$statementobjref` implicitly asks the session for another statement via `$newstatement`.** The assignment is not a pointer swap; it has a side effect on the session. Recorded verbatim as a warning in the source, and nothing in the help hints at it.

Use the **ref** property, not the object property. The wrapped statement is created with `$newstatementref`, which the help describes as creating a statement instance *to be used with an Object reference variable*, as opposed to `$newstatement` for an object variable. Going through `$statementobject` gives you a copy — the same copy-versus-reference trap as `Set reference X to inst.cVar` in `OMNIS_LORE.md` 7.5, one layer down. The library guards the wrong branch with a `Breakpoint` carrying that explanation rather than a comment.

### A list cannot use a wrapped statement

If the session object is subclassed so that `$newstatement` returns a wrapper, a list's `$select()` picks it up **implicitly**. The chain, from the demo's own comments:

```
Do iCustomerList.$sessionobject.$assign(iSessObj)   ## iSessObj subclasses the DAM session
Do iCustomerList.$select(' where CustomerID>@[#1]')
    ## implicitly: session.$newstatement  -> returns the wrapper
    ##             wrapper assigned to iCustomerList.$statementobject
    ##             wrapper.$prepare()   <- breaks here
    ##             wrapper.$execute()
```

And it breaks. The symptom is that `$prepare` is called **twice** by one `$select`, the second time with a null SQL parameter. Omnis Support closed the case, and the verdict is quoted in the source:

> ST/TA/025 — `$prepare` is called twice when doing a `$select`. 4 Apr 24: Unresolved. Unsupported functionality. It is not possible to superclass a dynamically generated object instance, like a statement object. The reported problem occurs because the core tries to query a non-existent `$state` property before execution, to determine whether the statement has already been prepared. Overriding `$newstatement()` and returning a custom object instance is likely to result in undefined behaviour.

The library ships a workaround — swallow the second `$prepare` and return 1 — and marks it as such. **Do not build on this.** "Undefined behaviour" from the vendor is not a caveat to work around; it is a wall.

### What to do instead

| you control | approach |
|---|---|
| explicit statement calls (`myStatement.$prepare`, `$execute`) | the `Do redirect` wrapper of §42 works properly here |
| a list or row driven by `$select` / `$fetch` | **use a table class** with the methods you want to intercept and `$sqlclassname` set to the schema class name |
| neither | interpose at the *session* level only, and log what the session sees |

The table-class route is the one the same library recommends in its own comment, and it is what `SqlLogTableSuperclass` implements: override `$select`, `$fetch`, `$insert`, `$update`, `$delete`, `$doinsert`, `$dodelete`, `$sqlerror`, read `$cinst.$statementobject.$errorcode` and friends inside, and call `Do inherited`. No dynamically generated instance is subclassed, so nothing is undefined.

The demo library carries all three variants side by side — `wSmartListLowLevel`, `wSmartListTableClass`, `wSmartListWrapper` — which is the cheapest way to see the difference.

### Distinguishing an implicit call from an explicit one

The wrapper needs to know whether it was called by the user or by the core during a `$select`, because the two need different handling. The library's own `$isImplicitCall()` does that, and the branch structure is worth copying even if the wrapper itself is a dead end:

```
If $cinst.$isImplicitCall()
    ## called by the core as part of myList.$select
Else
    ## direct call: myStatement.$prepare
    Get statement iFullSqlScript
End If
Do redirect iRealDAMStatementObjRef Returns result
```

`Get statement <var>` retrieves the SQL text of the current statement — useful when `$prepare` was called without the text as a parameter.

Also new here: `$wherenames` and `$fromclause` alongside the `$selectnames` family, `$extraquerytext` for appending to a generated statement, `$doinserts`/`$doupdates`/`$dodeletes` for list-level DML and `$doinsert(pfRow)` / `$doupdate(pfRow,pfRowOLD)` / `$dodelete(pfRow)` for row level — note `$doupdate` takes **both** the new row and the old one, which is how it builds the WHERE clause. (Signatures from studiotips.net; no library in the set calls the singular forms, so they are documented and web-witnessed but not library-witnessed.) Also `$savelistwork` / `$revertlistupdates` for committing or discarding pending list changes, `$usecursor`, `$plsql`, and `$debugfile` on the session for DAM-level tracing.

---

# From StudioTips (Doug Kuyvenhoven, ~2000–2008)

Eight libraries, 4234 methods, 29809 code lines — a tips collection rather than an application, so the code density is low but the *annotation* density is the highest in the set. Doug marks findings with `@BUG` and `@BUGWORKAROUND` tags, which makes the expensive knowledge mechanically findable.

79 notation tokens new to the merged reference; **740 documented tokens across nine libraries** in total.

## 47. Item references do not survive being stored

Two separate defects, both recorded by Doug with a workaround, and both affecting code we have already written down.

```
# @BUG: Item references stored in a list variable can be lost when the list changes lines.
# @BUGWORKAROUND: Rather than use a list variable to store the observers, we are using columns in a row variable.

# @BUG: Item references stored in a node's $rowdata row are lost.   ## 2005-03-31
# @BUGWORKAROUND: Store the fullname rather than a reference.
```

The workaround he settled on is the same in both cases: **store `$fullname` and re-resolve with `[fullname].$ref` when needed**, rather than storing the reference itself.

```
Do iEmptyNodeRowData.$cols.$add('methodfullname',kCharacter,kSimplechar,1000000)
Do iEmptyNodeRowData.$cols.$add('classfullname',kCharacter,kSimplechar,1000000)
```

Note the column length: 1000000, not 255. A `$fullname` is long.

**This contradicts two patterns already in this file.** §36 stores a data row in a tree node's `$rowdata`; §3–4 build lists with `kItemref` columns (`$cols.$add('objRef',kItemref)`). Both are in working code, so the defect is evidently not universal — but it is not obviously version-specific either, and Doug hit it hard enough to restructure around it. Before relying on a stored item reference, **either** re-resolve from a stored fullname, **or** verify by probe that references survive the specific operation you are doing (a list changing lines, a node being rebuilt). `OMNIS_LORE.md` 2.3 has the measured part: whether a held reference survives the removal of its class depends on how it was made. A list changing lines and a node being rebuilt are not measured.

## 48. `$toplevelhwnd`, and the three vertical reference points

A third hwnd nobody else in the set uses:

```
$cwind.$top                        top of the window
$cwind.$toplevelhwnd.$ref().$top   bottom of the TITLE BAR
$cwind.$framehwnd.$ref().$top      bottom of the MENU BAR -- present whether or not it is visible
$modes.$top / $modes.$height       screen area available for positioning a window
```

Three rules that go with them, all of which cost Doug time:

1. **`$hwnd` and `$framehwnd` work on window OBJECTS**, not only on window instances — complex grids, tab panes and so on. The help documents them under the window instance only.
2. **Use `$cwind`, not `$cinst`,** for `$toplevelhwnd` and `$framehwnd`: with `$cinst` the code breaks when the window is opened as a subwindow.
3. **The `()` is required**: `$cwind.$framehwnd.$ref().$top`. It forces evaluation of the chain up to that point before the property is read.

`$framehwnd` reporting the bottom of the menu bar even when the bar is hidden is logged as a bug and was never resolved.

## 49. Container insets are conditional, not constant

Doug's `oScreenCoordinates` computes a field's position by walking containers and adding a per-type offset — but the offset is a **function**, not a number: platform (`sys(6)`), `$taborient`, `$tabstyle`, `$multirow` combined with `$width<45*$tabcount`, and the container's border style all change it. The insets measured since are in `OMNIS_LORE.md` 10.2; there `$tabstyle` made no difference and `$taborient` did.

The one line that rules out a constants table outright, from his web notes: changing a complex grid's border to an embossed border shifts the offset.

## 50. `@BUG` as a searchable convention

Worth stealing outright. Every defect Doug hit is tagged in the comment where he worked around it:

```
# @BUG: <what fails>            ## <date> <who>
# @BUGWORKAROUND: <what to do instead>
```

That makes a codebase's accumulated pain `grep`-able, which is exactly what the distillation of every other library in this set had to reconstruct by reading. Adding these two tags costs nothing and turns a comment into an index entry.

## 51. Setting all tab captions or tooltips in one assignment

`$alltabcaptions` and `$alltabtooltips` are carriage-return separated strings covering every tab of a tab pane, and they are **assignable** at runtime — no loop over tabs, no `$currenttab` juggling:

```
Do tabRef.$alltabcaptions.$assign(con('Overview',kCr,'Detail',kCr,'History'))
Do tabRef.$alltabtooltips.$assign(con('All rows',kCr,'One row',kCr,'Changes'))
```

Read them back the same way and `split(…,kCr)` to get a list. Paged panes carry `$alltabcaptions` (their "tabs" are pages) but not `$alltabtooltips`.

Both appear in the help under the class tree (`notation/root/libs/lib/windows/window/objs/tab_pane`) *and* the instance tree (`notation/root/iwindows/window/objs/tab_pane`), which is what tells you they work at runtime and not only in design mode.

Recorded here because StudioTips states the opposite — read-only, class-only, "useless to the developer". It is wrong, and following it costs the simplest way there is to caption a tab pane from data.

---

# Measuring the window chrome instead of hardcoding it

From Doug Kuyvenhoven's `ScreenCoordinates` library (2008-03-14), supplied as a JSON export. It answers the question of the container insets (`OMNIS_LORE.md` 10.2), and the answer is a technique rather than a table of numbers.

## 52. Measure a bar by toggling it and reading the client-size delta

Open a scratch window off screen, turn every bar off, then switch each one on in turn and record how much the client area shrank. That number *is* the bar's size, on this platform, this theme, this Omnis version, this DPI — no constant to go stale.

```
Do rClass.$openonce() Returns rWin            ## its $construct puts it off screen
Do rWin.$hasmenus.$assign(kFalse)
Do rWin.$toolbarpos.$assign(kDockingAreaNone)
Do rWin.$hasstatusbar.$assign(kFalse)
Do rWin.$horzscroll.$assign(kFalse)
Do rWin.$vertscroll.$assign(kFalse)
Set reference rHwnd to rWin.$hwnd.$ref

Calculate StartSize as rHwnd.$clientheight
Do rWin.$hasmenus.$assign(kTrue)
Calculate menubarheight as StartSize-rHwnd.$clientheight

Calculate StartSize as rHwnd.$clientwidth
Do rWin.$vertscroll.$assign(kTrue)
Calculate scrollbarwidth as StartSize-rHwnd.$clientwidth
...
Do rWin.$close()
```

Toolbars are measured once per option combination, because the height changes with them:

```
Do rWin.$toolbaroptions.$assign(kTBOptionLargeIcons+kTBOptionShowText)
Do rWin.$toolbaroptions.$assign(kTBOptionLargeIcons)
Do rWin.$toolbaroptions.$assign(kTBOptionNone)
Do rWin.$toolbaroptions.$assign(kTBOptionShowText)
```

The results go into one row, computed once at startup and read from then on.

**What cannot be measured this way, he hardcodes and says so.** The title bar cannot be switched off, so:

```
Calculate Height as 22
Switch sys(6)
    Case 'M','X'
        Calculate Height as 22
End Switch
```

A platform switch whose branches are identical — an honest placeholder marking where a number had to be typed. Worth copying as a habit: measure what can be measured, hardcode the rest *visibly*.

## 53. Walking a field up to its window

```
Calculate TopOffset as 0
Calculate LeftOffset as 0
While prField<>prWin&prField
    Calculate TopOffset as TopOffset+prField.$top
    Calculate LeftOffset as LeftOffset+prField.$left
    If prField.$container().$objtype=kComplexGrid
        Do method getFieldPosns_kComplexGrid (prField,TopOffset,LeftOffset)
    Else If prField.$objtype=kTabPane
        Do method getFieldPosns_kTabPane (prField,TopOffset,LeftOffset)
    Else If prField.$objtype=kGroupBox
        Do method getFieldPosns_kGroupBox (prField,TopOffset,LeftOffset)
    Else
        If prField.$container().$vertscroll=kTrue
            Calculate TopOffset as TopOffset-(prField.$container().$vscroll*8)
        End If
        If prField.$container().$horzscroll=kTrue
            Calculate LeftOffset as LeftOffset-(prField.$container().$hscroll*8)
        End If
    End If
    Set reference prField to prField.$container
End While
```

Four things this makes explicit that a per-type constants table cannot:

1. **The loop guard is `prField<>prWin&prField`** — stop at the window, and stop if the reference goes unset. Note that here `$container` *is* used as the walk step, unlike §9's warning: this walks to the window deliberately, so container-skipping is the wanted behaviour.
2. **A complex grid is detected on the CONTAINER**, the other two on the field itself. A field inside a complex grid needs the grid's correction; a tab pane corrects for its own tabs.
3. **Scrolled containers subtract the scroll offset**, `$vscroll*8` and `$hscroll*8` — the scroll position is in units of 8 pixels. Neither the Executor nor the application library of §29–34 accounts for this, and it is the difference between right and wrong the moment a scrollbox is scrolled.
4. The per-type methods take `TopOffset`/`LeftOffset` **by reference** and add to them, rather than returning a constant.

For the tab-pane and group-box numbers themselves, see `OMNIS_LORE.md` 10.2.

---

# Language change: the comment character

**`;` was Omnis's comment character and was changed to `#`.** Full-line comments are `#`, inline comments `##`; the old forms were `;` and `;;`.

This is not trivia — it is a silent breakage waiting in old code. Every tool in this set that parses method text at runtime was written against one convention or the other, and none of them checks:

| library | marker used | era |
|---|---|---|
| StudioTips | `;;` ×8 | ~2000–2008 |
| application library (§29–34) | `;;` ×23, `##` ×2 | ~20 years, mixed |
| Executor | `##` ×6 | current |

**Old text-parsing code silently finds nothing on current Omnis.** It does not error — `pos(';;',line)` simply returns 0 for every line, so comments are never stripped and every commented-out line is treated as code. The application library containing both forms is the visible scar of the transition.

Before reusing any method-text parser from an old library, check which character it looks for. The Executor's `$stripComments` uses `#`/`##` and is correct for current Omnis.

---

Copyright (c) 2026 Udo Sonnabend (USO-FT). This text is licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/): you may share and adapt it, also commercially, if you name the author, link the source and the license, and say what you changed. Code examples in this text may also be used under the MIT License, without attribution in your code. Source: https://github.com/uso-ft/omnis-executor
