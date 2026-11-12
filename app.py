import os, time, requests
from flask import Flask, request, jsonify, render_template_string

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
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BON Ai</title>
<style>
body{font-family:sans-serif;margin:0;display:flex;flex-direction:column;height:100dvh}
h1{margin:0;padding:12px;font-size:18px;background:#222;color:#fff}
#log{flex:1;overflow-y:auto;padding:12px}
.m{margin:8px 0;padding:10px;border-radius:12px;max-width:85%;white-space:pre-wrap}
.u{background:#d9ecff;margin-left:auto}
.a{background:#eee}
form{display:flex;gap:8px;padding:8px;border-top:1px solid #ccc}
input{flex:1;padding:10px;font-size:16px}
button{padding:10px 16px;font-size:16px}
</style></head><body>
<h1>BON Ai</h1>
<div id="log"></div>
<form id="f"><input id="t" placeholder="พิมพ์ข้อความ..." autocomplete="off">
<button>ส่ง</button></form>
<script>
const log=document.getElementById("log"),t=document.getElementById("t");
let hist=[];
function add(c,x){const d=document.createElement("div");
d.className="m "+c;d.textContent=x;log.appendChild(d);
log.scrollTop=log.scrollHeight;return d}
document.getElementById("f").onsubmit=async e=>{
e.preventDefault();const x=t.value.trim();if(!x)return;t.value="";
add("u",x);hist.push({role:"user",content:x});
const w=add("a","...");
try{
const r=await fetch("/chat",{method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({messages:hist.slice(-10)})});
const j=await r.json();
w.textContent=j.answer;
if(r.ok)hist.push({role:"assistant",content:j.answer});
}catch(err){w.textContent="เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"}
};
</script></body></html>"""


@app.route("/")
def home():
    return render_template_string(PAGE)


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
