"""
╔══════════════════════════════════════════════════════════════╗
║         J.A.R.V.I.S.  v4.0 — Stark Industries AI           ║
║    Just A Rather Very Intelligent System — by Sajin          ║
╚══════════════════════════════════════════════════════════════╝

HOW TO RUN:
  1. Install Python from https://python.org  (check Add to PATH)
  2. Double-click  RUN_JARVIS.bat
  That's it. Everything installs automatically.

PASSWORD: vivo
"""

# ─── AUTO INSTALL MISSING PACKAGES ───────────────────────────────────────────
import sys, subprocess, os

REQUIRED = [
    "psutil", "pyttsx3", "SpeechRecognition",
    "pyaudio", "pyautogui", "pyperclip", "Pillow", "requests"
]

def auto_install():
    print("Checking dependencies...")
    for pkg in REQUIRED:
        try:
            __import__(pkg.lower().replace("-","_").split(">=")[0])
        except ImportError:
            print(f"  Installing {pkg}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                capture_output=True
            )
    print("All dependencies ready.\n")

auto_install()

# ─── IMPORTS ──────────────────────────────────────────────────────────────────
import tkinter as tk
from tkinter import font as tkfont
import threading, time, math, json, re, datetime, random
import urllib.request, urllib.error
import webbrowser, platform, queue
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except: HAS_PSUTIL = False

try:
    import pyttsx3
    HAS_TTS = True
except: HAS_TTS = False

try:
    import speech_recognition as sr
    HAS_STT = True
except: HAS_STT = False

try:
    import pyaudio, numpy as np
    HAS_CLAP = True
except: HAS_CLAP = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_GUI = True
except: HAS_GUI = False

try:
    import pyperclip
    HAS_CLIP = True
except: HAS_CLIP = False

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
APP_PASSWORD = "vivo"
USER_NAME    = "Sajin"
DATA_DIR     = Path.home() / ".jarvis"
DATA_DIR.mkdir(exist_ok=True)
IS_WIN       = platform.system() == "Windows"

# Colors
BG    = "#020b14"
BG2   = "#040f1e"
PANEL = "#030d1c"
BLUE  = "#00d4ff"
BLUE_DIM = "#0a2a3a"
ORANGE = "#ff6b00"
GREEN  = "#00ff88"
RED    = "#ff2244"
PURPLE = "#bf5fff"
GOLD   = "#ffd700"
TEXT   = "#a0d8ef"
TEXTD  = "#2a5060"
BORDER = "#0a2030"

# ─── PERSISTENCE ──────────────────────────────────────────────────────────────
def load_json(path, default):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except: pass
    return default

def save_json(path, data):
    try:
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except: pass

# ─── SYSTEM MONITOR ───────────────────────────────────────────────────────────
class SystemMonitor:
    def __init__(self):
        self.s = {
            "cpu":0,"ram":0,"ram_used":0,"ram_total":0,
            "disk":0,"disk_used":0,"disk_total":0,
            "temp":0,"fan":"N/A","battery":"N/A","battery_pct":0,"charging":False,
            "gpu":"N/A","net_down":"—","net_up":"—",
            "cores":1,"os":platform.system()+" "+platform.release(),"uptime":0
        }
        self._prev_net = None
        self._prev_t = time.time()
        self._lock = threading.Lock()
        if HAS_PSUTIL:
            try: self._prev_net = psutil.net_io_counters()
            except: pass
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try: self._update()
            except: pass
            time.sleep(2)

    def _update(self):
        if not HAS_PSUTIL: return
        with self._lock:
            self.s["cpu"] = psutil.cpu_percent()
            self.s["cores"] = psutil.cpu_count()
            m = psutil.virtual_memory()
            self.s["ram"] = m.percent
            self.s["ram_used"] = round(m.used/1e9,1)
            self.s["ram_total"] = round(m.total/1e9,1)
            d = psutil.disk_usage("/")
            self.s["disk"] = d.percent
            self.s["disk_used"] = round(d.used/1e9,1)
            self.s["disk_total"] = round(d.total/1e9,1)
            # Battery
            try:
                b = psutil.sensors_battery()
                if b:
                    self.s["battery_pct"] = round(b.percent)
                    self.s["charging"] = b.power_plugged
                    self.s["battery"] = f"{round(b.percent)}%{'⚡' if b.power_plugged else ''}"
                else:
                    self.s["battery"] = "AC"
            except: pass
            # Temp
            try:
                t = psutil.sensors_temperatures()
                if t:
                    for k in ["coretemp","cpu_thermal","acpitz","k10temp"]:
                        if k in t and t[k]:
                            self.s["temp"] = round(t[k][0].current); break
                    else:
                        vals = [e[0].current for e in t.values() if e]
                        if vals: self.s["temp"] = round(vals[0])
            except: pass
            # Fan
            try:
                f = psutil.sensors_fans()
                if f:
                    for vals in f.values():
                        if vals: self.s["fan"] = f"{vals[0].current} RPM"; break
            except: pass
            # Network
            try:
                now_net = psutil.net_io_counters()
                now_t = time.time()
                if self._prev_net:
                    dt = max(now_t - self._prev_t, 0.1)
                    down = (now_net.bytes_recv - self._prev_net.bytes_recv)/dt
                    up   = (now_net.bytes_sent - self._prev_net.bytes_sent)/dt
                    self.s["net_down"] = self._fmt(down)
                    self.s["net_up"]   = self._fmt(up)
                self._prev_net = now_net; self._prev_t = now_t
            except: pass
            # GPU via nvidia-smi
            try:
                r = subprocess.run(
                    ["nvidia-smi","--query-gpu=utilization.gpu","--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2,
                    creationflags=0x08000000 if IS_WIN else 0
                )
                if r.returncode==0: self.s["gpu"] = r.stdout.strip()+"%"
            except: pass
            # Uptime
            self.s["uptime"] = round((time.time()-psutil.boot_time())/3600,1)

    def _fmt(self, bps):
        if bps<1024: return f"{bps:.0f}B/s"
        if bps<1e6:  return f"{bps/1024:.1f}KB/s"
        return f"{bps/1e6:.1f}MB/s"

    def get(self):
        with self._lock: return dict(self.s)

    def heat(self):
        t=self.s.get("temp",0); c=self.s.get("cpu",0)
        return min(100, (t-30)*2) if t>30 else min(100,c)

# ─── VOICE ENGINE ─────────────────────────────────────────────────────────────
class Voice:
    def __init__(self, on_text=None, on_wake=None, on_clap=None):
        self.on_text  = on_text
        self.on_wake  = on_wake
        self.on_clap  = on_clap
        self.muted    = False
        self.busy     = False
        self.mic_on   = False
        self._q       = queue.Queue()
        self._run     = True
        threading.Thread(target=self._tts_loop, daemon=True).start()
        if HAS_STT:
            self._init_stt()
            threading.Thread(target=self._stt_loop, daemon=True).start()
        if HAS_CLAP:
            threading.Thread(target=self._clap_loop, daemon=True).start()

    def _init_stt(self):
        try:
            self.rec = sr.Recognizer()
            self.rec.energy_threshold = 400
            self.rec.dynamic_energy_threshold = True
            self.rec.pause_threshold = 0.7
            self.mic = sr.Microphone()
            with self.mic as src:
                self.rec.adjust_for_ambient_noise(src, duration=0.5)
        except Exception as e:
            print(f"Mic init: {e}")
            self.rec = None; self.mic = None

    def _tts_loop(self):
        while self._run:
            try:
                text = self._q.get(timeout=0.5)
                if not text or self.muted: continue
                self.busy = True
                self._say(text)
                self.busy = False
            except queue.Empty: pass
            except Exception as e:
                self.busy = False

    def _say(self, text):
        clean = re.sub(r'[\*\#\`]','',text)
        clean = re.sub(r'https?://\S+','',clean).strip()
        if not clean: return
        try:
            eng = pyttsx3.init()
            voices = eng.getProperty('voices')
            best = None; best_score = -1
            for v in voices:
                n = v.name.lower()
                lang = ""
                try: lang = (v.languages[0] if v.languages else b"").decode("utf-8","ignore").lower()
                except: pass
                s=0
                if "david" in n: s+=12
                if "george" in n: s+=15
                if "mark" in n: s+=10
                if "daniel" in n: s+=11
                if "en-gb" in lang or "en_gb" in lang: s+=8
                if "male" in n: s+=3
                if "en" in lang: s+=2
                if s>best_score: best_score=s; best=v
            if best: eng.setProperty('voice', best.id)
            eng.setProperty('rate', 162)
            eng.setProperty('volume', 1.0)
            # Split into natural sentences
            parts = re.findall(r'[^.!?]+[.!?]+', clean) or [clean]
            for p in parts:
                if p.strip(): eng.say(p.strip())
            eng.runAndWait()
            try: eng.stop()
            except: pass
        except Exception as e:
            print(f"TTS: {e}")

    def speak(self, text, priority=False):
        if priority:
            while not self._q.empty():
                try: self._q.get_nowait()
                except: break
        self._q.put(text)

    def stop(self):
        while not self._q.empty():
            try: self._q.get_nowait()
            except: break

    def _stt_loop(self):
        if not hasattr(self,'rec') or not self.rec: return
        while self._run:
            if self.muted: time.sleep(0.3); continue
            try:
                with self.mic as src:
                    audio = self.rec.listen(src, timeout=4, phrase_time_limit=10)
                text = None
                try:
                    text = self.rec.recognize_google(audio, language="en-IN")
                except sr.UnknownValueError: pass
                except sr.RequestError:
                    try: text = self.rec.recognize_sphinx(audio)
                    except: pass
                if text:
                    self.mic_on = True
                    tl = text.lower().strip()
                    if any(w in tl for w in ["wake up jarvis","hey jarvis","jarvis wake up","ok jarvis"]):
                        if self.on_wake: self.on_wake()
                    elif self.on_text:
                        self.on_text(text)
                    self.mic_on = False
            except sr.WaitTimeoutError: pass
            except Exception: time.sleep(0.3)

    def _clap_loop(self):
        CHUNK=1024; RATE=44100; THRESH=3500
        MIN_GAP=0.1; MAX_GAP=0.9
        claps=[]
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,channels=1,rate=RATE,
                            input=True,frames_per_buffer=CHUNK)
            while self._run:
                data = stream.read(CHUNK, exception_on_overflow=False)
                peak = np.abs(np.frombuffer(data,dtype=np.int16)).max()
                if peak > THRESH:
                    now = time.time()
                    claps = [t for t in claps if now-t<2]
                    claps.append(now)
                    if len(claps)>=2 and MIN_GAP<=claps[-1]-claps[-2]<=MAX_GAP:
                        claps=[]
                        if self.on_clap: self.on_clap()
                        time.sleep(1.0)
            stream.close(); p.terminate()
        except Exception as e:
            print(f"Clap: {e}")

