import os, re, time, requests
from flask import (Flask, request, jsonify,
                   render_template_string, send_file)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
KEY = os.environ["GROQ_KEY"]
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.8-27b"
SYSTEM = "คุณชื่อ BON จริงจัง ตอบตรงๆ ฉลาด สรุปเป็นข้อ สั้นแต่ได้ใจความ ตอบเป็นภาษาไทยเสมอ ยกเว้นผู้ใช้ขอภาษาอื่น"
LIMIT = 50  # ข้อความต่อคนต่อวัน
usage = {}

PAGE = """<!doctype html>
<html lang="th"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>BON Ai</title>
<link rel="icon" href="/logo.png">
<link rel="apple-touch-icon" href="/logo.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#f9f8f6">
<style>
*{box-sizing:border-box}
body{margin:0;background:#f9f8f6;color:#1f1e1d;font-family:sans-serif;display:flex;flex-direction:column;height:100dvh}
#log{flex:1;overflow-y:auto;padding:20px 16px 8px;display:flex;flex-direction:column}
#hello{margin:auto;text-align:center;padding-bottom:60px}
#hello img{width:72px;height:72px;border-radius:18px}
#hello h2{font-weight:400;font-size:26px;margin:18px 0 0}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.m{margin:10px 0;line-height:1.55;white-space:pre-wrap;max-width:88%;animation:fade .35s ease}
.u{align-self:flex-end;background:#efede8;padding:10px 14px;border-radius:18px}
.a{align-self:flex-start}
.pic{display:block;max-width:100%;max-height:220px;border-radius:12px;margin-bottom:6px}
#pv{display:none;gap:8px;align-items:center;padding:0 16px 4px}
#pv img{height:56px;border-radius:10px}
#pv button{border:0;background:#1f1e1d;color:#fff;border-radius:50%;width:24px;height:24px}
#bar{padding:8px 12px calc(12px + env(safe-area-inset-bottom))}
#f{display:flex;align-items:center;gap:8px;background:#fff;border-radius:28px;padding:8px 8px 8px 8px;box-shadow:0 2px 12px rgba(0,0,0,.12)}
#clip{width:40px;height:40px;border-radius:50%;border:0;background:#efede8;color:#1f1e1d;font-size:24px;line-height:1}
#t{flex:1;border:0;outline:0;font-size:16px;background:transparent;padding:8px 0;min-width:0}
#s{width:44px;height:44px;border-radius:50%;border:0;background:#1f1e1d;color:#fff;font-size:20px}
</style></head><body>
<div id="log"><div id="hello"><img src="/logo.png" alt="">
<h2 id="gh">วันนี้อยากคุยเรื่องอะไรดี</h2></div></div>
<div id="pv"></div>
<div id="bar"><form id="f">
<button type="button" id="clip">+</button>
<input type="file" id="fi" accept="image/*" hidden>
<input id="t" placeholder="คุยกับ BON..." autocomplete="off">
<button id="s">↑</button></form></div>
<script>
const log=document.getElementById("log"),t=document.getElementById("t");
const fi=document.getElementById("fi"),pv=document.getElementById("pv");
let hist=[],pending=null;
const G=["วันนี้อยากคุยเรื่องอะไรดี","มีอะไรให้ BON ช่วยไหม","ว่างๆ มาคุยกันหน่อย","ถามมาได้เลย","มีอะไรน่าสนใจบ้าง"];
document.getElementById("gh").textContent=G[Math.floor(Math.random()*G.length)];
function typeOut(el,s){return new Promise(res=>{
const a=Array.from(s);let i=0;el.textContent="";
const step=Math.max(1,Math.ceil(a.length/150));
const id=setInterval(()=>{i+=step;
el.textContent=a.slice(0,i).join("");
log.scrollTop=log.scrollHeight;
if(i>=a.length){clearInterval(id);res()}},20)})}
function add(c,x,img){const d=document.createElement("div");
d.className="m "+c;
if(img){const p=document.createElement("img");p.src=img;p.className="pic";d.appendChild(p);
const s=document.createElement("span");s.textContent=x;d.appendChild(s)}
else{d.textContent=x}
log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
function showPv(){pv.innerHTML="";
if(!pending){pv.style.display="none";return}
pv.style.display="flex";
const i=document.createElement("img");i.src=pending;
const b=document.createElement("button");b.type="button";b.textContent="✕";
b.onclick=()=>{pending=null;showPv()};
pv.appendChild(i);pv.appendChild(b)}
document.getElementById("clip").onclick=()=>fi.click();
fi.onchange=()=>{const f=fi.files[0];if(!f)return;
const rd=new FileReader();
rd.onload=()=>{const im=new Image();
im.onload=()=>{const m=1024,s=Math.min(1,m/Math.max(im.width,im.height));
const c=document.createElement("canvas");
c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);
c.getContext("2d").drawImage(im,0,0,c.width,c.height);
pending=c.toDataURL("image/jpeg",0.82);showPv()};
im.src=rd.result};
rd.readAsDataURL(f);fi.value=""};
document.getElementById("f").onsubmit=async e=>{
e.preventDefault();
let x=t.value.trim();if(!x&&!pending)return;
if(!x)x="อธิบายรูปนี้";
t.value="";
const h=document.getElementById("hello");if(h)h.remove();
const img=pending;pending=null;showPv();
if(img)hist.forEach(m=>{delete m.img});
add("u",x,img);
hist.push(img?{role:"user",content:x,img:img}:{role:"user",content:x});
const w=add("a","...");
try{
const r=await fetch("/chat",{method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({messages:hist.slice(-10)})});
const j=await r.json();
await typeOut(w,j.answer);
if(r.ok)hist.push({role:"assistant",content:j.answer});
}catch(err){w.textContent="เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"}
log.scrollTop=log.scrollHeight;
};
</script></body></html>"""


