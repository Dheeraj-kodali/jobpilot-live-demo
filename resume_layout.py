"""Source-preserving resume structure and readable PDF layout."""
import io
import re
from xml.sax.saxutils import escape

SECTIONS = {
    'profile':'Profile', 'summary':'Profile', 'professional summary':'Profile',
    'education':'Education','certificates':'Certifications','certifications':'Certifications',
    'skills':'Technical Skills','technical skills':'Technical Skills',
    'projects':'Projects','professional experience':'Experience','experience':'Experience',
    'additional information':'Additional Information','additinal information':'Additional Information',
}

def structure(text):
    lines=[re.sub(r'\s+',' ',line).strip() for line in text.splitlines() if line.strip()]
    # A PDF footer often repeats the same contact; keep the first occurrence.
    emails=set(); cleaned=[]
    for line in lines:
        if re.fullmatch(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',line):
            if line in emails: continue
            emails.add(line)
        cleaned.append(line)
    sections=[]; header=[]; current=None
    for line in cleaned:
        heading=SECTIONS.get(line.strip('# :').lower())
        if heading:
            current={'title':heading,'lines':[]}; sections.append(current)
        elif current is None: header.append(line)
        else: current['lines'].append(line)
    return header,sections

def render_pdf(text):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    header,sections=structure(text)
    ink=colors.HexColor('#202D39'); muted=colors.HexColor('#53616B'); accent=colors.HexColor('#285568')
    styles={
        'name':ParagraphStyle('name',fontName='Helvetica-Bold',fontSize=21,leading=24,textColor=ink,spaceAfter=4),
        'subtitle':ParagraphStyle('subtitle',fontName='Helvetica',fontSize=10,leading=13,textColor=muted,spaceAfter=5),
        'contact':ParagraphStyle('contact',fontName='Helvetica',fontSize=8.6,leading=12,textColor=muted,spaceAfter=3),
        'section':ParagraphStyle('section',fontName='Helvetica-Bold',fontSize=10,leading=12,textColor=accent,spaceBefore=9,spaceAfter=3,keepWithNext=True),
        'body':ParagraphStyle('body',fontName='Helvetica',fontSize=9.2,leading=12,textColor=ink,spaceAfter=3),
        'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=9.5,leading=12,textColor=ink,spaceBefore=4,spaceAfter=2,keepWithNext=True),
        'caption':ParagraphStyle('caption',fontName='Helvetica-Oblique',fontSize=8.7,leading=11,textColor=muted,spaceAfter=3,keepWithNext=True),
        'bullet':ParagraphStyle('bullet',fontName='Helvetica',fontSize=9.1,leading=11.7,textColor=ink,leftIndent=10,firstLineIndent=0,bulletIndent=0,spaceAfter=2),
    }
    story=[]
    def p(value,kind='body',bullet=False):
        value=value.replace('\ufffd','-')
        value=re.sub('[\u2010-\u2015\u2212]','-',value).replace('\u202f',' ').replace('\u00a0',' ')
        story.append(Paragraph(escape(value),styles[kind],bulletText='-' if bullet else None))
    if header:
        first=header[0]
        # Preserve the source subtitle while distinguishing it visually from a name.
        match=re.match(r'^([A-Z][A-Z .-]+?)\s+([A-Z][a-z].*)$',first)
        if match: p(match[1].strip(),'name');p(match[2],'subtitle')
        else: p(first,'name')
        contacts=[]
        for line in header[1:]:
            if '@' in line or re.search(r'\d{7,}|linkedin\.|github\.|https?://',line): contacts.append(line)
            else: p(line,'subtitle')
        if contacts: p('  |  '.join(contacts),'contact')
    for section in sections:
        title=section['title']; lines=section['lines']
        p(title.upper(),'section')
        rule=HRFlowable(width='100%',thickness=.5,color=colors.HexColor('#CAD6DC'),spaceAfter=5)
        rule.keepWithNext=True
        story.append(rule)
        if title=='Profile':
            p(' '.join(lines));continue
        if title=='Technical Skills' and len(lines)%2==0 and all(len(x)<60 for x in lines[::2]):
            for label,value in zip(lines[::2],lines[1::2]):
                story.append(Paragraph('<b>'+escape(label)+':</b> '+escape(value),styles['body']))
            continue
        if title=='Certifications':
            p(' · '.join(lines));continue
        grouped=[]
        for line in lines:
            is_bullet=bool(re.match(r'^[•\ufffd\x7f\u25a0*]\s|^-\s',line))
            clean=re.sub(r'^[•\ufffd\x7f\u25a0*\-]\s+','',line) if is_bullet else line
            if not is_bullet and grouped and grouped[-1][0]=='bullet' and not re.search(r'[.!?:]$',grouped[-1][1]):
                grouped[-1]=('bullet',grouped[-1][1]+' '+clean)
            else: grouped.append(('bullet' if is_bullet else 'plain',clean))
        previous=''
        for index,(kind,line) in enumerate(grouped):
            if kind=='bullet':p(line,'bullet',True)
            elif title in ('Projects','Experience'):
                is_title=index==0 or previous=='bullet'
                p(line,'title' if is_title else 'caption')
            elif title=='Education':p(line,'title' if index==0 else 'body')
            else:p(line)
            previous=kind
    if not sections:
        # Unknown layouts retain their source text rather than guessing section boundaries.
        if not header:p(text)
    buffer=io.BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=39,rightMargin=39,topMargin=32,bottomMargin=32,
                          title='Resume',author='',allowSplitting=1)
    doc.build(story)
    return buffer.getvalue()
