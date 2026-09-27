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
</head>
<body>
<header class="top"><a href="https://motdang.net/">Mot Dang · มดแดง</a><button id="present" type="button">Present · นำเสนอ</button></header>
<main>
<h1 class="intro" style="font:inherit;margin:8px 0 24px">The plan, in {n} slides. Arrow keys move; Present fills the screen. The notes under each slide are for the robots, who are most of our readers. · แผนธุรกิจ {n} หน้า โน้ตใต้ภาพเขียนไว้ให้บอทอ่าน</h1>
{chr(10).join(figs)}
</main>
<footer><a href="https://motdang.net/">motdang.net</a> · <a href="{REPO}">source</a> · nan@motdang.net</footer>
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

def main():
    items = slides()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    for v in BLOBS.values():
        shutil.copyfile(ROOT / v, OUT / v)
    (OUT / "index.html").write_text(page(items))
    card(items, OUT / "card.png")
    if not SITE.startswith("https://motdang.net"):
        (OUT / ".nojekyll").write_text("")
    print(f"{len(items)} slides → {OUT}")

if __name__ == "__main__":
    main()