@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/logo.png")
def logo():
    return send_file("logo_bon.png")


@app.route("/manifest.json")
def manifest():
    return jsonify(
        name="BON Ai",
        short_name="BON",
        start_url="/",
        display="standalone",
        background_color="#f9f8f6",
        theme_color="#f9f8f6",
        icons=[{"src": "/logo.png", "sizes": "512x512",
                "type": "image/png"}],
    )


@app.route("/chat", methods=["POST"])
def chat():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(",")[0].strip()
    day = time.strftime("%Y-%m-%d")
    k = (ip, day)
    usage[k] = usage.get(k, 0) + 1
    if usage[k] > LIMIT:
        return jsonify(answer="ครบโควตาวันนี้แล้ว พรุ่งนี้มาใหม่นะ"), 429

    msgs = request.json.get("messages", [])[-10:]
    last_img = -1
    for i, m in enumerate(msgs):
        img = m.get("img")
        if (isinstance(img, str) and img.startswith("data:image/")
                and len(img) < 3500000):
            last_img = i

    out = []
    for i, m in enumerate(msgs):
        if m.get("role") not in ("user", "assistant"):
            continue
        text = str(m.get("content", ""))[:1000]
        if i == last_img and m["role"] == "user":
            out.append({"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": m["img"]}},
            ]})
        else:
            out.append({"role": m["role"], "content": text})

    model = VISION_MODEL if last_img >= 0 else MODEL
    try:
        r = requests.post(
            URL,
            headers={"Authorization": "Bearer " + KEY},
            json={"model": model,
                  "messages": [{"role": "system", "content": SYSTEM}] + out},
            timeout=100,
        ).json()
        ans = r["choices"][0]["message"]["content"]
        ans = re.sub(r"<think>.*?</think>", "", ans, flags=re.S).strip()
        return jsonify(answer=ans or "ขออภัย ตอบไม่ได้ ลองใหม่อีกครั้ง")
    except Exception:
        return jsonify(answer="ขออภัย ระบบขัดข้อง ลองใหม่อีกครั้ง"), 500
