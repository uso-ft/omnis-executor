#!/usr/bin/env python3
"""
Danger blade -- the console's danger scan (CONTRACT.md §2), run on a script
BEFORE delivery.

Usage:  python3 check_danger.py <script.txt> [more.txt ...]
        python3 check_danger.py --selftest

WHY THIS EXISTS
---------------
The console scans every script on the run path
(`ExecutorConsole.$dangerFindings`, called by `$checkForDangerousCode`). A class the
script picks at run time cannot be backed up, so such a line raises a Yes/No before
close and backup (stage A); a softer case writes a protocol line (stage B). This
blade tells the author the same thing before the user sees the dialog.

Console and blade must say the same: the functions below are a LINE-BY-LINE
MIRROR of the Omnis methods (1-based mid/pos, the same regular expressions),
and they matched the Omnis methods live on the three control texts of
--selftest. Change a rule in one place and the other is wrong.

WHAT IT REPORTS
---------------
A finding is a NOTE ('..'), never a failure: a generic selection can be the point
of a script, and the dialog is the user's to answer. The exit code is 0 for
scripts. Leading tabs and spaces are removed first, as $assignScriptToExecutor
does, so the line numbers are the lines of $execute.

--selftest runs the three control texts and FAILS (exit 1) when a line or a stage
differs from what the Omnis methods produced. Run it after any change here.
"""
import sys
import re
def rxpos(rx,s,ign):
    m=re.search(rx,s,re.I if ign else 0)
    return (m.start()+1,len(m.group()),m.groupdict()) if m else (0,0,{})
def mid(s,p,n=None):
    if p<1: return ''
    return s[p-1:] if n is None else s[p-1:p-1+max(n,0)]
def pos(a,b): return b.find(a)+1
def rpos(a,b): return b.rfind(a)+1
def inside(t,o):
    d=0
    for c in range(o,len(t)+1):
        ch=mid(t,c,1)
        if ch in '([': d+=1
        elif ch in ')]':
            d-=1
            if d==0: return mid(t,o+1,c-o-1)
    return mid(t,o+1)
def arg(a,n):
    d=0;k=1;st=1
    for c in range(1,len(a)+1):
        ch=mid(a,c,1)
        if ch in '([': d+=1
        elif ch in ')]': d-=1
        elif ch==',' and d==0:
            if k==n: return mid(a,st,c-st).strip()
            k+=1;st=c+1
    return mid(a,st).strip() if k==n else ''
def roots(e,names):
    out='';off=1;h,ml,_=rxpos(r'[#\w]+',e,0)
    while h>0:
        h=off+h-1;tok=mid(e,h,ml).lower();prev=mid(e,h-1,1);off=h+ml
        if h==1 or (prev!='.' and prev!='$'):
            if pos(tok[:1],'0123456789')==0:
                if len(names)==0 or pos(','+tok+',',names)>0: out+=tok+','
        h,ml,_=rxpos(r'[#\w]+',mid(e,off),0)
    return out
def islit(e,const):
    rest=e.lower().replace('$clib().$name','~l~').replace('$clib.$name','~l~')
    if '[' in rest: return False
    off=1;h,ml,_=rxpos(r'[#\w$.]+',rest,0)
    while h>0:
        h=off+h-1;tok=mid(rest,h,ml);off=h+ml
        if tok!='con' and tok!='l' and pos(','+tok+',',const)==0: return False
        h,ml,_=rxpos(r'[#\w$.]+',mid(rest,off),0)
    return True
def chain(t,p):
    res='';middle=',';nota=False;c=p
    while mid(t,c,1)=='.':
        if mid(t,c+1,1)=='[':
            seg='[]';c=c+3+len(inside(t,c+1))
        else:
            h,ml,_=rxpos(r'^[#\w$]+',mid(t,c+1),0)
            if h==0: return res
            seg=mid(t,c+1,ml).lower();c=c+1+ml
            if mid(t,c,1)=='(': c=c+2+len(inside(t,c))
        if seg in ('$remove','$add','$assign'):
            if nota:
                if seg=='$remove' or ',$classdata,' in middle or ',$methodtext,' in middle or ',$name,' in middle: return 'A'
                res='B'
        elif seg[:1]=='$' and seg not in ('$line','$cols','$linecount'): nota=True
        middle+=seg+','
    return res
def mark(st,ru,ps,pr):
    if len(ps)==0 or st=='A': return st,ru
    if ps=='A' or st=='': return ps,pr
    return st,ru
