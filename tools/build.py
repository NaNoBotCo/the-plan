"""Build the deck as one static page.

  python3 tools/build.py                                   → docs/ (GitHub Pages)
  SITE_URL=https://motdang.net/the-plan OUT=../mot-dang/assets/the-plan python3 tools/build.py

Slides come from deck/ (the Slides artifact's own files); tools/slides.py regenerates them.
"""
import html, json, os, re, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = os.environ.get("SITE_URL", "https://nanobotco.github.io/the-plan").rstrip("/")
OUT = Path(os.environ.get("OUT", ROOT / "docs")).resolve()
CANON = "https://motdang.net/the-plan/"
REPO = "https://github.com/NaNoBotCo/the-plan"
BLOBS = {"/_blob/c63a392724600d2d8b06de9f4a9d894a": "img/plan-en.png",
         "/_blob/5cc1868ba26dba65807fddc933aeb5ef": "img/plan-th.png"}
FONTS = ("https://fonts.googleapis.com/css2?family=Mitr:wght@400;500;600"
         "&family=IBM+Plex+Sans+Thai:wght@400;600&family=Caveat:wght@500&display=swap")
TITLE = "Mot Dang — the plan · แผนมดแดง"
DESC = ("A business plan in twelve dimensions, for an audience of robots. "
        "Mot Dang, a Thai-first directory of Chiang Mai and Chiang Rai: 62 days, one human, 88,888 places.")

GUIDE = [
    ("1", "Cover", "a name and one strange line", "หน้าปก", "ชื่อ กับประโยคแปลก ๆ หนึ่งประโยค"),
    ("2", "The problem", "one day that happened, in three beats", "ปัญหา", "วันหนึ่งที่เกิดขึ้นจริง เล่าเป็นสามจังหวะ"),
    ("3", "The diagnosis", "two numbers that disagree", "อาการ", "ตัวเลขสองตัว ที่ขัดกัน"),
    ("4", "The plan", "the joke that is also the strategy", "แผน", "มุกตลก ที่เป็นกลยุทธ์ด้วย"),
    ("5", "The feature", "your worst number, told as the point", "จุดขาย", "ตัวเลขที่แย่ที่สุด เล่าให้เป็นประเด็น"),
    ("6", "Leaderboard", "who uses it, ranked", "ตารางคะแนน", "ใครใช้บ้าง เรียงอันดับ"),
    ("7", "Memo", "talk to the audience you have", "บันทึก", "พูดกับผู้ฟัง ที่คุณมีอยู่"),
    ("8", "Dimensions", "every arm on one page", "มิติ", "ทุกแขนขา ในหน้าเดียว"),
    ("9–15", "The arms", "one card each: what it does, a number, a link", "แขนขา", "การ์ดละหนึ่งแขน ทำอะไร ตัวเลข ลิงก์"),
    ("16", "Traction", "time, people, output", "ตัวเลข", "เวลา คน ผลงาน"),
    ("17", "The goal", "a big number, with its arithmetic", "เป้าหมาย", "ตัวเลขใหญ่ พร้อมเลขคณิต"),
    ("18", "Money", "each rail with its status; blanks said plainly", "รายได้", "ช่องทาง พร้อมสถานะ"),
    ("19", "Why you", "one quote", "ทำไมต้องคุณ", "คำพูดเดียว"),
    ("20", "Known bugs", "risks as a triage table", "บั๊ก", "ความเสี่ยง เป็นตารางคัดแยก"),
    ("21", "The ask", "a question, not a figure", "ข้อเสนอ", "เป็นคำถาม ไม่ใช่ตัวเลข"),
    ("22", "The end", "the line people repeat", "ปิดท้าย", "ประโยคที่คนจะพูดต่อ"),
    ("23", "Sources", "where each number came from", "ที่มา", "ตัวเลขแต่ละตัว มาจากไหน"),
]

