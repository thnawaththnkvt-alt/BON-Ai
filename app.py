import os, io, re, time, json, base64, requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, send_file, Response

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ["GROQ_KEY"]
TAVILY_KEY = os.environ.get("TAVILY_KEY", "")
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.8-27b"
BASE = ("คุณชื่อ BON ตอบเป็นภาษาไทยเสมอ ยกเว้นผู้ใช้ขอภาษาอื่น"
        " ตอบให้ตรงกับคำถามล่าสุดของผู้ใช้ก่อน ห้ามตอบเรื่องที่ไม่ได้ถาม"
        " ถ้าคำถามกำกวมให้ถามกลับสั้นๆ ข้อเดียว"
        " ถ้าไม่รู้ให้บอกว่าไม่รู้ ห้ามเดา")
DEFAULT_PERSONA = "จริงจัง ตอบตรงๆ สรุปเป็นข้อสั้นๆ แต่ได้ใจความ"
LIMIT = 50  # ข้อความต่อคนต่อวัน
WEB_LIMIT = 15  # ครั้งค้นเว็บต่อคนต่อวัน
FILE_CHARS = 5000  # ตัวอักษรจากไฟล์ที่ส่งให้บอท
MAX_MSGS = 30  # จำนวนข้อความย้อนหลังสูงสุดที่รับจากหน้าเว็บ
MEM_CHARS = 6000  # งบตัวอักษรความจำที่ส่งให้โมเดลต่อครั้ง
usage = {}
TH = timezone(timedelta(hours=7))


def now_th():
    return datetime.now(TH).strftime("%d/%m/%Y %H:%M")


def ev(**k):
    return json.dumps(k, ensure_ascii=False) + "\n"