G=r'\$(?P<G>classes|codes|fieldstyles|files|menus|objects|prefs|queries|remoteforms|remotemenus|remoteobjects|remotetasks|reports|schemas|searches|tables|tasks|toolbars|windows|libs)\.'
MRX=G+r'\$(?P<M>remove|sendall|makelist|appendlist|insertlist|first|next|findname|findident)(?P<E>[^#\w$]|$)'
def findings(text):
    out=[];taint=',';const=','
    for no,orig in enumerate(text.split('\r'),1):
        s=orig
        if s[:1]=='#': s=''
        for q in ("'[^']*'",'"[^"]*"'):
            h,ml,_=rxpos(q,s,0)
            while h>0:
                s=mid(s,1,h-1)+'~L~'+mid(s,h+ml); h,ml,_=rxpos(q,s,0)
        if pos('##',s): s=mid(s,1,pos('##',s)-1)
        X=r'\$extobjects\.(?:\[[^\]]*\]|[#\w]+)\.\$objects'
        h,ml,_=rxpos(X,s,1)
        while h>0:
            s=mid(s,1,h-1)+mid(s,h,ml).lower().replace('$objects','$xobjects',1)+mid(s,h+ml); h,ml,_=rxpos(X,s,1)
        low=s.lower();st='';ru='';src=False
        if len(s.strip())>0:
            if low[:12]=='delete class':
                if pos('[',s)>0:
                    if islit(mid(s,pos('[',s)+1,rpos(']',s)-pos('[',s)-1),const): st,ru=mark(st,ru,'B','Delete class of a named class')
                    else: st,ru=mark(st,ru,'A','Delete class with a calculated name')
                else: st,ru=mark(st,ru,'B','Delete class of a named class')
            if pos('eval(',low)>0 and len(roots(s,taint))>0: st,ru=mark(st,ru,'A','eval with a generic variable')
            off=1;h,ml,cap=rxpos(MRX,s,1)
            while h>0:
                h=off+h-1;g=cap['G'].lower();m=cap['M'].lower();c=h+ml-len(cap['E'] or '');off=c;a=''
                if mid(s,c,1)=='(': a=inside(s,c)
                if m=='remove':
                    if g!='libs':
                        a1=arg(a,1);a2=arg(a,2)
                        if len(roots(a1,taint))>0 or rxpos(r'(?:^|[^.\w$])\$(?:sendall)?ref(?:[^\w]|$)',a1,1)[0]>0: st,ru=mark(st,ru,'A','group.$remove of a generic class')
                        elif len(a2)>0 and a2.lower()!='kfalse': st,ru=mark(st,ru,'A','recursive group.$remove')
                        else: st,ru=mark(st,ru,'B','group.$remove of a named class')
                elif m in ('findname','findident'):
                    if not islit(a,const): src=True
                else:
                    src=True
                    if m in ('appendlist','insertlist'): taint+=roots(arg(a,1),'')
                    if m=='sendall':
                        a=arg(a,1);o2=1;h2,l2,_=rxpos(r'(?:^|[^.\w$])\$(?:sendall)?ref(?:\(\))?',a,1)
                        while h2>0:
                            h2=o2+h2-1;o2=h2+l2;st,ru=mark(st,ru,chain(a,o2),'$sendall writing through $ref')
                            h2,l2,_=rxpos(r'(?:^|[^.\w$])\$(?:sendall)?ref(?:\(\))?',mid(a,o2),1)
                h,ml,cap=rxpos(MRX,mid(s,off),1)
            off=1;h,ml,cap=rxpos(G+r'\[(?P<IN>[^\]]*)\]',s,1)
            while h>0:
                h=off+h-1;off=h+ml
                if not islit(cap['IN'].replace('//',''),const): src=True
                h,ml,cap=rxpos(G+r'\[(?P<IN>[^\]]*)\]',mid(s,off),1)
            off=1;h,ml,cap=rxpos(r'\[(?P<IN>[^\]]*)\]\.',s,0)
            while h>0:
                h=off+h-1;off=h+ml
                if len(roots(cap['IN'],taint))>0: st,ru=mark(st,ru,chain(s,off-1),'notation [calc] with a generic variable')
                h,ml,cap=rxpos(r'\[(?P<IN>[^\]]*)\]\.',mid(s,off),0)
            off=1;h,ml,_=rxpos(r'[#\w]+',s,0)
            while h>0:
                h=off+h-1;tok=mid(s,h,ml).lower();prev=mid(s,h-1,1);off=h+ml
                if pos(','+tok+',',taint)>0 and (h==1 or (prev!='.' and prev!='$')): st,ru=mark(st,ru,chain(s,off),'write through generic '+tok)
                h,ml,_=rxpos(r'[#\w]+',mid(s,off),0)
            if st: out.append((no,st,ru,orig.strip()[:110]))
            tg='';h,ml,cap=rxpos(r'Returns\s+(?P<T>[#\w]+)\s*$',s,1)
            if h>0: tg=cap['T'].lower();ex=mid(s,1,h-1)
            else:
                h,ml,cap=rxpos(r'^(?:Set reference|Calculate)\s+(?P<T>[#\w]+)\s+(?:to|as)\s',s,1)
                if h>0: tg=cap['T'].lower();ex=mid(s,h+ml)
            if tg:
                ig=src or len(roots(ex,taint))>0; il=islit(ex,const)
                taint=taint.replace(','+tg+',',',');const=const.replace(','+tg+',',',')
                if ig: taint+=tg+','
                if il: const+=tg+','
    return out


