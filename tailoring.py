"""Extractive job tailoring: reorder complete projects, never synthesize claims."""
import re
from resume_layout import SECTIONS
STOP = set("the and for with from this that your our you are will have has into using work role engineer engineering experience required preferred skills development build building".split())
def keywords(text):
    return {x for raw in re.findall(r"[a-z][a-z0-9+#.]*", text.lower()) if (x:=raw.rstrip(".")) and (len(x)>2 or x in {"ai","ml","c#"}) and x not in STOP}
def tailor(source, description):
    lines=source.splitlines(); start=None; end=len(lines)
    for i,line in enumerate(lines):
        section=SECTIONS.get(line.strip().lower())
        if section=='Projects': start=i+1
        elif start is not None and section: end=i;break
    target=keywords(description); source_terms=keywords(source)
    report={'method':'Source-based project ranking (no AI rewriting)',
            'matched_terms':sorted(target & source_terms),
            'not_evidenced_terms':sorted(target-source_terms), 'project_order':[]}
    if start is None: return source,report
    blocks=[]; block=[]; had_bullet=False; complete=False
    for line in lines[start:end]:
        bullet=bool(re.match(r'^\s*[•\ufffd\x7f\u25a0*\-]\s+',line))
        if line.strip() and not bullet and had_bullet and complete:
            blocks.append(block);block=[];had_bullet=False
        block.append(line)
        if line.strip():
            had_bullet=had_bullet or bullet
            complete=bool(re.search(r'[.!?]\s*$',line))
    if block:blocks.append(block)
    # Ambiguous layouts stay unchanged. A block needs a heading and source bullets.
    if not blocks or any(not any(re.match(r'^\s*[•\ufffd\x7f\u25a0*\-]\s+',x) for x in b) for b in blocks):
        return source,report
    ranked=sorted(blocks,key=lambda b:-len(keywords(' '.join(b)) & target))
    report['project_order']=[next(x.strip() for x in b if x.strip()) for b in ranked]
    return '\n'.join(lines[:start]+[x for b in ranked for x in b]+lines[end:]),report
