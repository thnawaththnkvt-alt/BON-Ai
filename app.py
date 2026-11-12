import os, time, requests
from flask import (Flask, request, jsonify,
                   render_template_string, send_file)

app = Flask(__name__)
KEY = os.environ["GROQ_KEY"]
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
SYSTEM = "คุณชื่อ BON จริงจัง ตอบตรงๆ ภาษาไทย ฉลาด สรุปเป็นข้อ สั้นแต่ได้ใจความ"
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
#bar{padding:8px 12px calc(12px + env(safe-area-inset-bottom))}
#f{display:flex;align-items:center;gap:8px;background:#fff;border-radius:28px;padding:8px 8px 8px 18px;box-shadow:0 2px 12px rgba(0,0,0,.12)}
#t{flex:1;border:0;outline:0;font-size:16px;background:transparent;padding:8px 0;min-width:0}
#s{width:44px;height:44px;border-radius:50%;border:0;background:#1f1e1d;color:#fff;font-size:20px}
</style></head><body>
<div id="log"><div id="hello"><img src="/logo.png" alt="">
<h2 id="gh">วันนี้อยากคุยเรื่องอะไรดี</h2></div></div>
<div id="bar"><form id="f">
<input id="t" placeholder="คุยกับ BON..." autocomplete="off">
<button id="s">↑</button></form></div>
<script>
const log=document.getElementById("log"),t=document.getElementById("t");
let hist=[];
const G=["วันนี้อยากคุยเรื่องอะไรดี","มีอะไรให้ BON ช่วยไหม","ว่างๆ มาคุยกันหน่อย","ถามมาได้เลย","มีอะไรน่าสนใจบ้าง"];
document.getElementById("gh").textContent=G[Math.floor(Math.random()*G.length)];
function typeOut(el,s){return new Promise(res=>{
const a=Array.from(s);let i=0;el.textContent="";
const step=Math.max(1,Math.ceil(a.length/150));
const id=setInterval(()=>{i+=step;
el.textContent=a.slice(0,i).join("");
log.scrollTop=log.scrollHeight;
if(i>=a.length){clearInterval(id);res()}},20)})}
function add(c,x){const d=document.createElement("div");
d.className="m "+c;d.textContent=x;log.appendChild(d);
log.scrollTop=log.scrollHeight;return d}
document.getElementById("f").onsubmit=async e=>{
e.preventDefault();const x=t.value.trim();if(!x)return;t.value="";
const h=document.getElementById("hello");if(h)h.remove();
add("u",x);hist.push({role:"user",content:x});
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
    msgs = [{"role": m["role"], "content": str(m["content"])[:1000]}
            for m in msgs if m.get("role") in ("user", "assistant")]
    try:
        r = requests.post(
            URL,
            headers={"Authorization": "Bearer " + KEY},
            json={"model": MODEL,
                  "messages": [{"role": "system", "content": SYSTEM}] + msgs},
            timeout=55,
        ).json()
        return jsonify(answer=r["choices"][0]["message"]["content"])
    except Exception:
        return jsonify(answer="ขออภัย ระบบขัดข้อง ลองใหม่อีกครั้ง"), 500
