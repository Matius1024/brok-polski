"""Builds Polish accessibility audio for Brok the InvestiGator with IVONA 2 Jacek.

Usage: python build.py plan | synth | convert | all
The English originals are kept in <game>/access_eng; <game>/access gets the Polish files.
"""
import os, re, sys, json, shutil, subprocess, glob
from concurrent.futures import ThreadPoolExecutor

GAME = os.environ.get("BROK_GAME", r"D:\SteamLibrary\steamapps\common\Brok")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(GAME, "access_eng")
DST = os.path.join(GAME, "access")
TXT = os.path.join(GAME, "txt", "pol")
WORK = os.path.join(HERE, "work")
VOICE = "IVONA 2 Jacek OEM"
RATE = 3  # SAPI rate -10..10; 0 = 50%, 3 = about 65%
WAVDIR = os.path.join(WORK, "wav" if RATE == 0 else f"wav_r{RATE}")

# Sounds and music titles: keep the English recording.
KEEP = re.compile(r"^(\d+|SILENCE.*|AUDIOD_SILENCE|SOUND_.*|TUTORIAL_BELL|TROPHY_UNLOCKED|OST_.*|ACCESSIBILITY_FLAG|"
                  r"ACCESSIBILITY_MOBILE_.*|ACCESSIBILITY_SCREEN_FLIP|HELP_BLINDMOVE_INSTRUCTIONS_TOUCH)$")

ONES = ["zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć", "dziesięć",
        "jedenaście", "dwanaście", "trzynaście", "czternaście", "piętnaście", "szesnaście", "siedemnaście",
        "osiemnaście", "dziewiętnaście"]
TENS = ["", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt", "sześćdziesiąt",
        "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt"]


def number_pl(n):
    if n < 20:
        return ONES[n]
    t, o = divmod(n, 10)
    return TENS[t] + ("" if o == 0 else " " + ONES[o])


def parse(path):
    d = {}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().replace("|", "")
            if k and v.strip() and k not in d:
                d[k] = v.strip()
    return d


def clean(t):
    t = re.sub(r"<(spr|button)=[^>]*>", " ", t)
    t = re.sub(r"</?[a-zA-Z]+(=[^>]*)?>", "", t)
    t = re.sub(r"\{[^}]*\}", " ", t)
    t = t.replace("##", ". ").replace("#", ". ")
    t = re.sub(r"(^|[\s(])>\s*", r"\1powyżej ", t)
    t = re.sub(r"(^|[\s(])<\s*", r"\1poniżej ", t)
    t = t.replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([.,!?])", r"\1", t)
    t = re.sub(r"([!?])\.(?!\.)", r"\1", t)
    t = re.sub(r"(?<!\.)\.\.(?!\.)", ".", t)
    t = re.sub(r"^[\s.,]+", "", t)
    return t.strip()


def load_tables():
    files = {fn[:-4].upper(): parse(os.path.join(TXT, fn)) for fn in os.listdir(TXT) if fn.lower().endswith(".txt")}
    files["TDLC"] = parse(os.path.join(HERE, "dlc_pl.txt"))
    files["EXTRA"] = parse(os.path.join(HERE, "extra_pl.txt"))
    return files


def lookup(files, folder, key):
    base = folder[1:]
    prio = ["T" + base, "ACCESS", "TCOMMON", "TDLC", "EXTRA"] + sorted(files)
    cands = [key, key.split("=")[0], key.replace(".##", "")]
    for k in cands:
        for p in prio:
            v = files.get(p, {}).get(k)
            if v:
                if re.fullmatch(r"[A-Z0-9_]+", v) and "_" in v and v != k:
                    return lookup(files, folder, v) or v
                return v
    # KEYn = n-th "##" part of KEY (MDIRECTOR2_n uses MDIRECTOR2_TEXT)
    m = re.match(r"^(.*?)(_?)(\d+)$", key)
    if m:
        stem, n = m.group(1), int(m.group(3))
        for b in (stem, stem + "_TEXT"):
            for p in prio:
                v = files.get(p, {}).get(b)
                if v and "##" in v:
                    parts = [x for x in v.split("##") if clean(x)]
                    if 1 <= n <= len(parts):
                        return parts[n - 1]
    m = re.match(r"^NUMBER_(\d+)$", key)
    if m:
        return number_pl(int(m.group(1)))
    return None