CSS = """
:root{--ink:#221B16;--cream:#F7F0E3;--mus:#E8B03A;--soft:#D9CBB5}
*{box-sizing:border-box}
html{background:var(--ink)}
body{margin:0;background:var(--ink);color:var(--cream);font-family:'IBM Plex Sans Thai',Tahoma,sans-serif}
a{color:var(--mus)}
.top{position:sticky;top:0;z-index:5;display:flex;gap:12px;align-items:center;justify-content:space-between;padding:10px 16px;background:rgba(34,27,22,.94)}
.top a{color:var(--cream);text-decoration:none;font-family:Mitr,Tahoma,sans-serif;font-size:18px}
.top button{font:600 15px 'IBM Plex Sans Thai',Tahoma,sans-serif;background:var(--mus);color:var(--ink);border:0;border-radius:999px;padding:8px 16px;cursor:pointer}
main{max-width:1600px;margin:0 auto;padding:8px 16px 16px}
.intro{font-size:17px;line-height:1.55;color:var(--soft);margin:8px 0 24px;max-width:60ch}
figure{margin:0 0 36px;scroll-margin-top:64px}
.frame{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:10px;background:var(--cream)}
.frame>section{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;overflow:hidden;font-size:32px;line-height:1.4}
.frame section *{margin:0}
.frame section h1{font-size:96px;font-weight:600;line-height:1.1}
.frame section h2{font-size:64px;font-weight:600;line-height:1.15}
.frame section h3{font-size:44px;font-weight:600;line-height:1.2}
.frame section ul{padding-left:1.2em}
.frame section table{border-collapse:collapse;width:100%}
.frame section th,.frame section td{border:2px solid rgba(34,27,22,.3);padding:.35em .6em;text-align:left;vertical-align:top}
.frame section th{font-weight:600}
.frame section svg{display:block}
figcaption{font-size:15px;line-height:1.55;color:var(--soft);padding:10px 2px 0;max-width:80ch}
figcaption b{color:var(--mus);font-weight:600}
.use{max-width:1100px;margin:24px auto 0;padding:32px 16px 8px;border-top:2px dashed var(--mus)}
.use h2{font:600 34px/1.2 Mitr,Tahoma,sans-serif;margin:0 0 6px}
.use h2 span{color:var(--mus)}
.use p{font-size:17px;line-height:1.6;color:var(--soft);margin:0 0 14px;max-width:70ch}
.use .btns{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 28px}
.use .btns a{font:600 16px 'IBM Plex Sans Thai',Tahoma,sans-serif;text-decoration:none;background:var(--mus);color:var(--ink);padding:10px 18px;border-radius:999px}
.use .btns a.alt{background:transparent;color:var(--cream);border:2px solid var(--mus)}
.use table{width:100%;border-collapse:collapse;font-size:16px;line-height:1.45}
.use th,.use td{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid rgba(217,203,181,.25)}
.use th{color:var(--mus);font-weight:600}
.use td:first-child{color:var(--mus);white-space:nowrap}
.use td small{display:block;color:var(--soft);font-size:15px}
@media (max-width:640px){.use table{font-size:15px}.use th:nth-child(3),.use td:nth-child(3){display:none}}
footer{max-width:1600px;margin:0 auto;padding:8px 16px 48px;font-size:15px;color:var(--soft)}
body.present .top,body.present figcaption,body.present .intro,body.present footer{display:none}
body.present main{max-width:none;padding:0}
body.present figure{height:100vh;margin:0;display:flex;align-items:center;justify-content:center;scroll-snap-align:start}
html.present{scroll-snap-type:y mandatory}
body.present .frame{width:min(100vw,177.78vh);border-radius:0}
"""

