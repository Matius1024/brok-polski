"""Instalator polskiej narracji dostępności dla gry Brok the InvestiGator.

Pobiera polskie nagrania (głos IVONA Jacek) z wydania na GitHubie i podmienia nimi
angielskie pliki w folderze access gry. Angielskie pliki zostają w folderze access_eng.
"""
import ctypes
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

REPO = "Matius1024/brok-polski"
AUDIO_URL = f"https://github.com/{REPO}/releases/latest/download/brok-pl-audio.zip"
ADDON_URL = f"https://github.com/{REPO}/releases/latest/download/brok-polski.nvda-addon"
STEAM_APPID = "949480"
MARKER = "brok-pl-installed.json"


def setup_console():
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
        ctypes.windll.kernel32.SetConsoleTitleW("Instalator Brok po polsku")
    except Exception:
        pass
    for stream in (sys.stdout, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def ask(prompt):
    try:
        return input(prompt + " ").strip()
    except EOFError:
        return ""


def yes(prompt):
    return ask(prompt + " (t = tak, n = nie)").lower().startswith(("t", "y"))


# ---------------------------------------------------------------- finding the game

def steam_paths():
    paths = []
    try:
        import winreg
        for root, key, value in [
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
        ]:
            try:
                with winreg.OpenKey(root, key) as k:
                    paths.append(os.path.normpath(winreg.QueryValueEx(k, value)[0]))
            except OSError:
                pass
    except ImportError:
        pass
    return paths


def steam_libraries():
    libs = []
    for steam in steam_paths():
        libs.append(steam)
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, encoding="utf-8", errors="replace") as f:
                for line in f:
                    parts = line.strip().split('"')
                    if len(parts) >= 4 and parts[1] == "path":
                        libs.append(os.path.normpath(parts[3].replace("\\\\", "\\")))
        except OSError:
            pass
    seen, out = set(), []
    for lib in libs:
        if lib.lower() not in seen:
            seen.add(lib.lower())
            out.append(lib)
    return out


def is_brok(folder):
    return bool(folder) and os.path.isfile(os.path.join(folder, "Brokgame.exe")) and \
        os.path.isdir(os.path.join(folder, "access"))


def find_brok():
    for lib in steam_libraries():
        manifest = os.path.join(lib, "steamapps", f"appmanifest_{STEAM_APPID}.acf")
        installdir = "Brok"
        try:
            with open(manifest, encoding="utf-8", errors="replace") as f:
                for line in f:
                    parts = line.strip().split('"')
                    if len(parts) >= 4 and parts[1] == "installdir":
                        installdir = parts[3]
        except OSError:
            pass
        folder = os.path.join(lib, "steamapps", "common", installdir)
        if is_brok(folder):
            return folder
    return None


def browse_folder():
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Wybierz folder gry Brok the InvestiGator (z plikiem Brokgame.exe)")
        root.destroy()
        return os.path.normpath(folder) if folder else None
    except Exception as e:
        print("Nie udało się otworzyć okna wyboru folderu:", e)
        return None


def choose_game_folder():
    found = find_brok()
    if found:
        print(f"Znaleziono grę Brok the InvestiGator w folderze:\n  {found}")
    else:
        print("Nie znaleziono gry Brok the InvestiGator w bibliotekach Steam.")
    while True:
        print()
        if found:
            print("Enter - użyj tego folderu")
        print("W - wybierz folder gry w oknie")
        print("P - wpisz ścieżkę do folderu gry")
        print("Q - anuluj")
        c = ask("Twój wybór:").lower()
        if c == "" and found:
            return found
        if c == "q":
            return None
        folder = None
        if c == "w":
            folder = browse_folder()
        elif c == "p":
            folder = ask("Ścieżka do folderu gry:").strip('"')
        if folder:
            if is_brok(folder):
                return folder
            print(f"W folderze {folder} nie ma gry Brok (brak pliku Brokgame.exe lub folderu access).")


# ---------------------------------------------------------------- download / install