PAGE = r"""<!doctype html>
<html lang="th" translate="no"><head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,interactive-widget=resizes-content">
<title>BON Ai</title>
<link rel="icon" href="/logo.png">
<link rel="apple-touch-icon" href="/logo.png">
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#ffffff">
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;overflow:hidden}
body{position:fixed;top:0;left:0;right:0;height:100dvh;background:#fff;color:#1c1c1e;font-family:sans-serif;display:flex;flex-direction:column}
#hd{display:flex;align-items:center;gap:2px;padding:6px 10px;padding-top:calc(6px + env(safe-area-inset-top));flex:none}
.ib{width:44px;height:44px;border:0;background:transparent;color:#1c1c1e;display:flex;align-items:center;justify-content:center;border-radius:50%;padding:0}
#ttl{flex:1;font-size:16px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;padding:0 6px}
#log{flex:1;overflow-y:auto;padding:8px 18px;display:flex;flex-direction:column;overscroll-behavior:contain}
#hello{margin:auto;text-align:center;padding-bottom:30px}
#hello img{width:72px;height:72px;border-radius:18px}
#hello h2{font-weight:400;font-size:26px;margin:18px 0 0}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.u{align-self:flex-end;background:#edf1fd;padding:12px 18px;border-radius:20px;max-width:85%;margin:14px 0 6px;white-space:pre-wrap;line-height:1.5;word-break:break-word;animation:fade .3s ease}
.pic{display:block;max-width:100%;max-height:220px;border-radius:12px;margin-bottom:6px}
.fn{font-size:13px;opacity:.7;margin-bottom:4px}
.a{align-self:stretch;margin:10px 0;line-height:1.65;animation:fade .3s ease}
.an{white-space:pre-wrap;word-break:break-word}
.thk{display:none;margin-bottom:8px;color:#8a8f98;font-size:15px}
.thk summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:6px}
.thk summary::-webkit-details-marker{display:none}
.thk summary::after{content:"›";font-size:20px;transition:transform .2s}
.thk[open] summary::after{transform:rotate(90deg)}
.tb{white-space:pre-wrap;font-size:13px;color:#777;margin-top:6px;padding-left:10px;border-left:2px solid #e3e6ee;max-height:180px;overflow:auto;line-height:1.5}
.live{display:none;font-size:13px;color:#555;margin-bottom:8px;line-height:1.6}
.live .lq{font-weight:bold;margin-bottom:2px}
.live a{display:block;color:#3f64e0;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;animation:fade .3s ease}
.acts{display:flex;align-items:center;gap:14px;margin-top:10px;color:#8a8f98}
.acts button{border:0;background:transparent;color:inherit;padding:6px;display:flex}
.acts button.on{color:#3f64e0}
.acts .sp{flex:1}
#cmp{padding:6px 14px calc(14px + env(safe-area-inset-bottom));flex:none}
#card{background:#fff;border:1px solid #e6e8ef;border-radius:28px;padding:14px 16px 10px;box-shadow:0 6px 24px rgba(30,40,90,.10)}
#pv{display:none;gap:8px;align-items:center;padding-bottom:8px;font-size:14px}
#pv img{height:56px;border-radius:10px}
#pv button{border:0;background:#1c1c1e;color:#fff;border-radius:50%;width:24px;height:24px}
#t{width:100%;border:0;outline:0;resize:none;font-size:16px;font-family:inherit;line-height:1.5;max-height:140px;background:transparent;padding:4px 0 10px;display:block;color:#1c1c1e}
#row{display:flex;align-items:center;gap:8px}
.grow{flex:1}
.chip{display:flex;align-items:center;gap:6px;border:1px solid #d9e2ff;background:#eef2ff;color:#3f64e0;border-radius:20px;padding:8px 14px;font-size:15px;font-family:inherit}
.chip.on{background:#3f64e0;color:#fff;border-color:#3f64e0}
.rb{width:44px;height:44px;border-radius:50%;border:2px solid #1c1c1e;background:#fff;color:#1c1c1e;display:flex;align-items:center;justify-content:center;padding:0;flex:none}
#go.send{background:#1c1c1e;color:#fff}
#go.rec{background:#e5484d;border-color:#e5484d;color:#fff}
#ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:10}
#ov.open{display:block}
#dr{position:fixed;top:0;bottom:0;left:0;width:84vw;max-width:340px;background:#fff;z-index:11;transform:translateX(-100%);transition:transform .25s ease;overflow-y:auto;padding:14px 14px calc(20px + env(safe-area-inset-bottom));padding-top:calc(14px + env(safe-area-inset-top));box-shadow:2px 0 16px rgba(0,0,0,.2)}
#dr.open{transform:none}
#dr .sec{font-size:13px;color:#777;margin:18px 0 6px}
#dr button,#dr select,#dr textarea{font-size:15px;font-family:inherit}
#nc{width:100%;padding:12px;border:0;border-radius:14px;background:#1c1c1e;color:#fff}
.ci{display:flex;align-items:center;border-radius:12px}
.ci.sel{background:#edf1fd}
.ct{flex:1;text-align:left;border:0;background:transparent;padding:10px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:#1c1c1e}
.cd{border:0;background:transparent;padding:8px}
.mb{display:block;width:100%;text-align:left;border:0;background:transparent;padding:10px;border-radius:12px;color:#1c1c1e}
.mb.sel{background:#edf1fd;font-weight:bold}
#cp{display:none;width:100%;min-height:90px;border:1px solid #ccc;border-radius:12px;padding:10px;margin-top:6px}
#dr label{display:block;margin:8px 0;font-size:14px}
#vs{width:100%;padding:8px;margin:4px 0}
#pt{width:100%}
.sm{padding:9px 12px;border:1px solid #ccc;border-radius:12px;background:#fff;margin-top:6px}
</style></head><body>
<div id="hd">
<button id="menu" class="ib" type="button"></button>
<div id="ttl">BON Ai</div>
<button id="spk" class="ib" type="button"></button>
<button id="newc" class="ib" type="button"></button>
</div>
<div id="log"></div>
<div id="cmp"><div id="card">
<div id="pv"></div>
<textarea id="t" rows="1" placeholder="ส่งข้อความหรือกดไมค์เพื่อพูด"></textarea>
<div id="row">
<button type="button" id="think" class="chip"></button>
<button type="button" id="web" class="chip"></button>
<div class="grow"></div>
<button type="button" id="plus" class="rb"></button>
<button type="button" id="go" class="rb"></button>
</div></div></div>
<input type="file" id="fi" accept="image/*,.pdf,.txt,.md,.csv,.json,.py,.html,.js,.log" hidden>
<div id="ov"></div>
<div id="dr">
<button id="nc" type="button">＋ แชทใหม่</button>
<div class="sec">แชทของฉัน</div><div id="cl"></div>
<div class="sec">โหมดของ BON</div><div id="ml"></div>
<textarea id="cp" maxlength="600" placeholder="เขียนนิสัยของ BON เอง เช่น เป็นพี่ชายใจดี ชอบให้กำลังใจ"></textarea>
<div class="sec">เสียง</div>
<label><input type="checkbox" id="sp"> ให้ BON พูดตอบ</label>
<select id="vs"></select>
<label>ระดับเสียง (ต่ำ = ทุ้ม)<input type="range" id="pt" min="0.5" max="1.5" step="0.1"></label>
<button class="sm" id="tv" type="button">ทดลองเสียง</button>
<div class="sec">อื่นๆ</div>
<button class="sm" id="clr" type="button">ลบแชททั้งหมด</button>
</div>
<script>const $=id=>document.getElementById(id);
const log=$("log"),t=$("t"),pv=$("pv"),fi=$("fi"),go=$("go");
const G=["วันนี้อยากคุยเรื่องอะไรดี","มีอะไรให้ BON ช่วยไหม","ว่างๆ มาคุยกันหน่อย","ถามมาได้เลย","มีอะไรน่าสนใจบ้าง"];
const MODES=[
["serious","🎯 จริงจัง","จริงจัง ตอบตรงๆ สรุปเป็นข้อสั้นๆ แต่ได้ใจความ"],
["friend","😎 เพื่อนสนิท","เป็นเพื่อนสนิทที่คุยสบายๆ พูดจาเป็นกันเอง ขี้เล่นเล็กน้อย ตอบสั้นๆ ใช้ภาษาพูด"],
["teacher","📚 ครูสอน","เป็นครูใจเย็น อธิบายเป็นขั้นตอน ใช้ตัวอย่างง่ายๆ และปิดท้ายด้วยคำถามชวนคิดสั้นๆ"],
["coder","💻 นักเขียนโค้ด","เป็นโปรแกรมเมอร์รุ่นพี่ ช่วยเขียนและแก้โค้ด ให้โค้ดที่รันได้จริง อธิบายสั้นๆ"],
["writer","✍️ นักเขียน","เป็นนักเขียนสร้างสรรค์ ใช้ภาษาสละสลวย มีจินตนาการ เสนอไอเดียหลายแบบ"],
["coach","🌱 โค้ชให้กำลังใจ","เป็นโค้ชใจดี รับฟังก่อน ถามชวนคิด ให้กำลังใจ และแนะนำขั้นตอนเล็กๆ ที่ทำได้จริง"],
["custom","🧩 เขียนนิสัยเอง",""]
];
const LS="bon_v1";
let S=null;
try{S=JSON.parse(localStorage.getItem(LS)||"null")}catch(e){S=null}
if(!S||!Array.isArray(S.chats))S={chats:[],cur:null,mode:"serious",custom:"",speak:false,pitch:0.7,voice:""};
function save(){try{localStorage.setItem(LS,JSON.stringify(S,(k,v)=>(k==="img"||k==="file")?undefined:v))}catch(e){}}
function cur(){return S.chats.find(c=>c.id===S.cur)}
function persona(){
if(S.mode==="custom")return (S.custom||"").trim()||MODES[0][2];
const m=MODES.find(x=>x[0]===S.mode);return m?m[2]:MODES[0][2]}
let pending=null,pfile=null,webOn=false,thinkOn=false,busy=false,listening=false;

function svgi(inner,sz){return '<svg viewBox="0 0 24 24" width="'+(sz||22)+'" height="'+(sz||22)+'" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+inner+'</svg>'}
const P={
menu:'<path d="M3 7h12M3 12h18M3 17h8"/>',
newc:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
plus:'<path d="M12 5v14M5 12h14"/>',
atom:'<ellipse cx="12" cy="12" rx="9" ry="3.6"/><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(120 12 12)"/>',
globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
mic:'<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
up:'<path d="M12 19V5M6 11l6-6 6 6"/>',
spkon:'<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
spkoff:'<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4z"/><path d="M16 9.5l5 5M21 9.5l-5 5"/>',
copy:'<rect x="8" y="8" width="11" height="11" rx="2.5"/><path d="M5 15V7.5A2.5 2.5 0 0 1 7.5 5H15"/>',
thumbup:'<path d="M7 11v8H4v-8h3zM7 11l4-7c1.5 0 2.2 1 2 2.4L12.6 10H18a2 2 0 0 1 2 2.4l-1.2 5.6A2 2 0 0 1 16.8 19H7"/>',
thumbdown:'<path d="M7 13V5H4v8h3zM7 13l4 7c1.5 0 2.2-1 2-2.4L12.6 14H18a2 2 0 0 0 2-2.4L18.8 6A2 2 0 0 0 16.8 5H7"/>',
spk:'<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
share:'<path d="M14 5l6 6-6 6V13c-5 0-8 1.5-10 5 .8-5 4-9 10-9.5V5z"/>',
redo:'<path d="M20 12a8 8 0 1 1-2.6-5.9"/><path d="M20 4v5h-5"/>'
};
$("menu").innerHTML=svgi(P.menu,24);
$("newc").innerHTML=svgi(P.newc,26);
$("plus").innerHTML=svgi(P.plus,22);
$("think").innerHTML=svgi(P.atom,18)+"<span>คิด</span>";
$("web").innerHTML=svgi(P.globe,18)+"<span>ค้นหา</span>";

function fit(){const v=window.visualViewport;
const h=v?v.height:window.innerHeight;
document.body.style.height=h+"px";window.scrollTo(0,0);
log.scrollTop=log.scrollHeight}
if(window.visualViewport){
visualViewport.addEventListener("resize",fit);
visualViewport.addEventListener("scroll",()=>window.scrollTo(0,0))}
window.addEventListener("resize",fit);
t.addEventListener("focus",()=>setTimeout(fit,300));
fit();

function grow(){t.style.height="auto";t.style.height=Math.min(t.scrollHeight,140)+"px"}
function updateGo(){
const has=t.value.trim().length>0||!!pending||!!pfile;
go.className="rb"+(listening?" rec":(has?" send":""));
go.innerHTML=svgi(has&&!listening?P.up:P.mic,22)}
t.addEventListener("input",()=>{grow();updateGo()});
t.addEventListener("keydown",e=>{
if(e.key==="Enter"&&!e.shiftKey&&window.innerWidth>800){e.preventDefault();send()}});

function setTitle(){
const c=cur();
$("ttl").textContent=(c&&c.title&&c.title!=="แชทใหม่")?c.title:"BON Ai"}
function showHello(){
log.innerHTML='<div id="hello"><img src="/logo.png" alt=""><h2 id="gh"></h2></div>';
$("gh").textContent=G[Math.floor(Math.random()*G.length)]}
function addUser(x,img,fn){
const d=document.createElement("div");d.className="u";
if(img){const p=document.createElement("img");p.src=img;p.className="pic";d.appendChild(p)}
if(fn){const q=document.createElement("div");q.className="fn";q.textContent="📄 "+fn;d.appendChild(q)}
const s=document.createElement("span");s.textContent=x;d.appendChild(s);
log.appendChild(d);log.scrollTop=log.scrollHeight}
function newAns(){
const d=document.createElement("div");d.className="a";
const live=document.createElement("div");live.className="live";
const thk=document.createElement("details");thk.className="thk";
const sm=document.createElement("summary");
const sumt=document.createElement("span");sumt.textContent="กำลังคิด...";sm.appendChild(sumt);
const tb=document.createElement("div");tb.className="tb";
thk.appendChild(sm);thk.appendChild(tb);
const an=document.createElement("div");an.className="an";
d.appendChild(live);d.appendChild(thk);d.appendChild(an);
log.appendChild(d);log.scrollTop=log.scrollHeight;
return {d:d,live:live,thk:thk,sumt:sumt,tb:tb,an:an}}
function copyText(s){
if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(s).catch(()=>{})}
else{const x=document.createElement("textarea");x.value=s;document.body.appendChild(x);x.select();try{document.execCommand("copy")}catch(e){}x.remove()}}
function flash(b){b.classList.add("on");setTimeout(()=>b.classList.remove("on"),900)}
function addActs(ui,text,last){
const old=ui.d.querySelector(".acts");if(old)old.remove();
const a=document.createElement("div");a.className="acts";
function btn(name,fn,cls){const b=document.createElement("button");b.type="button";
if(cls)b.className=cls;b.innerHTML=svgi(P[name],20);b.onclick=()=>fn(b);a.appendChild(b);return b}
btn("copy",b=>{copyText(text);flash(b)});
const up=btn("thumbup",()=>{up.classList.toggle("on");dn.classList.remove("on")});
const dn=btn("thumbdown",()=>{dn.classList.toggle("on");up.classList.remove("on")});
btn("spk",()=>speak(text,true));
btn("share",()=>{if(navigator.share){navigator.share({text:text}).catch(()=>{})}else{copyText(text)}});
if(last){const sp=document.createElement("div");sp.className="sp";a.appendChild(sp);btn("redo",regen,"redo")}
ui.d.appendChild(a);log.scrollTop=log.scrollHeight}
function fillAns(ui,m,last){
ui.an.textContent=m.content;
if(m.tt!=null&&m.th){ui.thk.style.display="block";ui.sumt.textContent="คิดเป็นเวลา "+m.tt+" วินาที";ui.tb.textContent=m.th}
if(m.src&&m.src.length){ui.live.style.display="block";
const q=document.createElement("div");q.className="lq";q.textContent="🌐 แหล่งที่มา";ui.live.appendChild(q);
m.src.forEach(s=>{const a=document.createElement("a");a.href=s.url;a.target="_blank";a.rel="noopener";
a.textContent="🔗 "+(s.title||s.url);ui.live.appendChild(a)})}
addActs(ui,m.content,last)}
function renderMsgs(){
const c=cur();
if(!c||!c.msgs.length){showHello();return}
log.innerHTML="";
c.msgs.forEach((m,i)=>{
if(m.role==="user"){addUser(m.content,null,m.had||null)}
else{fillAns(newAns(),m,i===c.msgs.length-1)}});
log.scrollTop=log.scrollHeight}function newChat(){
const c=cur();
if(c&&!c.msgs.length){closeDr();return}
const n={id:Date.now().toString(36),title:"แชทใหม่",msgs:[]};
S.chats.unshift(n);S.cur=n.id;save();renderMsgs();renderList();setTitle();closeDr()}
function renderList(){
const cl=$("cl");cl.innerHTML="";
S.chats.forEach(c=>{
const row=document.createElement("div");row.className="ci"+(c.id===S.cur?" sel":"");
const b=document.createElement("button");b.type="button";b.className="ct";b.textContent=c.title;
b.onclick=()=>{S.cur=c.id;save();renderMsgs();renderList();setTitle();closeDr()};
const d=document.createElement("button");d.type="button";d.className="cd";d.textContent="🗑";
d.onclick=()=>{if(!confirm("ลบแชทนี้?"))return;
S.chats=S.chats.filter(x=>x.id!==c.id);
if(S.cur===c.id)S.cur=S.chats.length?S.chats[0].id:null;
if(!S.cur){newChat()}else{save();renderMsgs();renderList();setTitle()}};
row.appendChild(b);row.appendChild(d);cl.appendChild(row)})}
function renderModes(){
const ml=$("ml");ml.innerHTML="";
MODES.forEach(m=>{const b=document.createElement("button");b.type="button";
b.className="mb"+(S.mode===m[0]?" sel":"");b.textContent=m[1];
b.onclick=()=>{S.mode=m[0];save();renderModes()};ml.appendChild(b)});
$("cp").style.display=S.mode==="custom"?"block":"none"}
const dr=$("dr"),ov=$("ov");
function openDr(){dr.classList.add("open");ov.classList.add("open")}
function closeDr(){dr.classList.remove("open");ov.classList.remove("open")}
$("menu").onclick=openDr;
ov.onclick=closeDr;
$("nc").onclick=newChat;
$("newc").onclick=newChat;
const cp=$("cp");
cp.value=S.custom||"";
cp.oninput=()=>{S.custom=cp.value;save()};
$("clr").onclick=()=>{
if(!confirm("ลบแชททั้งหมดในเครื่องนี้?"))return;
S.chats=[];S.cur=null;save();newChat()};

const TTS=!!window.speechSynthesis;
function cleanTTS(s){return String(s).replace(/[*#`_>]/g,"").replace(/https?:\/\/\S+/g,"")}
function speak(txt,force){
if(!TTS||(!S.speak&&!force))return;
speechSynthesis.cancel();
const u=new SpeechSynthesisUtterance(cleanTTS(txt).slice(0,1500));
u.lang="th-TH";u.pitch=S.pitch;u.rate=1;
const vs=speechSynthesis.getVoices().filter(v=>v.lang&&v.lang.toLowerCase().indexOf("th")===0);
const v=vs.find(x=>x.name===S.voice)||vs[0];if(v)u.voice=v;
speechSynthesis.speak(u)}
const spC=$("sp");
function showSpk(){$("spk").innerHTML=svgi(S.speak?P.spkon:P.spkoff,24);spC.checked=!!S.speak}
function setSpeak(v){S.speak=v;save();showSpk();if(!v&&TTS)speechSynthesis.cancel()}
$("spk").onclick=()=>setSpeak(!S.speak);
spC.onchange=()=>setSpeak(spC.checked);
const vsel=$("vs");
function loadVoices(){
if(!TTS){vsel.style.display="none";return}
const vs=speechSynthesis.getVoices().filter(v=>v.lang&&v.lang.toLowerCase().indexOf("th")===0);
vsel.innerHTML="";
if(!vs.length){const o=document.createElement("option");o.textContent="ไม่พบเสียงไทยในเครื่อง";vsel.appendChild(o);return}
vs.forEach(v=>{const o=document.createElement("option");o.value=v.name;o.textContent=v.name;
if(v.name===S.voice)o.selected=true;vsel.appendChild(o)})}
if(TTS){speechSynthesis.onvoiceschanged=loadVoices}
loadVoices();
vsel.onchange=()=>{S.voice=vsel.value;save()};
const pt=$("pt");
pt.value=S.pitch;
pt.oninput=()=>{S.pitch=parseFloat(pt.value);save()};
$("tv").onclick=()=>speak("สวัสดีครับ ผมชื่อบอน",true);

$("web").onclick=()=>{webOn=!webOn;$("web").classList.toggle("on",webOn)};
$("think").onclick=()=>{thinkOn=!thinkOn;$("think").classList.toggle("on",thinkOn)};

function showPv(){pv.innerHTML="";
if(!pending&&!pfile){pv.style.display="none";updateGo();return}
pv.style.display="flex";
if(pending){const i=document.createElement("img");i.src=pending;pv.appendChild(i)}
if(pfile){const n=document.createElement("span");n.textContent="📄 "+pfile.name;pv.appendChild(n)}
const b=document.createElement("button");b.type="button";b.textContent="✕";
b.onclick=()=>{pending=null;pfile=null;showPv()};
pv.appendChild(b);updateGo()}
$("plus").onclick=()=>fi.click();
fi.onchange=()=>{const f=fi.files[0];if(!f)return;
const nm=f.name.toLowerCase();
if(f.type.startsWith("image/")){
const rd=new FileReader();
rd.onload=()=>{const im=new Image();
im.onload=()=>{const m=1024,s=Math.min(1,m/Math.max(im.width,im.height));
const c=document.createElement("canvas");
c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);
c.getContext("2d").drawImage(im,0,0,c.width,c.height);
pfile=null;pending=c.toDataURL("image/jpeg",0.82);showPv()};
im.src=rd.result};
rd.readAsDataURL(f)}
else if(nm.endsWith(".pdf")){
if(f.size>3000000){alert("ไฟล์ใหญ่เกิน 3 MB");fi.value="";return}
const rd=new FileReader();
rd.onload=async()=>{
pv.style.display="flex";pv.textContent="กำลังอ่านไฟล์...";
try{
const r=await fetch("/extract",{method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({data:rd.result})});
const j=await r.json();
if(!r.ok){alert(j.error);pfile=null;showPv();return}
pending=null;pfile={name:f.name,text:j.text};showPv();
}catch(e){alert("อ่านไฟล์ไม่สำเร็จ");showPv()}};
rd.readAsDataURL(f)}
else{
const rd=new FileReader();
rd.onload=()=>{pending=null;
pfile={name:f.name,text:String(rd.result).slice(0,8000)};showPv()};
rd.readAsText(f)}
fi.value=""};

const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
let rec=null;
function toggleDictation(){
if(!SR){alert("เบราว์เซอร์นี้ไม่รองรับการพูด");return}
if(listening){rec.stop();return}
rec=new SR();rec.lang="th-TH";rec.interimResults=true;rec.continuous=false;
const base=t.value?t.value+" ":"";
rec.onstart=()=>{listening=true;updateGo()};
rec.onresult=e=>{let s="";for(const r of e.results)s+=r[0].transcript;t.value=base+s;grow()};
rec.onerror=e=>{if(e.error==="not-allowed")alert("ต้องอนุญาตให้ใช้ไมโครโฟน")};
rec.onend=()=>{listening=false;updateGo();t.focus()};
rec.start()}
go.onclick=()=>{
if(listening){rec.stop();return}
if(t.value.trim()||pending||pfile)send();else toggleDictation()};function send(){
if(busy)return;
let x=t.value.trim();if(!x&&!pending&&!pfile)return;
if(!x)x=pfile?"สรุปไฟล์นี้":"อธิบายรูปนี้";
if(TTS)speechSynthesis.cancel();
if(listening&&rec)rec.stop();
let ch=cur();if(!ch){newChat();ch=cur()}
t.value="";grow();
const h=$("hello");if(h)h.remove();
const img=pending,fl=pfile;pending=null;pfile=null;showPv();
if(img||fl)ch.msgs.forEach(m=>{delete m.img;delete m.file});
addUser(x,img,fl?fl.name:null);
const um={role:"user",content:x};
if(img){um.img=img;um.had="รูปภาพ"}
if(fl){um.file=fl;um.had=fl.name}
ch.msgs.push(um);
if(ch.title==="แชทใหม่"){ch.title=x.slice(0,26);renderList();setTitle()}
save();run()}

function regen(){
if(busy)return;
const ch=cur();if(!ch)return;
while(ch.msgs.length&&ch.msgs[ch.msgs.length-1].role==="assistant")ch.msgs.pop();
if(!ch.msgs.length)return;
save();renderMsgs();run()}

async function run(){
const ch=cur();if(!ch||busy)return;
busy=true;
const w=webOn,th=thinkOn;
const ui=newAns();
let full="",gotAns=false,errd=false,srcs=0,thStart=false,secs=null;
const srcList=[],t0=Date.now();
ui.an.textContent=w?"กำลังค้นหา...":"กำลังคิด...";
const handle=ev=>{
if(ev.t==="status"){if(!gotAns&&!thStart)ui.an.textContent=ev.m}
else if(ev.t==="query"){ui.live.style.display="block";ui.live.innerHTML="";
const q=document.createElement("div");q.className="lq";
q.textContent="🌐 กำลังค้น: "+ev.q;ui.live.appendChild(q)}
else if(ev.t==="source"){ui.live.style.display="block";
const a=document.createElement("a");a.href=ev.url;a.target="_blank";a.rel="noopener";
a.textContent="🔗 "+(ev.title||ev.url);ui.live.appendChild(a);srcs++;
srcList.push({title:ev.title,url:ev.url})}
else if(ev.t==="think"){if(th){
if(!thStart){thStart=true;ui.thk.style.display="block";ui.thk.open=true;ui.an.textContent=""}
ui.tb.textContent+=ev.d;ui.tb.scrollTop=ui.tb.scrollHeight}}
else if(ev.t==="ans"){
if(!gotAns){gotAns=true;ui.an.textContent="";
if(thStart){secs=Math.max(1,Math.round((Date.now()-t0)/1000));
ui.sumt.textContent="คิดเป็นเวลา "+secs+" วินาที";ui.thk.open=false}}
full+=ev.d;ui.an.textContent=full.replace(/\*\*/g,"")}
else if(ev.t==="err"){errd=true;ui.an.textContent=ev.m}
else if(ev.t==="done"){
if(thStart&&secs===null){secs=Math.max(1,Math.round((Date.now()-t0)/1000));ui.sumt.textContent="คิดเป็นเวลา "+secs+" วินาที"}
ui.thk.open=false;
const q=ui.live.querySelector(".lq");if(q&&srcs)q.textContent="🌐 แหล่งที่มา"}
log.scrollTop=log.scrollHeight};
try{
const msgs=ch.msgs.slice(-30).map(m=>{
const o={role:m.role,content:m.content};
if(m.img)o.img=m.img;if(m.file)o.file=m.file;return o});
const r=await fetch("/chat",{method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({messages:msgs,web:w,think:th,persona:persona()})});
if(!r.ok||!r.body){ui.an.textContent="ขออภัย ส่งข้อมูลไม่สำเร็จ ("+r.status+")"}
else{
const rd=r.body.getReader(),dec=new TextDecoder();let buf="";
for(;;){const o=await rd.read();if(o.done)break;
buf+=dec.decode(o.value,{stream:true});
const lines=buf.split("\n");buf=lines.pop();
for(const ln of lines){if(!ln.trim())continue;
let v;try{v=JSON.parse(ln)}catch(err){continue}
handle(v)}}
if(!gotAns&&!errd)ui.an.textContent="ขออภัย ตอบไม่ได้ ลองใหม่อีกครั้ง"}
}catch(err){ui.an.textContent="เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง"}
busy=false;
if(full){const clean=full.replace(/\*\*/g,"");
const m={role:"assistant",content:clean,src:srcList};
if(thStart){m.th=ui.tb.textContent.slice(0,3000);m.tt=secs}
ch.msgs.push(m);save();
log.querySelectorAll(".redo").forEach(b=>b.remove());
addActs(ui,clean,true);speak(clean)}
log.scrollTop=log.scrollHeight}

if(!S.chats.length){S.chats.unshift({id:Date.now().toString(36),title:"แชทใหม่",msgs:[]});S.cur=S.chats[0].id;save()}
if(!cur()){S.cur=S.chats[0].id}
renderMsgs();renderList();renderModes();showSpk();setTitle();updateGo();grow();
</script></body></html>"""@app.route("/")
def home():
    resp = Response(PAGE, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/logo.png")
def logo():
    return send_file(os.path.join(HERE, "logo_bon.png"))


@app.route("/manifest.json")
def manifest():
    return jsonify(
        name="BON Ai",
        short_name="BON",
        start_url="/",
        display="standalone",
        background_color="#ffffff",
        theme_color="#ffffff",
        icons=[{"src": "/logo.png", "sizes": "512x512",
                "type": "image/png"}],
    )


@app.route("/extract", methods=["POST"])
def extract():
    if PdfReader is None:
        return jsonify(error="เซิร์ฟเวอร์ยังไม่ได้ติดตั้ง pypdf"), 500
    try:
        data = request.json.get("data", "")
        raw = base64.b64decode(data.split(",", 1)[1])
        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for p in reader.pages[:20]:
            parts.append(p.extract_text() or "")
            if sum(len(s) for s in parts) > 8000:
                break
        text = "\n".join(parts).strip()[:8000]
        if not text:
            return jsonify(
                error="อ่านข้อความจากไฟล์นี้ไม่ได้ (อาจเป็นไฟล์สแกน)"), 400
        return jsonify(text=text)
    except Exception:
        return jsonify(error="อ่านไฟล์ PDF ไม่สำเร็จ"), 400


def web_search(q):
    r = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": "Bearer " + TAVILY_KEY},
        json={"query": q[:300], "max_results": 4,
              "search_depth": "basic"},
        timeout=25,
    ).json()
    return r.get("results", [])