def plan():
    if not os.path.isdir(SRC):
        print("Backing up English files to", SRC)
        shutil.copytree(DST, SRC)
    files = load_tables()
    jobs, raws, kept, missing = {}, {}, [], []
    for folder in sorted(os.listdir(SRC)):
        fdir = os.path.join(SRC, folder)
        if not os.path.isdir(fdir):
            continue
        for fn in sorted(os.listdir(fdir)):
            if not fn.lower().endswith(".ogg"):
                continue
            key = fn[:-4]
            rel = folder + "/" + fn
            if KEEP.match(key):
                kept.append(rel); continue
            raw = lookup(files, folder, key)
            text = clean(raw) if raw else ""
            if not re.search(r"\w", text):
                missing.append(rel); continue
            jobs[rel] = text
            raws[rel] = raw
    os.makedirs(WORK, exist_ok=True)
    json.dump(raws, open(os.path.join(WORK, "raw.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(jobs, open(os.path.join(WORK, "jobs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    open(os.path.join(WORK, "kept_english.txt"), "w", encoding="utf-8").write("\n".join(kept + missing))
    print(f"polish={len(jobs)} kept_sounds={len(kept)} no_text={len(missing)}")
    print("no text:", " ".join(missing))
    return jobs


def synth(jobs, nproc=4):
    texts = sorted(set(jobs.values()))
    ids = {t: i for i, t in enumerate(texts)}
    json.dump(ids, open(os.path.join(WORK, "texts.json"), "w", encoding="utf-8"), ensure_ascii=False)
    wavdir = WAVDIR; os.makedirs(wavdir, exist_ok=True)
    todo = [(i, t) for t, i in ids.items() if not os.path.exists(os.path.join(wavdir, f"{i}.wav"))]
    print(f"unique texts={len(texts)} to synthesize={len(todo)}")
    chunks = [todo[k::nproc] for k in range(nproc)]
    procs = []
    for k, ch in enumerate(chunks):
        if not ch:
            continue
        lst = os.path.join(WORK, f"synth_{k}.tsv")
        with open(lst, "w", encoding="utf-8") as f:
            for i, t in ch:
                f.write(f"{os.path.join(wavdir, str(i) + '.wav')}\t{t}\n")
        procs.append(subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                       os.path.join(HERE, "synth.ps1"), lst, VOICE, str(RATE)]))
    for p in procs:
        p.wait()


def convert(jobs):
    ids = json.load(open(os.path.join(WORK, "texts.json"), encoding="utf-8"))
    wavdir = WAVDIR
    def one(item):
        rel, text = item
        wav = os.path.join(wavdir, f"{ids[text]}.wav")
        out = os.path.join(DST, *rel.split("/"))
        if not os.path.exists(wav) or os.path.getsize(wav) < 1000:
            return rel
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "loudnorm=I=-24.5:TP=-6:LRA=11",
                            "-ar", "24000", "-ac", "1", "-c:a", "libvorbis", "-q:a", "4", out],
                           capture_output=True)
        return rel if r.returncode else None
    with ThreadPoolExecutor(8) as ex:
        bad = [r for r in ex.map(one, jobs.items()) if r]
    print(f"converted={len(jobs) - len(bad)} failed={len(bad)}", bad[:20])


def norm(t):
    """Same normalization as the NVDA add-on: letters and digits only, lowercase."""
    t = re.sub(r"<[^>]*>|\{[^}]*\}", " ", t)
    return re.sub(r"[\W_]+", "", t.lower())


def nvda_map(jobs):
    """Writes text -> recording (path relative to the game's access folder) for the NVDA add-on."""
    raws = json.load(open(os.path.join(WORK, "raw.json"), encoding="utf-8"))
    m = {}
    for rel, text in jobs.items():
        for t in [text, raws.get(rel, "")] + raws.get(rel, "").split("##"):
            k = norm(t)
            if len(k) >= 2:
                m.setdefault(k, rel)
    out = os.path.join(HERE, "..", "nvda_addon", "globalPlugins", "brokPolski", "brok_map.json")
    json.dump(m, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("nvda map entries:", len(m))


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "plan"
    jobs = plan()
    if stage in ("synth", "all"):
        synth(jobs)
    if stage in ("convert", "all"):
        convert(jobs)
    if stage in ("nvda", "all"):
        nvda_map(jobs)