POSITIVE = 'Set reference libRef to Executor.$ref\nDo libRef.$classes.$makelist($ref) Returns list\nDo list.$sendall(libRef.$classes.$remove(list.c1))\nSet reference ref to libRef.$classes.$first\nWhile ref.$class()<>\'\'\nDo libRef.$classes.$remove(ref)\nSet reference ref to libRef.$classes.$next(ref)\nEnd While\nDo $root.$libs.$makelist($ref) Returns list2\nDo list2.$sendall(list2.c1.$classes.$remove(list2.c1.$classes.$first()))\nDo libRef.$classes.$appendlist(list3,$ref)\nDo libRef.$classes.$remove(list3.c1)\nDo libRef.$classes.$findident(count) Returns ref2\nDo ref2.$methods.$remove(ref2.$methods.$first())\nDo libRef.$classes.$remove(Executor.$classes.MyFolder,kTrue)\nSet reference ref4 to libRef.$classes.$first()\nDo [ref4.$fullname].$methods.$add(\'x\')\nCalculate text as eval(con(ref4.$fullname,\'.$methodtext.$assign(""x"")\'))\nCalculate name as list.c1\nDelete class [name]\nDo $clib.$classes.$sendall($ref.$desc.$assign(\'x\'))'
NEGATIVE = "Set reference libRef to Executor.$ref\nDo libRef.$classes.$remove($root.$libs.Executor.$classes.Executor)\nDo libRef.$classes.$remove($libs.Executor.$classes.Executor)\nDo libRef.$classes.$remove(Executor.$classes.Executor)\nDo libRef.$classes.$remove(Executor.$classes.$findname('Executor'))\nCalculate name as 'Tool'\nDo $clib.$classes.$remove($clib.$classes.$findname(name))\nDo $clib.$classes.$remove(Executor.$classes.MyFolder,kFalse)\nDelete class [name]\nDo $clib.$classes.$makelist($ref.$name) Returns list\nDo list.$line.$assign(3)\nDo list.$cols.$add('x')\nDo list.$add('y')\nCalculate text as con(text,list.c1)\nDo list.$search($ref.c1='x') Returns count\nSave class [list.c1]\nSet reference ref to Executor.$classes.$findname('Tool')\nDo ref.$methods.$add('x')\nSet reference ref to $clib.$classes.$first()\nSet reference ref to Executor.$classes.Tool\nDo ref.$methods.$remove(ref.$methods.$first())"
EXTRA = "Do $root.$extobjects.$makelist($ref) Returns list\nDo list.$add('x')\nCalculate text as 'Do $clib.$classes.$remove(ref) ## inside a literal'\nSet reference ref to $clib.$classes.$first()\nDo ref.$showascheckedout.$assign(kTrue)\nDo ref.$name.$assign('x')\nSet reference ref to Executor.$classes.Tool\nDo ref.$name.$assign('y')\nDo list.$sendall($clib.$classes.$remove($ref))"
EXPECTED = [
    ('positive', POSITIVE, '3A 6A 10A 12A 14A 15A 17B 18A 20A 21B'),
    ('negative', NEGATIVE, '2B 3B 4B 5B 7B 8B 9B'),
    ('extra', EXTRA, '5B 6A 9A'),
]


def as_method_text(text):
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return '\r'.join(l.strip('\t ') for l in lines)


def selftest():
    bad = 0
    for label, text, want in EXPECTED:
        got = ' '.join(f'{n}{s}' for n, s, _, _ in findings(as_method_text(text)))
        if got == want:
            print(f"ok   selftest {label}: {got}")
        else:
            bad += 1
            print(f"FAIL selftest {label}")
            print(f"     -> expected {want}")
            print(f"     -> got      {got}")
    print(f"\n{len(EXPECTED) - bad}/{len(EXPECTED)} controls as measured in Omnis")
    return 1 if bad else 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args == ['--selftest']:
        return selftest()
    for name in args:
        try:
            text = open(name, encoding='utf-8', errors='replace').read()
        except OSError:
            print(f"skip (not a file): {name}")
            continue
        found = findings(as_method_text(text))
        if not found:
            print(f"ok   {name}")
            continue
        a = sum(1 for f in found if f[1] == 'A')
        print(f"..   {name}: {a} stage A (dialog), {len(found) - a} stage B (protocol)")
        for n, s, rule, line in found:
            print(f"     .. line {n} stage {s}: {rule} | {line}")
    print(f"\n{len(args)} file(s) scanned (danger scan) -- findings are notes")
    return 0


if __name__ == '__main__':
    sys.exit(main())