JS = """
(function(){
var frames=[].slice.call(document.querySelectorAll('.frame'));
function fit(){frames.forEach(function(f){f.firstElementChild.style.transform='scale('+(f.clientWidth/1920)+')';});}
fit();window.addEventListener('resize',fit);
if(window.ResizeObserver){var ro=new ResizeObserver(fit);frames.forEach(function(f){ro.observe(f);});}
var figs=[].slice.call(document.querySelectorAll('figure'));
function cur(){var best=0,d=1e9;figs.forEach(function(f,i){var t=Math.abs(f.getBoundingClientRect().top);if(t<d){d=t;best=i;}});return best;}
function go(i){i=Math.max(0,Math.min(figs.length-1,i));figs[i].scrollIntoView({behavior:'smooth',block:document.body.classList.contains('present')?'center':'start'});}
document.addEventListener('keydown',function(e){
 if(e.target.closest&&e.target.closest('input,textarea'))return;
 if(['ArrowRight','ArrowDown','PageDown',' '].indexOf(e.key)>=0){e.preventDefault();go(cur()+1);}
 else if(['ArrowLeft','ArrowUp','PageUp'].indexOf(e.key)>=0){e.preventDefault();go(cur()-1);}
 else if(e.key==='Escape'&&document.body.classList.contains('present'))toggle(false);
});
var btn=document.getElementById('present');
function toggle(on){var i=cur();document.body.classList.toggle('present',on);document.documentElement.classList.toggle('present',on);
 if(on&&document.documentElement.requestFullscreen)document.documentElement.requestFullscreen().catch(function(){});
 if(!on&&document.fullscreenElement)document.exitFullscreen();
 setTimeout(function(){fit();go(i);},60);}
btn.addEventListener('click',function(){toggle(!document.body.classList.contains('present'));});
document.addEventListener('fullscreenchange',function(){if(!document.fullscreenElement&&document.body.classList.contains('present'))toggle(false);});
})();
"""

def slides():
    deck = json.loads((ROOT / "deck" / "deck.json").read_text())
    out = []
    for sid in deck["order"]:
        s = (ROOT / "deck" / "slides" / f"{sid}.html").read_text()
        m = re.search(r"<aside>(.*?)</aside>", s, re.S)
        note = m.group(1).strip() if m else ""
        s = re.sub(r"<aside>.*?</aside>", "", s, flags=re.S)
        for k, v in BLOBS.items():
            s = s.replace(k, v)
        out.append((sid, s.strip(), note))
    return out

def use_section():
    rows = "".join(f"<tr><td>{n}</td><td>{en}<small>{th}</small></td><td>{job}<small>{thjob}</small></td></tr>"
                   for n, en, job, th, thjob in GUIDE)
    return f"""<section class="use" id="use">
<h2>Use this plan <span>· เอาแผนนี้ไปใช้</span></h2>
<p>Copy it, change it, pitch with it. The deck is CC BY 4.0: keep the credit line <b>NaN · motdang.net · CC BY 4.0</b> and a link back. The code that builds it is MIT. The still on slide 4 belongs to <i>Nathan for You</i>; put your own picture there.</p>
<p>เอาไปใช้ได้ แก้ได้ ใช้เสนองานได้ ขอแค่ใส่เครดิต NaN · motdang.net · CC BY 4.0 และลิงก์กลับมา ภาพในหน้า ๔ เป็นของรายการ Nathan for You ให้ใส่ภาพของคุณเอง</p>
<div class="btns"><a href="the-plan.pdf" download>PDF · ดาวน์โหลด</a><a class="alt" href="{REPO}/generate">Use as a template · ใช้เป็นแม่แบบ</a><a class="alt" href="{REPO}">Source · โค้ด</a></div>
<table><tr><th>Slide</th><th>Name · ชื่อ</th><th>Its job · หน้าที่</th></tr>{rows}</table>
</section>"""