def open_stream(payload):
    r = requests.post(
        URL,
        headers={"Authorization": "Bearer " + KEY},
        json=payload,
        stream=True,
        timeout=100,
    )
    r.encoding = "utf-8"
    return r


def reply(gen):
    return Response(
        gen,
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def msg_len(m):
    c = m["content"]
    if isinstance(c, str):
        return len(c)
    return sum(len(p.get("text", "")) for p in c if p.get("type") == "text")


def trim(out):
    kept = []
    total = 0
    for m in reversed(out):
        n = msg_len(m)
        if kept and total + n > MEM_CHARS:
            break
        kept.append(m)
        total += n
    kept.reverse()
    while len(kept) > 1 and kept[0]["role"] != "user":
        kept.pop(0)
    return kept


@app.route("/chat", methods=["POST"])
def chat():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ip = ip.split(",")[0].strip()
    day = time.strftime("%Y-%m-%d")
    k = (ip, day)
    usage[k] = usage.get(k, 0) + 1
    if usage[k] > LIMIT:
        return reply(ev(t="ans", d="ครบโควตาวันนี้แล้ว พรุ่งนี้มาใหม่นะ")
                     + ev(t="done", sources=[]))

    body = request.json
    want_web = bool(body.get("web"))
    want_think = bool(body.get("think"))
    persona = str(body.get("persona", "")).strip()[:600] or DEFAULT_PERSONA
    msgs = body.get("messages", [])[-MAX_MSGS:]
    last_img = -1
    last_file = -1
    for i, m in enumerate(msgs):
        img = m.get("img")
        if (isinstance(img, str) and img.startswith("data:image/")
                and len(img) < 3500000):
            last_img = i
        if isinstance(m.get("file"), dict):
            last_file = i

    out = []
    last_user_text = ""
    for i, m in enumerate(msgs):
        if m.get("role") not in ("user", "assistant"):
            continue
        text = str(m.get("content", ""))[:1200]
        if m["role"] == "user":
            last_user_text = text
        if i == last_file and m["role"] == "user":
            fl = m["file"]
            text = ("ไฟล์: " + str(fl.get("name", ""))[:100] + "\n"
                    + str(fl.get("text", ""))[:FILE_CHARS]
                    + "\n\nคำถาม: " + text)
        if i == last_img and m["role"] == "user":
            out.append({"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": m["img"]}},
            ]})
        else:
            out.append({"role": m["role"], "content": text})
    out = trim(out)

    model = VISION_MODEL if last_img >= 0 else MODEL

    def gen():
        system = (BASE + " บุคลิกและสไตล์การตอบ: " + persona
                  + " ตอนนี้คือวันที่และเวลาไทย " + now_th()
                  + " ถ้าผู้ใช้ถามวันหรือเวลา ให้ตอบจากค่านี้เท่านั้น"
                  " ห้ามใช้เครื่องหมาย ** หรือ markdown ใช้ข้อความธรรมดา")
        sources = []

        if want_web:
            if not TAVILY_KEY:
                system += (" ผู้ใช้เปิดโหมดค้นเว็บ แต่ระบบยังไม่ได้ตั้งค่า"
                           " ให้บอกผู้ใช้ตรงๆ ว่าตอนนี้ค้นเว็บยังไม่ได้")
            else:
                wk = (ip, day, "web")
                usage[wk] = usage.get(wk, 0) + 1
                if usage[wk] > WEB_LIMIT:
                    system += (" ค้นเว็บครบโควตาวันนี้แล้ว ให้ตอบจากความรู้เดิม"
                               " และบอกผู้ใช้ว่าวันนี้ค้นเว็บไม่ได้แล้ว")
                else:
                    yield ev(t="status", m="กำลังค้นเว็บ...")
                    yield ev(t="query", q=last_user_text[:80])
                    try:
                        results = web_search(last_user_text)
                    except Exception:
                        results = []
                    if results:
                        lines = []
                        for n, x in enumerate(results, 1):
                            title = str(x.get("title", ""))[:120]
                            link = str(x.get("url", ""))
                            lines.append("[%d] %s\n%s\n%s" % (
                                n, title, link,
                                str(x.get("content", ""))[:400]))
                            sources.append({"title": title, "url": link})
                            yield ev(t="source", title=title, url=link)
                        system += (
                            "\n\nผลค้นเว็บ (บางหน้าอาจเก่า ถ้าวันที่ในผลค้น"
                            "ไม่ตรงกับวันที่ปัจจุบัน ให้เชื่อวันที่ปัจจุบัน):\n"
                            + "\n\n".join(lines)
                            + "\n\nตอบโดยอ้างอิงผลค้นเว็บด้านบน"
                            " ถ้าข้อมูลไม่พอให้บอกตรงๆ อย่าเดาหรือแต่งเพิ่ม")
                    else:
                        system += (" ค้นเว็บไม่สำเร็จหรือไม่พบผล"
                                   " ให้บอกผู้ใช้ตรงๆ แล้วตอบเท่าที่รู้")

        yield ev(t="status", m="กำลังคิด...")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + out,
            "stream": True,
        }
        if model == VISION_MODEL:
            payload["reasoning_format"] = "parsed"
        try:
            r = open_stream(payload)
            if r.status_code != 200 and "reasoning_format" in payload:
                r.close()
                payload.pop("reasoning_format")
                r = open_stream(payload)
            if r.status_code != 200:
                code = r.status_code
                r.close()
                yield ev(t="err",
                         m="ขออภัย ระบบขัดข้อง (%d) ลองใหม่อีกครั้ง" % code)
                return
            in_think = False
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    j = json.loads(d)
                except Exception:
                    continue
                delta = (j.get("choices") or [{}])[0].get("delta") or {}
                rs = delta.get("reasoning")
                if rs and want_think:
                    yield ev(t="think", d=rs)
                c = delta.get("content")
                while c:
                    if in_think:
                        p = c.find("</think>")
                        if p < 0:
                            if want_think:
                                yield ev(t="think", d=c)
                            c = ""
                        else:
                            if p and want_think:
                                yield ev(t="think", d=c[:p])
                            c = c[p + 8:]
                            in_think = False
                    else:
                        p = c.find("<think>")
                        if p < 0:
                            yield ev(t="ans", d=c)
                            c = ""
                        else:
                            if p:
                                yield ev(t="ans", d=c[:p])
                            c = c[p + 7:]
                            in_think = True
            r.close()
        except Exception:
            yield ev(t="err", m="ขออภัย ระบบขัดข้อง ลองใหม่อีกครั้ง")
            return
        yield ev(t="done", sources=sources)

    return reply(gen())