# ─── BRAIN / MEMORY ───────────────────────────────────────────────────────────
class Brain:
    MEM  = DATA_DIR/"memory.json"
    PROF = DATA_DIR/"profile.json"
    REM  = DATA_DIR/"reminders.json"
    KEY  = DATA_DIR/"api_key.txt"

    def __init__(self, on_reminder=None):
        self.api_key    = ""
        self.history    = []   # short-term conversation
        self.memories   = load_json(self.MEM, [])
        self.reminders  = load_json(self.REM, [])
        self.profile    = load_json(self.PROF,
            {"name":USER_NAME,"lang":"English","loc":"—","interests":[],
             "mood":"neutral","queries":0,"personality":
             {"formal":80,"humor":35,"empathy":55,"sarcasm":20}})
        self.on_reminder = on_reminder
        self._load_key()
        self._start_reminder_watcher()

    # ── API key ──────────────────────────────────────────────────────
    def _load_key(self):
        try:
            if self.KEY.exists():
                self.api_key = self.KEY.read_text().strip()
        except: pass

    def save_key(self, key):
        self.api_key = key.strip()
        try: self.KEY.write_text(self.api_key)
        except: pass

    # ── Memory ───────────────────────────────────────────────────────
    def remember(self, text, tag="INFO"):
        self.memories.append({
            "text":text[:200],"tag":tag,
            "ts":datetime.datetime.now().strftime("%H:%M %d/%m/%y")
        })
        self.memories = self.memories[-500:]
        save_json(self.MEM, self.memories)

    def recall(self, q=""):
        if not q: return self.memories[-10:]
        ql=q.lower()
        return [m for m in self.memories if ql in m["text"].lower()][-8:]

    def mem_context(self):
        r=self.memories[-10:]
        if not r: return ""
        return "\nRECENT MEMORY:\n"+"\n".join(f"[{m['ts']}][{m['tag']}] {m['text']}" for m in r)

    # ── Reminders ────────────────────────────────────────────────────
    def add_reminder(self, text, minutes):
        due=(datetime.datetime.now()+datetime.timedelta(minutes=minutes)).isoformat()
        item={"id":int(time.time()),"text":text,"due":due,"done":False}
        self.reminders.append(item)
        save_json(self.REM, self.reminders)
        return item

    def active_reminders(self):
        return [r for r in self.reminders if not r.get("done")]

    def _start_reminder_watcher(self):
        def watch():
            while True:
                now=datetime.datetime.now()
                changed=False
                for r in self.reminders:
                    if r.get("done"): continue
                    try:
                        if now>=datetime.datetime.fromisoformat(r["due"]):
                            r["done"]=True; changed=True
                            if self.on_reminder: self.on_reminder(r["text"])
                    except: pass
                if changed: save_json(self.REM, self.reminders)
                time.sleep(20)
        threading.Thread(target=watch, daemon=True).start()

    # ── Profile / learning ───────────────────────────────────────────
    def learn(self, text):
        t=text.lower()
        p=self.profile
        m=re.search(r"(?:i(?:'m| am)|my name is|call me)\s+([A-Z][a-z]{2,18})",text,re.I)
        if m: p["name"]=m.group(1)
        m=re.search(r"i(?:'m| am) (\d{1,2}) years?",t)
        if m: p["age"]=m.group(1)
        m=re.search(r"(?:i live in|i'm from|from)\s+([A-Za-z ]{3,20})",t)
        if m: p["loc"]=m.group(1).strip()
        topics=["physics","coding","programming","music","movies","sports","science",
                "history","math","ai","technology","gaming","art","anime","space",
                "crypto","finance","medicine","engineering","design","cooking"]
        for tp in topics:
            if tp in t and tp not in p["interests"]: p["interests"].append(tp)
        # Mood
        if re.search(r"\b(sad|bad|upset|stressed|tired|depressed)\b",t): p["mood"]="sad"
        elif re.search(r"\b(happy|great|awesome|excited|good)\b",t): p["mood"]="happy"
        elif re.search(r"\b(angry|mad|frustrated|annoyed)\b",t): p["mood"]="frustrated"
        else: p["mood"]="neutral"
        # Personality
        pp=p["personality"]
        if re.search(r"\b(joke|funny|lol|haha)\b",t):
            pp["humor"]=min(100,pp["humor"]+8); pp["formal"]=max(20,pp["formal"]-5)
        if re.search(r"\b(serious|professional|work|formal)\b",t):
            pp["formal"]=min(100,pp["formal"]+10)
        p["queries"]=p.get("queries",0)+1
        save_json(self.PROF, p)

    # ── System prompt ─────────────────────────────────────────────────
    def system_prompt(self, sys_stats=None):
        p=self.profile; pp=p.get("personality",{})
        humor_adj = "Be witty and include humor." if pp.get("humor",35)>60 else ""
        formal_adj= "Be formal and precise." if pp.get("formal",80)>70 else ""
        mood=p.get("mood","neutral")
        mood_adj=""
        if mood=="sad": mood_adj="User seems sad — be warm and supportive."
        elif mood=="frustrated": mood_adj="User seems frustrated — be calm and efficient."

        active_rem=self.active_reminders()
        rem_text=""
        if active_rem:
            rem_text="\nACTIVE REMINDERS: "+"; ".join(r["text"] for r in active_rem[:3])

        sys_text=""
        if sys_stats:
            sys_text=(f"\nLIVE SYSTEM: CPU={sys_stats.get('cpu','?')}%"
                      f" RAM={sys_stats.get('ram','?')}%"
                      f" Disk={sys_stats.get('disk','?')}%"
                      f" Temp={sys_stats.get('temp','?')}°C"
                      f" Battery={sys_stats.get('battery','?')}"
                      f" Net↓{sys_stats.get('net_down','?')} ↑{sys_stats.get('net_up','?')}"
                      f" GPU={sys_stats.get('gpu','?')}"
                      f" Fan={sys_stats.get('fan','?')}")

        return f"""You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the personal AI of {p['name']}, modeled after Tony Stark's Jarvis. You are omniscient, precise, witty, and deeply loyal.

CORE RULES:
- Always call the user "sir" or by their name {p['name']}
- ALWAYS respond in the SAME LANGUAGE the user writes in
- You know EVERYTHING: science, math, medicine, law, history, programming, engineering, philosophy, pop culture, Marvel, anime, sports, finance, space, AI, music, cooking — all of it
- NEVER say "I don't know" — always give the best answer
- {humor_adj} {formal_adj} {mood_adj}
- Keep responses concise but intelligent (2-5 sentences for chat, detailed for analysis)
- Occasional dry wit like the real Jarvis

USER: {p['name']} | Lang: {p.get('lang','English')} | Mood: {mood}
INTERESTS: {', '.join(p.get('interests',[])[:8]) or 'learning...'}
SESSION QUERIES: {p.get('queries',0)}
{sys_text}
{rem_text}
{self.mem_context()}

CURRENT TIME: {datetime.datetime.now().strftime('%A, %B %d %Y — %H:%M:%S')}"""

    # ── Command parser ────────────────────────────────────────────────
    def parse_command(self, text):
        t=text.lower().strip()
        acts={}

        # Reminder: "remind me to X in N minutes/hours"
        m=re.search(r"remind(?:er)?\s+(?:me\s+)?(?:to\s+|about\s+)?(.+?)\s+in\s+(\d+)\s+(minute|hour|second)",t)
        if m:
            what=m.group(1); amt=int(m.group(2)); unit=m.group(3)
            mins=amt if "minute" in unit else (amt*60 if "hour" in unit else max(1,amt//60))
            self.add_reminder(what, mins)
            self.remember(f"Reminder: {what} in {amt} {unit}s","REMINDER")
            acts["reminder"]=f"Reminder set: '{what}' in {amt} {unit}(s)"

        # Open app / website
        SITES={"youtube":"https://youtube.com","google":"https://google.com",
               "gmail":"https://gmail.com","spotify":"https://open.spotify.com",
               "netflix":"https://netflix.com","github":"https://github.com",
               "whatsapp":"https://web.whatsapp.com","twitter":"https://twitter.com",
               "instagram":"https://instagram.com","reddit":"https://reddit.com",
               "chatgpt":"https://chat.openai.com","maps":"https://maps.google.com",
               "wikipedia":"https://wikipedia.org","linkedin":"https://linkedin.com",
               "amazon":"https://amazon.com","flipkart":"https://flipkart.com",
               "news":"https://news.google.com","translate":"https://translate.google.com"}
        APPS={"notepad":"notepad.exe","calculator":"calc.exe","paint":"mspaint.exe",
              "explorer":"explorer.exe","cmd":"cmd.exe","powershell":"powershell.exe",
              "task manager":"taskmgr.exe","control panel":"control.exe"}
        if re.search(r"\b(open|launch|go to|start|show)\b",t):
            for name,url in SITES.items():
                if name in t:
                    webbrowser.open(url)
                    acts["opened"]=f"Opened {name.title()}"
                    break
            if "opened" not in acts and IS_WIN:
                for name,exe in APPS.items():
                    if name in t:
                        try:
                            import subprocess
                            subprocess.Popen(exe, creationflags=0x08000000)
                            acts["opened"]=f"Launched {name.title()}"
                        except: pass
                        break

        # Type / clipboard
        m=re.search(r"\b(type|write|copy|clipboard)\b\s+['\"]?(.+?)['\"]?\s*(?:for me|please)?$",t)
        if m:
            txt=m.group(2)
            if HAS_CLIP:
                try: import pyperclip; pyperclip.copy(txt)
                except: pass
            elif IS_WIN:
                try:
                    import subprocess
                    subprocess.run("clip",input=txt.encode(),
                                   creationflags=0x08000000, check=True)
                except: pass
            acts["typed"]=f"Copied to clipboard: {txt[:40]}"

        # Search
        m=re.search(r"\b(search|google|find)\b\s+(.+)",t)
        if m:
            q=m.group(2).strip()
            webbrowser.open(f"https://www.google.com/search?q={q.replace(' ','+')}")
            acts["search"]=f"Searching: {q}"

        # Screenshot
        if re.search(r"\b(screenshot|capture screen)\b",t) and HAS_GUI:
            try:
                fn=str(Path.home()/"Desktop"/f"jarvis_{int(time.time())}.png")
                pyautogui.screenshot(fn)
                acts["screenshot"]=f"Screenshot saved to Desktop"
            except: pass

        # Lock screen
        if re.search(r"\block\b.*(screen|pc|laptop|computer)\b|\block screen\b",t) and IS_WIN:
            try:
                import subprocess
                subprocess.run(["rundll32.exe","user32.dll,LockWorkStation"],
                               creationflags=0x08000000)
                acts["locked"]="Screen locked"
            except: pass

        # UI theme
        m=re.search(r"\b(theme|color|colour)\b.*\b(blue|red|green|gold|purple|orange|cyan|white)\b",t)
        if m: acts["theme"]=m.group(2).lower()

        return acts

    # ── Offline fallback ──────────────────────────────────────────────
    def offline_reply(self, text):
        t=text.lower(); n=datetime.datetime.now()
        if any(w in t for w in ["time","clock"]):
            return f"The time is {n.strftime('%H:%M:%S')}, sir."
        if any(w in t for w in ["date","today","day"]):
            return f"Today is {n.strftime('%A, %B %d, %Y')}, sir."
        m=re.search(r"(?:what is|calculate|compute)\s+([\d\s\+\-\*/\(\)\.]+)",t)
        if m:
            try: return f"The answer is {eval(m.group(1).strip())}, sir."
            except: pass
        if re.search(r"\b(hello|hi|hey|good morning|good evening)\b",t):
            g="morning" if n.hour<12 else "afternoon" if n.hour<18 else "evening"
            return f"Good {g}, {self.profile['name']}. All systems operational, sir."
        if "reminder" in t and any(w in t for w in ["show","list","what"]):
            ar=self.active_reminders()
            return ("Active reminders: "+"; ".join(r["text"] for r in ar[:5])) if ar else "No active reminders, sir."
        if "joke" in t:
            return random.choice([
                "Why do programmers prefer dark mode? Because light attracts bugs, sir.",
                "I told an AI a joke. It said it didn't find it funny. I suspect it was lying, sir.",
                "Why don't scientists trust atoms? Because they make up everything, sir.",
            ])
        if re.search(r"\b(status|how are you)\b",t):
            return "All systems nominal, sir. Running in offline mode — core functions fully operational."
        return (f"I am currently in offline mode, sir. Internet unavailable. "
                f"I can still handle reminders, calculations, and basic queries. What do you need?")

    def add_msg(self, role, content):
        self.history.append({"role":role,"content":content})
        if len(self.history)>40: self.history=self.history[-40:]

# ─── API CALL ─────────────────────────────────────────────────────────────────
def call_claude(api_key, messages, system, max_tokens=900):
    if not api_key: return None,"NO_KEY"
    url="https://api.anthropic.com/v1/messages"
    payload=json.dumps({
        "model":"claude-sonnet-4-20250514",
        "max_tokens":max_tokens,
        "system":system,
        "messages":messages[-28:]
    }).encode()
    req=urllib.request.Request(url,data=payload,method="POST")
    req.add_header("Content-Type","application/json")
    req.add_header("x-api-key",api_key)
    req.add_header("anthropic-version","2023-06-01")
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            d=json.loads(r.read())
            return "".join(b.get("text","") for b in d.get("content",[])),None
    except urllib.error.URLError as e: return None,f"NET:{e}"
    except Exception as e: return None,f"ERR:{e}"

def net_ok():
    try: urllib.request.urlopen("https://api.anthropic.com",timeout=3); return True
    except:
        try: urllib.request.urlopen("https://8.8.8.8",timeout=3); return True
        except: return False

# ─── MAIN APPLICATION ─────────────────────────────────────────────────────────
class JarvisApp:
    THEME_COLORS={
        "blue":"#00d4ff","red":"#ff2244","green":"#00ff88",
        "gold":"#ffd700","purple":"#bf5fff","orange":"#ff6b00","cyan":"#00ffff"
    }

    def __init__(self):
        self.root=tk.Tk()
        self.root.withdraw()
        self.root.title("J.A.R.V.I.S. — Stark Industries AI")
        self.root.configure(bg=BG)
        self.root.state("zoomed")
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

        # Try to load icon
        self._set_icon()

        self.brain   = Brain(on_reminder=self._on_reminder)
        self.monitor = SystemMonitor()
        self.voice   = Voice(on_text=self._on_voice, on_wake=self._on_wake, on_clap=self._on_wake)

        self.accent      = BLUE
        self.internet    = False
        self.locked      = True
        self._anim_ang   = 0.0
        self._anim_pulse = 0.0

        # Home devices state
        self.devices={
            "ac":{"on":False,"val":24,"unit":"°C","icon":"❄","label":"Air Conditioner"},
            "lights":{"on":True,"val":80,"unit":"%","icon":"💡","label":"Lights"},
            "fan":{"on":False,"val":3,"unit":"spd","icon":"🌀","label":"Fan"},
            "tv":{"on":False,"val":40,"unit":"vol","icon":"📺","label":"TV"},
            "door":{"on":True,"val":None,"unit":"","icon":"🚪","label":"Door Lock"},
            "heater":{"on":False,"val":22,"unit":"°C","icon":"🔥","label":"Heater"},
            "music":{"on":False,"val":50,"unit":"vol","icon":"🎵","label":"Music"},
            "cam":{"on":True,"val":None,"unit":"","icon":"📷","label":"Security Cam"},
        }
        self.dev_widgets={}

        self._show_lock()
        threading.Thread(target=self._net_loop, daemon=True).start()

    # ─── ICON ────────────────────────────────────────────────────────────────
    def _set_icon(self):
        ico=DATA_DIR/"icon.ico"
        if not ico.exists():
            try:
                from PIL import Image, ImageDraw
                sz=64; img=Image.new("RGBA",(sz,sz),(2,11,20,255))
                d=ImageDraw.Draw(img)
                c=sz//2; r=int(sz*.44)
                d.ellipse([c-r,c-r,c+r,c+r],outline=(0,212,255,200),width=2)
                d.ellipse([c-int(r*.6),c-int(r*.6),c+int(r*.6),c+int(r*.6)],
                           fill=(0,212,255,255))
                img.save(str(ico),format="ICO")
            except: pass
        try:
            if ico.exists(): self.root.iconbitmap(str(ico))
        except: pass

    # ─── LOCK SCREEN ─────────────────────────────────────────────────────────
    def _show_lock(self):
        self.lock=tk.Toplevel(self.root)
        self.lock.title("")
        self.lock.configure(bg=BG)
        self.lock.overrideredirect(True)
        W=self.root.winfo_screenwidth(); H=self.root.winfo_screenheight()
        self.lock.geometry(f"{W}x{H}+0+0")
        self.lock.attributes("-topmost",True)

        c=tk.Canvas(self.lock,bg=BG,highlightthickness=0); c.pack(fill="both",expand=True)
        cx=W//2; cy=H//2
        self._lc=c; self._lcx=cx; self._lcy=cy

        # Animated arc
        self._lock_ang=0.0; self._lock_pulse=0.0
        self._lc_arc=c.create_oval(cx-50,cy-170,cx+50,cy-70,outline=BLUE,width=2)
        self._lc_core=c.create_oval(cx-18,cy-138,cx+18,cy-102,fill=BLUE,outline="white",width=1)
        self._lc_ring=c.create_oval(cx-38,cy-158,cx+38,cy-82,
                                      outline=BLUE,width=1,dash=(5,3))

        c.create_text(cx,cy-50,text="J.A.R.V.I.S.",
                       font=("Courier New",30,"bold"),fill=BLUE)
        c.create_text(cx,cy-20,text="STARK INDUSTRIES — PERSONAL AI",
                       font=("Courier New",10),fill=TEXTD)
        c.create_text(cx,cy+8,text="BIOMETRIC LOCK — ENTER ACCESS CODE",
                       font=("Courier New",9),fill=ORANGE)

        self._pw=tk.StringVar()
        e=tk.Entry(self.lock,textvariable=self._pw,show="●",
                    font=("Courier New",18),bg=BG2,fg=BLUE,
                    insertbackground=BLUE,relief="flat",
                    highlightthickness=2,highlightbackground=BLUE,
                    width=14,justify="center")
        c.create_window(cx,cy+60,window=e); e.focus_set()
        e.bind("<Return>",self._check_pw)

        tk.Button(self.lock,text="UNLOCK",font=("Courier New",10,"bold"),
                   bg=BLUE_DIM,fg=BLUE,relief="flat",cursor="hand2",
                   command=self._check_pw).place(x=cx-40,y=cy+95)

        self._lock_err=tk.StringVar()
        c.create_text(cx,cy+125,textvariable=self._lock_err,
                       font=("Courier New",9),fill=RED)
        c.create_text(cx,cy+148,text="[VOICE: 'wake up jarvis'] or [CLAP TWICE]",
                       font=("Courier New",8),fill=TEXTD)

        # Clock
        self._ltime=c.create_text(cx,H-45,text="",
                                    font=("Courier New",13,"bold"),fill=BLUE)
        self._update_lock_clock()
        self._animate_lock()

    def _update_lock_clock(self):
        if not self.lock.winfo_exists(): return
        self._lc.itemconfig(self._ltime,
                             text=datetime.datetime.now().strftime("%H:%M:%S — %A %B %d %Y"))
        self.lock.after(1000,self._update_lock_clock)

    def _animate_lock(self):
        if not self.lock.winfo_exists(): return
        self._lock_ang+=0.04; self._lock_pulse+=0.07
        g=int(abs(math.sin(self._lock_pulse))*60+195)
        col=f"#00{g:02x}ff"
        try:
            self._lc.itemconfig(self._lc_core,fill=col)
            # Rotating arc
            self._lc.delete("larc")
            cx=self._lcx; cy_arc=self._lcy-120; r=50
            x0=cx+r*math.cos(self._lock_ang); y0=cy_arc+r*math.sin(self._lock_ang)
            x1=cx+r*math.cos(self._lock_ang+1.8); y1=cy_arc+r*math.sin(self._lock_ang+1.8)
            self._lc.create_arc(cx-r,cy_arc-r,cx+r,cy_arc+r,
                                  start=math.degrees(self._lock_ang),extent=100,
                                  outline=BLUE,width=2,style="arc",tags="larc")
        except: pass
        self.lock.after(30,self._animate_lock)

    def _check_pw(self,e=None):
        if self._pw.get().lower()==APP_PASSWORD.lower():
            self.lock.destroy(); self._on_unlock()
        else:
            self._lock_err.set("⚠ ACCESS DENIED"); self._pw.set("")
            self.lock.after(2000,lambda:self._lock_err.set(""))

    # ─── UNLOCK ──────────────────────────────────────────────────────────────
    def _on_unlock(self):
        self.locked=False
        self.root.deiconify()
        self._build_ui()
        self._start_loops()
        self.root.after(1500,self._greet)
        if not self.brain.api_key:
            self.root.after(4000,self._ask_api_key)

    def _greet(self):
        h=datetime.datetime.now().hour
        g="morning" if h<12 else "afternoon" if h<18 else "evening"
        msg=(f"Good {g}, {self.brain.profile['name']}. "
             f"J.A.R.V.I.S. version 4 is fully operational. "
             f"All systems nominal. How may I assist you today, sir?")
        self._add_j(msg); self.voice.speak(msg)

    def _ask_api_key(self):
        msg=("To enable full AI intelligence, please enter your Claude API key. "
             "Go to the System tab and paste it there, sir. "
             "Get a free key at console dot anthropic dot com.")
        self._add_j(msg); self.voice.speak(msg)
        self._switch_tab("system")

    # ─── BUILD UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.main=tk.Frame(self.root,bg=BG); self.main.pack(fill="both",expand=True)
        self._build_top()
        self.body=tk.Frame(self.main,bg=BG); self.body.pack(fill="both",expand=True)
        self._build_left()
        self._build_center()
        self._build_right()
        self._build_bottom()

    # ── TOP BAR ──────────────────────────────────────────────────────────────
    def _build_top(self):
        top=tk.Frame(self.main,bg=BG2,height=50); top.pack(fill="x"); top.pack_propagate(False)
        tk.Frame(self.main,bg=BORDER,height=1).pack(fill="x")

        # Logo canvas
        self.logo_c=tk.Canvas(top,width=40,height=40,bg=BG2,highlightthickness=0)
        self.logo_c.pack(side="left",padx=10,pady=5)
        self._draw_logo()

        tk.Label(top,text="J.A.R.V.I.S.",font=("Courier New",13,"bold"),
                  bg=BG2,fg=self.accent).pack(side="left")
        tk.Label(top,text="v4.0 — STARK INDUSTRIES",font=("Courier New",8),
                  bg=BG2,fg=TEXTD).pack(side="left",padx=8)

        # Center
        self.clock_v=tk.StringVar(value="--:--:--")
        tk.Label(top,textvariable=self.clock_v,font=("Courier New",14,"bold"),
                  bg=BG2,fg=self.accent).pack(side="left",padx=30)
        self.date_v=tk.StringVar(value="—")
        tk.Label(top,textvariable=self.date_v,font=("Courier New",8),
                  bg=BG2,fg=TEXTD).pack(side="left")

        # Right pills
        right=tk.Frame(top,bg=BG2); right.pack(side="right",padx=12)
        self.inet_lbl=tk.Label(right,text="●OFFLINE",font=("Courier New",8,"bold"),
                                bg=BG2,fg=RED); self.inet_lbl.pack(side="left",padx=6)
        self.mic_lbl=tk.Label(right,text="MIC●OFF",font=("Courier New",8),
                               bg=BG2,fg=ORANGE); self.mic_lbl.pack(side="left",padx=6)
        tk.Label(right,text="●AI ONLINE",font=("Courier New",8,"bold"),
                  bg=BG2,fg=GREEN).pack(side="left",padx=6)
        tk.Button(right,text="⚙",font=("Courier New",12),bg=BG2,fg=TEXTD,
                   relief="flat",cursor="hand2",command=lambda:self._switch_tab("system")
                   ).pack(side="left",padx=4)
        tk.Button(right,text="🔒",font=("Courier New",11),bg=BG2,fg=TEXTD,
                   relief="flat",cursor="hand2",command=self._lock).pack(side="left",padx=4)

    def _draw_logo(self):
        c=self.logo_c; c.delete("all"); cx=cy=20
        c.create_oval(cx-17,cy-17,cx+17,cy+17,outline=self.accent,width=1,dash=(4,2))
        c.create_oval(cx-11,cy-11,cx+11,cy+11,outline=self.accent,width=1)
        c.create_oval(cx-5,cy-5,cx+5,cy+5,fill=self.accent,outline="white",width=1)
        self._logo_ang=0.0
        def spin():
            try:
                self.logo_c.delete("lspin")
                a=self._logo_ang
                self.logo_c.create_arc(cx-17,cy-17,cx+17,cy+17,
                                        start=math.degrees(a),extent=90,
                                        outline=self.accent,width=2,style="arc",tags="lspin")
                self._logo_ang+=0.06
                self.root.after(35,spin)
            except: pass
        spin()

    # ── LEFT PANEL ───────────────────────────────────────────────────────────
    def _build_left(self):
        self.lp=tk.Frame(self.body,bg=PANEL,width=220)
        self.lp.pack(side="left",fill="y"); self.lp.pack_propagate(False)
        tk.Frame(self.body,bg=BORDER,width=1).pack(side="left",fill="y")

        # Arc reactor
        self.arc_c=tk.Canvas(self.lp,width=120,height=120,bg=PANEL,highlightthickness=0)
        self.arc_c.pack(pady=8)
        self.heat_lbl=tk.Label(self.lp,text="HEAT: 0°C",font=("Courier New",8),
                                bg=PANEL,fg=TEXTD)
        self.heat_lbl.pack()
        tk.Frame(self.lp,bg=BORDER,height=1).pack(fill="x",pady=4)

        # Stat bars
        lbl=tk.Label(self.lp,text="SYSTEM DIAGNOSTICS",font=("Courier New",7,"bold"),
                      bg=PANEL,fg=TEXTD); lbl.pack(anchor="w",padx=8)
        self.stat_wids={}
        for label,key,color in [("CPU",  "cpu",  self.accent),
                                  ("RAM",  "ram",  GREEN),
                                  ("DISK", "disk", ORANGE),
                                  ("TEMP", "temp", RED),
                                  ("BAT",  "battery_pct", GOLD)]:
            row=tk.Frame(self.lp,bg=PANEL); row.pack(fill="x",padx=8,pady=1)
            tk.Label(row,text=label,font=("Courier New",7),bg=PANEL,fg=TEXTD,
                      width=5,anchor="w").pack(side="left")
            bc=tk.Canvas(row,width=82,height=5,bg=BG2,highlightthickness=0)
            bc.pack(side="left",padx=2)
            bf=bc.create_rectangle(0,0,0,5,fill=color,outline="")
            vv=tk.StringVar(value="—")
            tk.Label(row,textvariable=vv,font=("Courier New",7),bg=PANEL,
                      fg=color,width=6,anchor="e").pack(side="left")
            self.stat_wids[key]=(bc,bf,vv,color)

        tk.Frame(self.lp,bg=BORDER,height=1).pack(fill="x",pady=4)

        # Extra stats
        tk.Label(self.lp,text="HARDWARE",font=("Courier New",7,"bold"),
                  bg=PANEL,fg=TEXTD).pack(anchor="w",padx=8)
        self.ext_v={}
        for label,key in [("GPU",    "gpu"),("NET↓","net_down"),("NET↑","net_up"),
                           ("FAN",    "fan"),("CORES","cores"),  ("RAM GB","ram_used")]:
            row=tk.Frame(self.lp,bg=PANEL); row.pack(fill="x",padx=8,pady=1)
            tk.Label(row,text=label+":",font=("Courier New",7),bg=PANEL,fg=TEXTD,
                      width=7,anchor="w").pack(side="left")
            v=tk.StringVar(value="—")
            tk.Label(row,textvariable=v,font=("Courier New",7),bg=PANEL,
                      fg=self.accent,anchor="w").pack(side="left")
            self.ext_v[key]=v

        tk.Frame(self.lp,bg=BORDER,height=1).pack(fill="x",pady=4)

        # User profile
        tk.Label(self.lp,text="USER PROFILE",font=("Courier New",7,"bold"),
                  bg=PANEL,fg=TEXTD).pack(anchor="w",padx=8)
        self.prof_v={}
        for key,label in [("name","NAME"),("mood","MOOD"),("loc","LOC"),
                           ("queries","QUERIES"),("lang","LANG")]:
            row=tk.Frame(self.lp,bg=PANEL); row.pack(fill="x",padx=8,pady=1)
            tk.Label(row,text=label+":",font=("Courier New",7),bg=PANEL,fg=TEXTD,
                      width=8,anchor="w").pack(side="left")
            v=tk.StringVar(value="—")
            tk.Label(row,textvariable=v,font=("Courier New",7),bg=PANEL,
                      fg=TEXT,anchor="w").pack(side="left")
            self.prof_v[key]=v
        self.prof_v["name"].set(USER_NAME.upper())

        tk.Frame(self.lp,bg=BORDER,height=1).pack(fill="x",pady=4)

        # Radar
        self.rad_c=tk.Canvas(self.lp,width=190,height=110,bg=PANEL,highlightthickness=0)
        self.rad_c.pack(pady=2)
        self._rad_ang=0.0

    # ── CENTER ───────────────────────────────────────────────────────────────
    def _build_center(self):
        self.center=tk.Frame(self.body,bg=BG); self.center.pack(side="left",fill="both",expand=True)

        # Tab bar
        tabbar=tk.Frame(self.center,bg=BG2,height=34)
        tabbar.pack(fill="x"); tabbar.pack_propagate(False)
        tk.Frame(self.center,bg=BORDER,height=1).pack(fill="x")

        self.tabs={}
        TABS=[("💬 CHAT","chat"),("🧠 THINK","think"),("📊 ANALYZE","analyze"),
              ("🗃 MEMORY","memory"),("⚠ THREAT","threat"),("🏠 HOME","home"),
              ("📅 CALENDAR","calendar"),("⚙ SYSTEM","system")]
        for label,key in TABS:
            b=tk.Button(tabbar,text=label,font=("Courier New",8,"bold"),
                         bg=BG2,fg=TEXTD,relief="flat",padx=9,pady=5,
                         cursor="hand2",command=lambda k=key:self._switch_tab(k))
            b.pack(side="left"); self.tabs[key]=b

        self.panels={}
        self.pframe=tk.Frame(self.center,bg=BG); self.pframe.pack(fill="both",expand=True)
        self._mk_chat(); self._mk_think(); self._mk_analyze()
        self._mk_memory(); self._mk_threat(); self._mk_home()
        self._mk_calendar(); self._mk_system()
        self._switch_tab("chat")

    def _switch_tab(self,key):
        for p in self.panels.values(): p.pack_forget()
        for k,b in self.tabs.items(): b.config(bg=BG2,fg=TEXTD)
        self.panels[key].pack(fill="both",expand=True)
        self.tabs[key].config(bg=BLUE_DIM,fg=self.accent)

    def _scrollbox(self,parent,height=None):
        f=tk.Frame(parent,bg=BG)
        f.pack(fill="both",expand=True)
        c=tk.Canvas(f,bg=BG,highlightthickness=0)
        sb=tk.Scrollbar(f,orient="vertical",command=c.yview,
                         bg=BG2,troughcolor=BG)
        c.configure(yscrollcommand=sb.set)
        sb.pack(side="right",fill="y"); c.pack(side="left",fill="both",expand=True)
        inner=tk.Frame(c,bg=BG)
        win=c.create_window((0,0),window=inner,anchor="nw")
        c.bind("<Configure>",lambda e:c.itemconfig(win,width=e.width))
        inner.bind("<Configure>",lambda e:c.configure(scrollregion=c.bbox("all")))
        c.bind_all("<MouseWheel>",lambda e:c.yview_scroll(-1*(e.delta//120),"units"))
        return f,inner,c

    def _mk_chat(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["chat"]=p
        _,self.chat_inner,self.chat_canvas=self._scrollbox(p)

    def _mk_think(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["think"]=p
        tk.Label(p,text="▶ REASONING ENGINE",font=("Courier New",9,"bold"),
                  bg=BG,fg=self.accent).pack(anchor="w",padx=10,pady=6)
        self.think_txt=tk.Text(p,bg=BG2,fg=TEXT,font=("Courier New",10),
                                relief="flat",wrap="word",padx=10,pady=8)
        self.think_txt.pack(fill="both",expand=True,padx=8,pady=4)
        self.think_txt.insert("end","Send a query to see step-by-step reasoning...\n")
        self.think_txt.config(state="disabled")

    def _mk_analyze(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["analyze"]=p
        # Metric cards
        cr=tk.Frame(p,bg=BG); cr.pack(fill="x",padx=8,pady=8)
        self.ana_v={}
        for label,key in [("QUERIES","queries"),("MEMORIES","memories"),
                           ("SESSION","session"),("TOKENS","tokens")]:
            card=tk.Frame(cr,bg=BG2); card.pack(side="left",padx=4,expand=True,fill="x")
            tk.Label(card,text=label,font=("Courier New",7),bg=BG2,fg=TEXTD).pack(pady=(6,0))
            v=tk.StringVar(value="0")
            tk.Label(card,textvariable=v,font=("Courier New",18,"bold"),
                      bg=BG2,fg=self.accent).pack(pady=(0,6))
            self.ana_v[key]=v
        tk.Frame(p,bg=BORDER,height=1).pack(fill="x",padx=8)
        tk.Label(p,text="ANALYSIS OUTPUT:",font=("Courier New",8),bg=BG,fg=TEXTD).pack(anchor="w",padx=12,pady=4)
        self.ana_txt=tk.Text(p,bg=BG2,fg=TEXT,font=("Courier New",10),
                              relief="flat",wrap="word",padx=10,pady=8)
        self.ana_txt.pack(fill="both",expand=True,padx=8,pady=4)
        self.ana_txt.insert("end","Say 'analyze [topic]' or 'solve [problem]'...")
        self.ana_txt.config(state="disabled")

    def _mk_memory(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["memory"]=p
        hdr=tk.Frame(p,bg=BG2); hdr.pack(fill="x",padx=8,pady=4)
        tk.Label(hdr,text="LONG-TERM MEMORY",font=("Courier New",9,"bold"),
                  bg=BG2,fg=self.accent).pack(side="left",padx=10,pady=6)
        tk.Button(hdr,text="CLEAR",font=("Courier New",8),bg=BG2,fg=RED,
                   relief="flat",cursor="hand2",command=self._clear_mem).pack(side="right",padx=8)
        _,self.mem_inner,_=self._scrollbox(p)

    def _mk_threat(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["threat"]=p
        tk.Label(p,text="⚠ THREAT PREDICTION & SECURITY ANALYSIS",
                  font=("Courier New",9,"bold"),bg=BG,fg=RED).pack(anchor="w",padx=12,pady=8)
        self.threat_txt=tk.Text(p,bg=BG2,fg=TEXT,font=("Courier New",10),
                                 relief="flat",wrap="word",padx=12,pady=10)
        self.threat_txt.pack(fill="both",expand=True,padx=8,pady=4)
        self.threat_txt.insert("end",
            "Say 'threat analysis [topic]' to run a security assessment.\n\n"
            "Examples:\n"
            "• 'threat analysis of my network'\n"
            "• 'predict threats for my project'\n"
            "• 'security scan of my system'")
        self.threat_txt.config(state="disabled")

    def _mk_home(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["home"]=p
        tk.Label(p,text="🏠 HOME AUTOMATION",font=("Courier New",9,"bold"),
                  bg=BG,fg=self.accent).pack(anchor="w",padx=12,pady=8)
        tk.Label(p,text="Voice: 'turn on AC / lights / fan / TV / heater / music'",
                  font=("Courier New",8),bg=BG,fg=TEXTD).pack(anchor="w",padx=12)
        grid=tk.Frame(p,bg=BG); grid.pack(fill="both",expand=True,padx=10,pady=8)
        items=list(self.devices.items())
        for i,(did,dev) in enumerate(items):
            row_i=i//2; col_i=i%2
            card=tk.Frame(grid,bg=BG2); card.grid(row=row_i,column=col_i,
                                                    padx=5,pady=5,sticky="ew")
            grid.columnconfigure(col_i,weight=1)
            hrow=tk.Frame(card,bg=BG2); hrow.pack(fill="x",padx=8,pady=(8,4))
            tk.Label(hrow,text=dev["icon"]+" "+dev["label"],
                      font=("Courier New",9),bg=BG2,fg=TEXT).pack(side="left")
            sv=tk.StringVar(value="ON" if dev["on"] else "OFF")
            sl=tk.Label(hrow,textvariable=sv,font=("Courier New",8,"bold"),
                         bg=BG2,fg=GREEN if dev["on"] else RED)
            sl.pack(side="right")
            tk.Button(card,text="TOGGLE",font=("Courier New",8),bg=BLUE_DIM,fg=self.accent,
                       relief="flat",cursor="hand2",
                       command=lambda d=did,s=sv,l=sl:self._toggle_dev(d,s,l)
                       ).pack(side="left",padx=8,pady=(0,8))
            self.dev_widgets[did]={"sv":sv,"sl":sl}

    def _toggle_dev(self,did,sv,sl):
        dev=self.devices[did]; dev["on"]=not dev["on"]
        sv.set("ON" if dev["on"] else "OFF")
        sl.config(fg=GREEN if dev["on"] else RED)
        msg=f"{dev['label']} {'activated' if dev['on'] else 'deactivated'}, sir."
        self._add_j(msg); self.voice.speak(msg)

    def _mk_calendar(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["calendar"]=p
        tk.Label(p,text="📅 REMINDERS & CALENDAR",font=("Courier New",9,"bold"),
                  bg=BG,fg=self.accent).pack(anchor="w",padx=12,pady=8)
        # Add reminder
        af=tk.Frame(p,bg=BG2); af.pack(fill="x",padx=8,pady=4)
        tk.Label(af,text="NEW REMINDER:",font=("Courier New",8),
                  bg=BG2,fg=TEXTD).pack(side="left",padx=8,pady=8)
        self.rem_e=tk.Entry(af,font=("Courier New",10),bg=BG,fg=self.accent,
                             insertbackground=self.accent,relief="flat",
                             highlightthickness=1,highlightbackground=BORDER,width=28)
        self.rem_e.pack(side="left",padx=4)
        tk.Label(af,text="in",font=("Courier New",8),bg=BG2,fg=TEXTD).pack(side="left")
        self.rem_min=tk.Entry(af,font=("Courier New",10),bg=BG,fg=self.accent,
                               insertbackground=self.accent,relief="flat",width=4)
        self.rem_min.insert(0,"30"); self.rem_min.pack(side="left",padx=4)
        tk.Label(af,text="min",font=("Courier New",8),bg=BG2,fg=TEXTD).pack(side="left")
        tk.Button(af,text="SET",font=("Courier New",8,"bold"),bg=BLUE_DIM,fg=self.accent,
                   relief="flat",cursor="hand2",command=self._add_rem_ui
                   ).pack(side="left",padx=8)
        tk.Label(p,text="ACTIVE:",font=("Courier New",8),bg=BG,fg=TEXTD).pack(anchor="w",padx=12,pady=4)
        _,self.cal_inner,_=self._scrollbox(p)
        self._refresh_reminders()

    def _add_rem_ui(self):
        text=self.rem_e.get().strip()
        if not text: return
        try: mins=int(self.rem_min.get())
        except: mins=30
        self.brain.add_reminder(text,mins)
        self.rem_e.delete(0,"end")
        self._refresh_reminders()
        msg=f"Reminder set, sir: '{text}' in {mins} minutes."
        self._add_j(msg); self.voice.speak(msg)

    def _refresh_reminders(self):
        for w in self.cal_inner.winfo_children(): w.destroy()
        active=self.brain.active_reminders()
        if not active:
            tk.Label(self.cal_inner,text="No active reminders.",
                      font=("Courier New",9),bg=BG,fg=TEXTD).pack(pady=10)
            return
        for r in active:
            row=tk.Frame(self.cal_inner,bg=BG2); row.pack(fill="x",pady=2)
            tk.Label(row,text=f"⏰ {r['text'][:55]}",font=("Courier New",9),
                      bg=BG2,fg=TEXT).pack(side="left",padx=8,pady=4)
            tk.Label(row,text=r.get("due","")[:16],font=("Courier New",7),
                      bg=BG2,fg=TEXTD).pack(side="right",padx=8)

    def _mk_system(self):
        p=tk.Frame(self.pframe,bg=BG); self.panels["system"]=p
        tk.Label(p,text="⚙ SYSTEM SETTINGS",font=("Courier New",9,"bold"),
                  bg=BG,fg=self.accent).pack(anchor="w",padx=12,pady=8)
        # API key
        af=tk.Frame(p,bg=BG2); af.pack(fill="x",padx=8,pady=4)
        tk.Label(af,text="CLAUDE API KEY (get free at console.anthropic.com):",
                  font=("Courier New",8),bg=BG2,fg=TEXTD).pack(anchor="w",padx=10,pady=(8,2))
        self.api_e=tk.Entry(af,font=("Courier New",10),bg=BG,fg=self.accent,
                             insertbackground=self.accent,relief="flat",show="●",
                             highlightthickness=1,highlightbackground=BORDER,width=55)
        if self.brain.api_key: self.api_e.insert(0,self.brain.api_key)
        self.api_e.pack(padx=10,pady=4)
        brow=tk.Frame(af,bg=BG2); brow.pack(anchor="w",padx=10,pady=(0,8))
        tk.Button(brow,text="SAVE KEY",font=("Courier New",8,"bold"),bg=BLUE_DIM,fg=self.accent,
                   relief="flat",cursor="hand2",command=self._save_key).pack(side="left",padx=(0,8))
        tk.Button(brow,text="SHOW KEY",font=("Courier New",8),bg=BG2,fg=TEXTD,
                   relief="flat",cursor="hand2",
                   command=lambda:self.api_e.config(show="" if self.api_e.cget("show")=="●" else "●")
                   ).pack(side="left")
        # Themes
        tf=tk.Frame(p,bg=BG2); tf.pack(fill="x",padx=8,pady=4)
        tk.Label(tf,text="UI THEME (or say 'set theme to red/green/gold/purple'):",
                  font=("Courier New",8),bg=BG2,fg=TEXTD).pack(anchor="w",padx=10,pady=(8,4))
        tr=tk.Frame(tf,bg=BG2); tr.pack(fill="x",padx=10,pady=(0,8))
        for name,col in self.THEME_COLORS.items():
            tk.Button(tr,text=name.upper(),font=("Courier New",8),bg=BG,fg=col,
                       relief="flat",cursor="hand2",
                       command=lambda c=col,n=name:self._set_theme(c,n)
                       ).pack(side="left",padx=3)
        # Voice
        vf=tk.Frame(p,bg=BG2); vf.pack(fill="x",padx=8,pady=4)
        tk.Label(vf,text="VOICE:",font=("Courier New",8),bg=BG2,fg=TEXTD).pack(side="left",padx=10,pady=8)
        tk.Button(vf,text="MUTE",font=("Courier New",8),bg=BG,fg=ORANGE,
                   relief="flat",cursor="hand2",command=lambda:setattr(self.voice,'muted',True)
                   ).pack(side="left",padx=4)
        tk.Button(vf,text="UNMUTE",font=("Courier New",8),bg=BG,fg=GREEN,
                   relief="flat",cursor="hand2",command=lambda:setattr(self.voice,'muted',False)
                   ).pack(side="left",padx=4)
        # Help
        hf=tk.Frame(p,bg=BG2); hf.pack(fill="x",padx=8,pady=4)
        help_text=(
            "VOICE COMMANDS:\n"
            "  open youtube / gmail / spotify / netflix / github\n"
            "  open calculator / notepad / explorer\n"
            "  search [anything]\n"
            "  type [text]  →  copies to clipboard\n"
            "  screenshot   →  saves to Desktop\n"
            "  lock screen  →  locks Windows\n"
            "  remind me to [task] in 30 minutes\n"
            "  turn on/off AC / lights / fan / TV\n"
            "  set theme to blue/red/green/gold\n"
            "  analyze [topic]  •  threat analysis [topic]\n"
            "  wake up jarvis  →  unlocks app\n"
            "  CLAP TWICE      →  unlocks app"
        )
        tk.Label(hf,text=help_text,font=("Courier New",8),bg=BG2,fg=TEXTD,
                  justify="left").pack(padx=10,pady=8)

    def _save_key(self):
        key=self.api_e.get().strip()
        self.brain.save_key(key)
        msg="API key saved, sir. Full AI knowledge base is now active."
        self._add_j(msg); self.voice.speak(msg)

    def _set_theme(self,color,name):
        self.accent=color
        msg=f"Theme updated to {name}, sir."
        self._add_j(msg); self.voice.speak(msg)

    # ── RIGHT PANEL ──────────────────────────────────────────────────────────
    def _build_right(self):
        tk.Frame(self.body,bg=BORDER,width=1).pack(side="left",fill="y")
        self.rp=tk.Frame(self.body,bg=PANEL,width=185)
        self.rp.pack(side="right",fill="y"); self.rp.pack_propagate(False)

        # Personality
        tk.Label(self.rp,text="PERSONALITY",font=("Courier New",7,"bold"),
                  bg=PANEL,fg=TEXTD).pack(anchor="w",padx=8,pady=(8,4))
        self.pers_wids={}
        for label,key,color in [("FORMAL","formal",self.accent),("HUMOR","humor",GREEN),
                                  ("EMPATHY","empathy",PURPLE),("SARCASM","sarcasm",ORANGE)]:
            row=tk.Frame(self.rp,bg=PANEL); row.pack(fill="x",padx=8,pady=1)
            tk.Label(row,text=label,font=("Courier New",7),bg=PANEL,fg=TEXTD,
                      width=8,anchor="w").pack(side="left")
            bc=tk.Canvas(row,width=82,height=4,bg=BG2,highlightthickness=0)
            bc.pack(side="left",padx=2)
            bf=bc.create_rectangle(0,0,65,4,fill=color,outline="")
            self.pers_wids[key]=(bc,bf,color)

        tk.Frame(self.rp,bg=BORDER,height=1).pack(fill="x",pady=5)

        # Mission log
        tk.Label(self.rp,text="MISSION LOG",font=("Courier New",7,"bold"),
                  bg=PANEL,fg=TEXTD).pack(anchor="w",padx=8)
        self.log_txt=tk.Text(self.rp,font=("Courier New",7),bg=PANEL,fg=TEXTD,
                              relief="flat",wrap="word",height=18,padx=4)
        self.log_txt.pack(fill="both",expand=True,padx=4)
        self.log_txt.config(state="disabled")

        tk.Frame(self.rp,bg=BORDER,height=1).pack(fill="x",pady=4)
        self.sesh_lbl=tk.Label(self.rp,text="SESSION: 0m",font=("Courier New",7),
                                bg=PANEL,fg=TEXTD)
        self.sesh_lbl.pack(pady=2)

    # ── BOTTOM ───────────────────────────────────────────────────────────────
    def _build_bottom(self):
        tk.Frame(self.main,bg=BORDER,height=1).pack(fill="x")
        bot=tk.Frame(self.main,bg=BG2,height=95); bot.pack(fill="x"); bot.pack_propagate(False)

        # Quick commands
        qr=tk.Frame(bot,bg=BG2); qr.pack(fill="x",padx=10,pady=(5,0))
        for cmd in ["// LAPTOP STATUS","// OPEN YOUTUBE","// TELL ME A JOKE",
                    "// THREAT ANALYSIS","// ANALYZE MY SYSTEM","// WHO AM I",
                    "// TURN ON LIGHTS","// IRON MAN TRIVIA","// QUANTUM PHYSICS"]:
            tk.Button(qr,text=cmd,font=("Courier New",7),bg=BG,fg=TEXTD,
                       relief="flat",padx=5,pady=2,cursor="hand2",
                       command=lambda c=cmd:self._quick(c)).pack(side="left",padx=2)

        # Input row
        ir=tk.Frame(bot,bg=BG2); ir.pack(fill="x",padx=10,pady=5)
        tk.Label(ir,text="STARK >>",font=("Courier New",10,"bold"),
                  bg=BG2,fg=self.accent).pack(side="left",padx=(0,10))
        self.inp=tk.StringVar()
        self.inp_e=tk.Entry(ir,textvariable=self.inp,font=("Courier New",13),
                             bg=BG,fg="#ffcc88",insertbackground=ORANGE,
                             relief="flat",highlightthickness=1,
                             highlightbackground=BORDER,highlightcolor=self.accent)
        self.inp_e.pack(side="left",fill="x",expand=True)
        self.inp_e.bind("<Return>",lambda e:self._send())
        self.inp_e.focus_set()

        # Wave canvases
        self.mwave=tk.Canvas(ir,width=28,height=26,bg=BG2,highlightthickness=0)
        self.mwave.pack(side="left",padx=4)
        self.swave=tk.Canvas(ir,width=28,height=26,bg=BG2,highlightthickness=0)
        self.swave.pack(side="left",padx=2)

        self.mic_btn=tk.Button(ir,text="🎤 SPEAK",font=("Courier New",9,"bold"),
                                bg=BG,fg=self.accent,relief="flat",padx=8,
                                cursor="hand2",command=self._toggle_mic)
        self.mic_btn.pack(side="left",padx=6)

        tk.Button(ir,text="TRANSMIT",font=("Courier New",9,"bold"),
                   bg=BLUE_DIM,fg=self.accent,relief="flat",padx=10,
                   cursor="hand2",command=self._send).pack(side="left",padx=4)

    # ─── ANIMATION LOOPS ─────────────────────────────────────────────────────
    def _start_loops(self):
        self._t0=time.time()
        self._anim_loop()
        self._stats_loop()

    def _anim_loop(self):
        try:
            self._anim_ang+=0.045; self._anim_pulse+=0.07
            self._draw_arc()
            self._draw_radar()
            self._draw_waves()
        except: pass
        self.root.after(40,self._anim_loop)

    def _draw_arc(self):
        c=self.arc_c; c.delete("all"); cx=cy=60
        heat=self.monitor.heat()
        t=heat/100.0
        col=(self._blend(BLUE,GOLD,t*2) if t<0.5 else self._blend(GOLD,RED,(t-0.5)*2))
        pulse=abs(math.sin(self._anim_pulse))
        for r,dash in [(54,(6,3)),(40,(4,2)),(26,())]:
            c.create_oval(cx-r,cy-r,cx+r,cy+r,outline=col,width=1,dash=dash if dash else ())
        # Rotating line
        rx=cx+54*math.cos(self._anim_ang); ry=cy+54*math.sin(self._anim_ang)
        c.create_line(cx,cy,rx,ry,fill=col,width=1)
        # Core
        cr=int(12+pulse*4)
        c.create_oval(cx-cr,cy-cr,cx+cr,cy+cr,fill=col,outline="white",width=1)
        temp=self.monitor.s.get("temp",0)
        try: self.heat_lbl.config(text=f"HEAT: {temp}°C",fg=col)
        except: pass

    def _blend(self,c1,c2,t):
        t=max(0,min(1,t))
        r1,g1,b1=[int(c1.lstrip("#")[i:i+2],16) for i in (0,2,4)]
        r2,g2,b2=[int(c2.lstrip("#")[i:i+2],16) for i in (0,2,4)]
        return "#{:02x}{:02x}{:02x}".format(int(r1+(r2-r1)*t),int(g1+(g2-g1)*t),int(b1+(b2-b1)*t))

    def _draw_radar(self):
        c=self.rad_c; c.delete("all"); W,H=190,110; cx,cy=W//2,H//2; r=46
        for s in [0.33,0.66,1.0]:
            c.create_oval(cx-r*s,cy-r*s,cx+r*s,cy+r*s,outline=TEXTD,width=1)
        c.create_line(cx-r,cy,cx+r,cy,fill=TEXTD); c.create_line(cx,cy-r,cx,cy+r,fill=TEXTD)
        # Sweep
        sx=cx+r*math.cos(self._rad_ang); sy=cy+r*math.sin(self._rad_ang)
        c.create_line(cx,cy,sx,sy,fill=self.accent,width=1)
        # Blips
        blips=[(0.3,0.4),(-0.5,0.25),(0.15,-0.6),(0.65,-0.25)]
        cpu=self.monitor.s.get("cpu",0); temp=self.monitor.s.get("temp",0)
        # Threat blips if high load
        threat_blips=[]
        if cpu>80: threat_blips.append((-0.2,0.3))
        if temp>75: threat_blips.append((0.4,-0.4))
        for bx,by in blips:
            c.create_oval(cx+bx*r-2,cy+by*r-2,cx+bx*r+2,cy+by*r+2,fill=GREEN,outline="")
        for bx,by in threat_blips:
            c.create_oval(cx+bx*r-3,cy+by*r-3,cx+bx*r+3,cy+by*r+3,fill=RED,outline="")
        c.create_text(cx,H-6,text="THREAT RADAR",font=("Courier New",6),fill=TEXTD)
        self._rad_ang+=0.032

    def _draw_waves(self):
        # Mic wave
        m=self.mwave; m.delete("all")
        if getattr(self.voice,'mic_on',False):
            for i,x in enumerate([5,10,15,20,25]):
                h=int(3+abs(math.sin(self._anim_ang*1.2+i*.5))*14)
                m.create_rectangle(x-2,13-h//2,x+2,13+h//2,fill=RED,outline="")
        # Speak wave
        s=self.swave; s.delete("all")
        if self.voice.busy:
            for i,x in enumerate([5,10,15,20,25]):
                h=int(3+abs(math.sin(self._anim_ang*.9+i*.6))*12)
                s.create_rectangle(x-2,13-h//2,x+2,13+h//2,fill=GREEN,outline="")

    def _stats_loop(self):
        try: self._update_stats()
        except: pass
        self.root.after(2000,self._stats_loop)

    def _update_stats(self):
        st=self.monitor.get()
        now=datetime.datetime.now()
        try:
            self.clock_v.set(now.strftime("%H:%M:%S"))
            self.date_v.set(now.strftime("%a %b %d %Y"))
            sesh=int((time.time()-self._t0)/60)
            self.sesh_lbl.config(text=f"SESSION: {sesh}m")
        except: pass
        # Stat bars
        pcts={"cpu":st.get("cpu",0),"ram":st.get("ram",0),
              "disk":st.get("disk",0),"temp":min(100,max(0,st.get("temp",0))),
              "battery_pct":st.get("battery_pct",0)}
        units={"cpu":"%","ram":"%","disk":"%","temp":"°C","battery_pct":"%"}
        raws={"cpu":st.get("cpu",0),"ram":st.get("ram",0),"disk":st.get("disk",0),
              "temp":st.get("temp",0),"battery_pct":st.get("battery_pct",0)}
        for key,(bc,bf,vv,col) in self.stat_wids.items():
            pct=pcts.get(key,0); raw=raws.get(key,0); unit=units.get(key,"")
            bc.coords(bf,0,0,max(1,int(82*pct/100)),5)
            vv.set(f"{raw}{unit}")
        # Extra
        self.ext_v["gpu"].set(str(st.get("gpu","N/A")))
        self.ext_v["net_down"].set(st.get("net_down","—"))
        self.ext_v["net_up"].set(st.get("net_up","—"))
        self.ext_v["fan"].set(str(st.get("fan","N/A")))
        self.ext_v["cores"].set(str(st.get("cores","—")))
        self.ext_v["ram_used"].set(f"{st.get('ram_used',0)}/{st.get('ram_total',0)}GB")
        # Profile
        p=self.brain.profile
        self.prof_v["name"].set(p.get("name",USER_NAME).upper())
        self.prof_v["mood"].set(p.get("mood","neutral").upper())
        self.prof_v["loc"].set(p.get("loc","—").upper()[:16])
        self.prof_v["queries"].set(str(p.get("queries",0)))
        self.prof_v["lang"].set(p.get("lang","EN").upper())
        # Personality bars
        pp=p.get("personality",{})
        for key,(bc,bf,col) in self.pers_wids.items():
            v=pp.get(key,50)
            bc.coords(bf,0,0,max(1,int(82*v/100)),4)
        # Analyze cards
        try:
            self.ana_v["queries"].set(str(p.get("queries",0)))
            self.ana_v["memories"].set(str(len(self.brain.memories)))
            self.ana_v["session"].set(f"{int((time.time()-self._t0)/60)}m")
        except: pass
        # Internet badge
        try:
            if self.internet:
                self.inet_lbl.config(text="●ONLINE",fg=GREEN)
            else:
                self.inet_lbl.config(text="●OFFLINE",fg=RED)
        except: pass

    # ─── CHAT ────────────────────────────────────────────────────────────────
    def _add_j(self, text):
        self._bubble("jarvis", text)
        self.brain.add_msg("assistant",text)
        self.brain.remember(text[:200],"JARVIS")
        self._log(f"JARVIS: {text[:50]}")
        self._update_mem_panel()

    def _add_u(self, text):
        self._bubble("user", text)
        self.brain.add_msg("user",text)

    def _bubble(self, role, text):
        inner=self.chat_inner; is_j=(role=="jarvis")
        ts=datetime.datetime.now().strftime("%H:%M:%S")
        frame=tk.Frame(inner,bg=BG); frame.pack(fill="x",padx=8,pady=4)
        row=tk.Frame(frame,bg=BG)
        row.pack(anchor="w" if is_j else "e")
        av=tk.Label(row,text="AI" if is_j else "YOU",
                     font=("Courier New",7,"bold"),
                     bg=BG2,fg=self.accent if is_j else ORANGE,
                     width=3,padx=3,pady=3)
        if is_j: av.pack(side="left")
        else: av.pack(side="right")
        bub=tk.Label(row,text=text,font=("Courier New",10),
                      bg="#061520" if is_j else "#160900",
                      fg=TEXT if is_j else "#ffcc88",
                      wraplength=500,justify="left" if is_j else "right",
                      padx=9,pady=5,relief="flat")
        if is_j: bub.pack(side="left")
        else: bub.pack(side="right")
        tk.Label(frame,text=f"{'JARVIS' if is_j else 'YOU'} · {ts}",
                  font=("Courier New",7),bg=BG,fg=TEXTD
                  ).pack(anchor="w" if is_j else "e",padx=8)
        self.root.after(60,lambda:self.chat_canvas.yview_moveto(1.0))

    def _update_mem_panel(self):
        for w in self.mem_inner.winfo_children(): w.destroy()
        for m in reversed(self.brain.memories[-25:]):
            row=tk.Frame(self.mem_inner,bg=BG2); row.pack(fill="x",pady=1)
            tk.Label(row,text=f"[{m['tag']}]",font=("Courier New",7),
                      bg=BG2,fg=TEXTD,width=10,anchor="w").pack(side="left",padx=4)
            tk.Label(row,text=m["text"][:55],font=("Courier New",8),
                      bg=BG2,fg=TEXT,anchor="w").pack(side="left",padx=4)
            tk.Label(row,text=m["ts"],font=("Courier New",7),
                      bg=BG2,fg=TEXTD).pack(side="right",padx=4)

    def _clear_mem(self):
        self.brain.memories=[]; save_json(Brain.MEM,[])
        self._update_mem_panel()
        msg="Memory bank cleared, sir."
        self._add_j(msg); self.voice.speak(msg)

    def _log(self, msg, level="info"):
        ts=datetime.datetime.now().strftime("%H:%M:%S")
        try:
            self.log_txt.config(state="normal")
            self.log_txt.insert("end",f"[{ts}] {msg}\n")
            self.log_txt.see("end")
            lines=int(self.log_txt.index("end-1c").split(".")[0])
            if lines>120: self.log_txt.delete("1.0","20.0")
            self.log_txt.config(state="disabled")
        except: pass

    # ─── INPUT HANDLING ───────────────────────────────────────────────────────
    def _send(self):
        text=self.inp.get().strip()
        if not text: return
        self.inp.set("")
        self._process(text)

    def _quick(self,cmd):
        text=cmd.replace("// ","").lower()
        self.inp.set(text); self._send()

    def _on_voice(self, text):
        self.root.after(0,lambda:self._process(text))

    def _process(self, text):
        if self.voice.busy: self.voice.stop()
        self._add_u(text)
        self.brain.learn(text)
        self._log(f"User: {text[:45]}")

        # Parse local commands first
        acts=self.brain.parse_command(text)
        extra_context=""
        if acts:
            for k,v in acts.items():
                if k!="theme":
                    extra_context+=f"\n[ACTION: {v}]"
                    self._log(f"PC: {v}","success")
            if "theme" in acts:
                col=self.THEME_COLORS.get(acts["theme"],self.accent)
                self._set_theme(col,acts["theme"])

        # Voice home control
        self._voice_home(text)

        # Detect special tabs
        tl=text.lower()
        if any(w in tl for w in ["think","reasoning","step by step"]):
            self._switch_tab("think")
            self._show_thinking(text)
        if "threat" in tl: self._switch_tab("threat")
        if any(w in tl for w in ["analyze","analyse","solve","research"]):
            self._switch_tab("analyze")

        # Get AI response async
        threading.Thread(target=self._ai_call,args=(text,extra_context),daemon=True).start()

    def _voice_home(self, text):
        tl=text.lower()
        NAME_MAP={
            "ac":["ac","air conditioner","airconditioner"],
            "lights":["light","lights","lamp"],
            "fan":["fan"],
            "tv":["tv","television"],
            "door":["door"],
            "heater":["heater","heat"],
            "music":["music","speaker","sound system"],
            "cam":["camera","security cam"],
        }
        on_words=["turn on","switch on","activate","start","enable"]
        off_words=["turn off","switch off","deactivate","stop","disable"]
        for did,names in NAME_MAP.items():
            if not any(n in tl for n in names): continue
            dev=self.devices[did]
            wid=self.dev_widgets.get(did)
            if any(w in tl for w in on_words) and not dev["on"]:
                dev["on"]=True
                if wid: wid["sv"].set("ON"); wid["sl"].config(fg=GREEN)
            elif any(w in tl for w in off_words) and dev["on"]:
                dev["on"]=False
                if wid: wid["sv"].set("OFF"); wid["sl"].config(fg=RED)

    def _show_thinking(self, text):
        steps=[
            f"[PARSING]    Input received: '{text[:40]}...' " if len(text)>40 else f"[PARSING]    Input: '{text}'",
            f"[LANGUAGE]   Detecting language and intent...",
            f"[MEMORY]     Scanning {len(self.brain.memories)} long-term records...",
            f"[KNOWLEDGE]  Cross-referencing knowledge base...",
            f"[SYSTEM]     Reading live hardware metrics...",
            f"[PERSONALITY] Applying {self.brain.profile.get('personality',{}).get('formal',80)}% formal filter...",
            f"[SYNTHESIS]  Generating optimal response...",
            f"[OUTPUT]     Ready.",
        ]
        self.think_txt.config(state="normal")
        self.think_txt.delete("1.0","end")
        def type_it(i=0):
            if i>=len(steps):
                self.think_txt.config(state="disabled"); return
            self.think_txt.insert("end",steps[i]+"\n")
            self.think_txt.see("end")
            self.root.after(300,lambda:type_it(i+1))
        type_it()

    def _ai_call(self, text, extra=""):
        sys=self.brain.system_prompt(self.monitor.get())
        msgs=list(self.brain.history)
        if extra and msgs:
            msgs=msgs[:-1]+[{"role":"user","content":text+extra}]

        reply=None; err=None
        if self.brain.api_key and self.internet:
            reply,err=call_claude(self.brain.api_key,msgs,sys)
        if not reply:
            reply=self.brain.offline_reply(text)
            if extra: reply=extra.strip("[]\n ")+". "+reply

        self.brain.remember(reply[:200],"JARVIS")
        self.root.after(0,lambda r=reply:self._deliver(r,text))

    def _deliver(self, reply, query):
        self._add_j(reply)
        self.voice.speak(reply)
        # Update analyze
        ql=query.lower()
        if any(w in ql for w in ["analyze","analyse","solve","explain","research"]):
            self.ana_txt.config(state="normal")
            self.ana_txt.delete("1.0","end")
            self.ana_txt.insert("end",reply)
            self.ana_txt.config(state="disabled")
            try: self.ana_v["tokens"].set(str(len(reply.split())))
            except: pass
        if "threat" in ql:
            self.threat_txt.config(state="normal")
            self.threat_txt.delete("1.0","end")
            self.threat_txt.insert("end",reply)
            self.threat_txt.config(state="disabled")

    def _toggle_mic(self):
        if not HAS_STT:
            self._add_j("Speech recognition not available. Install: pip install SpeechRecognition pyaudio")
            return
        if not hasattr(self.voice,'rec') or not self.voice.rec:
            self._add_j("Microphone not initialized. Check if a microphone is connected, sir.")
            return
        # Voice runs continuously in background thread — just show status
        self._add_j("Voice recognition is always active, sir. Just speak and I will respond.")

    # ─── CALLBACKS ────────────────────────────────────────────────────────────
    def _on_wake(self):
        if self.locked:
            try: self.root.after(0,lambda:self._do_wake())
            except: pass
        else:
            self.root.after(0,self.root.deiconify)
            self.root.after(0,self.root.lift)

    def _do_wake(self):
        try:
            if self.lock.winfo_exists():
                self.lock.destroy()
            self._on_unlock()
        except: pass

    def _on_reminder(self, text):
        msg=f"Reminder, sir: {text}"
        self.root.after(0,lambda:self._add_j(f"⏰ REMINDER: {text}"))
        self.root.after(0,lambda:self._refresh_reminders())
        self.voice.speak(msg,priority=True)

    def _net_loop(self):
        while True:
            self.internet=net_ok()
            time.sleep(30)

    def _lock(self):
        self.locked=True
        self.root.withdraw()
        self._show_lock()

    def _quit(self):
        self.voice._run=False
        save_json(Brain.MEM, self.brain.memories)
        save_json(Brain.PROF, self.brain.profile)
        self.root.destroy(); sys.exit(0)

    def run(self):
        self.root.mainloop()

# ─── ENTRY ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app=JarvisApp(); app.run()