def jsonld():
    return json.dumps({"@context": "https://schema.org", "@type": "PresentationDigitalDocument",
                       "name": "The Plan: a business plan in twelve dimensions, for an audience of robots",
                       "alternateName": "แผนมดแดง", "url": CANON, "inLanguage": ["en", "th"],
                       "author": {"@type": "Person", "name": "NaN", "url": "https://motdang.net/"},
                       "license": "https://creativecommons.org/licenses/by/4.0/",
                       "isAccessibleForFree": True, "datePublished": "2026-09-27",
                       "keywords": "business plan, pitch deck, business plan example, pitch deck template, Chiang Mai",
                       "encoding": {"@type": "MediaObject", "contentUrl": SITE + "/the-plan.pdf", "encodingFormat": "application/pdf"},
                       "codeRepository": REPO}, ensure_ascii=False)

def page(items):
    n = len(items)
    figs = []
    for i, (sid, sec, note) in enumerate(items, 1):
        cap = f'<b>{i} / {n}</b> · notes for robots · โน้ตสำหรับบอท'
        if note:
            cap += f' — {html.escape(note, quote=False)}'
        figs.append(f'<figure id="{sid}"><div class="frame">{sec}</div><figcaption>{cap}</figcaption></figure>')
    alt = "" if SITE.startswith("https://motdang.net") else f'<link rel="alternate" href="{SITE}/">'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<meta name="description" content="{html.escape(DESC)}">
<link rel="canonical" href="{CANON}">{alt}
<meta property="og:type" content="website">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{html.escape(DESC)}">
<meta property="og:url" content="{SITE}/">
<meta property="og:image" content="{SITE}/card.png?v=2">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A business plan for an audience of robots. 299 humans, 1,950,000 robots in one week. motdang.net/the-plan">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}</style>
<script type="application/ld+json">{jsonld()}</script>
</head>
<body>
<header class="top"><a href="https://motdang.net/">Mot Dang · มดแดง</a><button id="present" type="button">Present · นำเสนอ</button></header>
<main>
<h1 class="intro" style="font:inherit;margin:8px 0 24px">The plan, in {n} slides. Arrow keys move; Present fills the screen. The notes under each slide are for the robots, who are most of our readers. · แผนธุรกิจ {n} หน้า โน้ตใต้ภาพเขียนไว้ให้บอทอ่าน</h1>
{chr(10).join(figs)}
</main>
{use_section()}
<footer>NaN · <a href="https://motdang.net/">motdang.net</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> · <a href="{REPO}">source</a> · nan@motdang.net</footer>
<script>{JS}</script>
</body>
</html>
"""

def card(items, dest):
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    src = ROOT / "tools" / "card.html"
    subprocess.run([chrome, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1200,630", "--virtual-time-budget=6000", f"--screenshot={dest}", src.as_uri()],
                   check=True, capture_output=True)

def pdf(items, dest):
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    pages = "".join(f'<div class="frame">{sec}</div>' for _, sec, _ in items)
    doc = (f'<!doctype html><meta charset="utf-8"><title>{TITLE}</title><link rel="stylesheet" href="{FONTS}"><style>{CSS}'
           '@page{size:1920px 1080px;margin:0}html,body{background:#F7F0E3}'
           '.frame{width:1920px;height:1080px;aspect-ratio:auto;border-radius:0;page-break-after:always;break-after:page}'
           '.frame>section{transform:none}</style>' + pages)
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "print.html"
        p.write_text(doc.replace('src="img/', f'src="{(ROOT / "img").as_uri()}/'))
        subprocess.run([chrome, "--headless=new", "--no-pdf-header-footer", "--virtual-time-budget=8000",
                        f"--print-to-pdf={dest}", p.as_uri()], check=True, capture_output=True)

def main():
    items = slides()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    for v in BLOBS.values():
        shutil.copyfile(ROOT / v, OUT / v)
    (OUT / "index.html").write_text(page(items))
    card(items, OUT / "card.png")
    pdf(items, OUT / "the-plan.pdf")
    if not SITE.startswith("https://motdang.net"):
        (OUT / ".nojekyll").write_text("")
    print(f"{len(items)} slides → {OUT}")

if __name__ == "__main__":
    main()