def download(url, dest, label):
    print(f"Pobieranie: {label}")
    req = urllib.request.Request(url, headers={"User-Agent": "brok-polski-installer"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done, next_report = 0, 10
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total and done * 100 // total >= next_report:
                print(f"  {next_report}%")
                next_report += 10
    print("Pobieranie zakończone.")


def install_audio(game):
    access = os.path.join(game, "access")
    backup = os.path.join(game, "access_eng")
    if not os.path.isdir(backup):
        print("Kopiuję oryginalne angielskie nagrania do folderu access_eng...")
        shutil.copytree(access, backup)
    else:
        print("Kopia angielskich nagrań już istnieje (access_eng), zostawiam ją bez zmian.")
    tmp = os.path.join(tempfile.gettempdir(), "brok-pl-audio.zip")
    try:
        download(AUDIO_URL, tmp, "polskie nagrania (około 95 MB)")
        with zipfile.ZipFile(tmp) as z:
            info = json.loads(z.read("brok-pl-audio.json").decode("utf-8"))
            names = [n for n in z.namelist() if n.lower().endswith(".ogg")]
            print(f"Instaluję {len(names)} polskich nagrań...")
            for n in names:
                target = os.path.normpath(os.path.join(access, n))
                if not target.startswith(os.path.normpath(access) + os.sep):
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(n) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        with open(os.path.join(access, MARKER), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(f"Gotowe. Zainstalowano polską narrację w wersji {info.get('version', '?')}.")
    print("Jeśli Steam zweryfikuje pliki gry albo ją zaktualizuje, uruchom instalator ponownie.")


def restore_english(game):
    access = os.path.join(game, "access")
    backup = os.path.join(game, "access_eng")
    if not os.path.isdir(backup):
        print("Brak kopii angielskich nagrań (folder access_eng). Możesz je przywrócić,")
        print("weryfikując pliki gry w Steam: Biblioteka, Brok, Właściwości, Zainstalowane pliki.")
        return
    print("Przywracam angielskie nagrania...")
    for root, dirs, files in os.walk(backup):
        rel = os.path.relpath(root, backup)
        os.makedirs(os.path.join(access, rel), exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(root, f), os.path.join(access, rel, f))
    try:
        os.remove(os.path.join(access, MARKER))
    except OSError:
        pass
    print("Gotowe. Gra ma znowu angielską narrację.")


def install_addon():
    tmp = os.path.join(tempfile.gettempdir(), "brok-polski.nvda-addon")
    download(ADDON_URL, tmp, "dodatek NVDA Brok po polsku")
    print("Otwieram dodatek. NVDA zapyta, czy go zainstalować, a potem o ponowne uruchomienie.")
    os.startfile(tmp)


def show_tips():
    print()
    print("Jak grać z polską narracją:")
    print("- Polskie nagrania gra odtwarza sama, gdy w opcjach dostępności jest włączona opcja W pełni narrowany.")
    print("  Język gry ustaw na polski.")
    print("- Jeśli chcesz, żeby NVDA czytał też kwestie z angielskiego dubbingu (polskie napisy),")
    print("  zainstaluj dodatek NVDA (opcja 3) i włącz w grze, w opcjach dostępności,")
    print("  obie opcje: Narracja schowka oraz Wysyłaj kwestie z podkładem głosowym do schowka.")
    print("  Dodatek odtworzy wtedy teksty dostępności polskimi nagraniami, a kwestie przeczyta NVDA.")
    print("  NVDA+Shift+B włącza i wyłącza dodatek.")


def main():
    setup_console()
    print("Instalator polskiej narracji dostępności dla gry Brok the InvestiGator.")
    print("Nagrania: głos IVONA Jacek. Projekt: https://github.com/" + REPO)
    game = None
    while True:
        print()
        print("1 - Zainstaluj polskie nagrania")
        print("2 - Przywróć angielskie nagrania")
        print("3 - Zainstaluj dodatek NVDA (czytanie kwestii z dubbingu)")
        print("4 - Jak grać z polską narracją")
        print("0 - Wyjście")
        c = ask("Wybierz numer i naciśnij Enter:")
        try:
            if c in ("1", "2"):
                if not game:
                    game = choose_game_folder()
                if not game:
                    continue
                if c == "1":
                    install_audio(game)
                    show_tips()
                else:
                    restore_english(game)
            elif c == "3":
                install_addon()
            elif c == "4":
                show_tips()
            elif c == "0" or c == "":
                if c == "0" or yes("Zakończyć?"):
                    return
        except PermissionError:
            print("Brak dostępu do plików gry. Zamknij grę i spróbuj ponownie,")
            print("a jeśli to nie pomoże, uruchom instalator jako administrator.")
        except Exception as e:
            print("Wystąpił błąd:", e)


if __name__ == "__main__":
    main()
