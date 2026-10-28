# Brok po polsku – polska narracja dostępności

Nieoficjalna polska narracja dostępności dla gry **Brok the InvestiGator** (Steam). Gra ma pełny tryb dla osób niewidomych, ale nagrania tej narracji (opisy pomieszczeń, nazwy przedmiotów, menu, podpowiedzi) są tylko po angielsku, nawet gdy język gry jest ustawiony na polski. Ten projekt podmienia je na polskie nagrania.

- **6109 polskich nagrań**, głos IVONA 2 Jacek, szybkość 65%.
- Teksty pochodzą z oficjalnego polskiego tłumaczenia gry.
- **DLC The Brawl Bar** nie ma w grze polskiego tłumaczenia, więc zostało przetłumaczone na potrzeby tego projektu (z wersji hiszpańskiej).
- Dźwięki, cisza i tytuły utworów muzycznych zostają oryginalne.

## Instalacja

1. Pobierz **BrokPolskiInstalator.exe** z najnowszego wydania: [Releases](https://github.com/Matius1024/brok-polski/releases/latest).
2. Zamknij grę i uruchom instalator. Działa w oknie konsoli, więc czytnik ekranu czyta go bez problemu.
3. Wybierz **1 – Zainstaluj polskie nagrania**. Instalator:
   - sam znajdzie grę w bibliotekach Steam albo pozwoli wybrać lub wpisać inny folder;
   - sprawdzi, czy w folderze jest gra (plik `Brokgame.exe` i folder `access`);
   - skopiuje oryginalne angielskie nagrania do folderu `access_eng`;
   - pobierze polskie nagrania (około 95 MB) i podmieni nimi angielskie.
4. W grze ustaw język polski i w opcjach dostępności włącz **W pełni narrowany**.

Opcja **2** przywraca angielskie nagrania z kopii. Jeśli Steam zweryfikuje pliki gry albo ją zaktualizuje, polskie nagrania mogą zostać nadpisane. Wtedy uruchom instalator ponownie.

## Dodatek NVDA: kwestie z dubbingu

Gra ma angielski dubbing. Jeśli chcesz, żeby NVDA czytał też polskie napisy do kwestii postaci:

1. W instalatorze wybierz **3 – Zainstaluj dodatek NVDA** albo pobierz `brok-polski.nvda-addon` z wydania i otwórz go.
2. W grze, w opcjach dostępności, włącz **Narracja schowka** oraz **Wysyłaj kwestie z podkładem głosowym do schowka**.

W tym trybie gra wysyła teksty do schowka zamiast odtwarzać nagrania. Dodatek rozpoznaje teksty, które mają polskie nagranie, i odtwarza je głosem Jacka z folderu gry. Gdy gra skleja kilka tekstów, odtwarza kilka nagrań po kolei. Pozostałe teksty, czyli głównie kwestie z dubbingu, czyta NVDA.

- Dodatek działa tylko wtedy, gdy na wierzchu jest okno gry.
- **NVDA+Shift+B** włącza i wyłącza dodatek.
- Jeśli masz dodatek clipReader, podczas gry jest on wyciszany, żeby teksty nie były czytane dwa razy.
- Wymaga NVDA 2024.1 lub nowszego (wersja 64-bitowa). Do odczytu plików ogg używa biblioteki libsndfile (licencja LGPL, w pliku `libsndfile_COPYING.txt`).

## Dla twórców

- `tools/build.py` buduje nagrania od nowa: `python build.py all`. Ścieżkę gry ustawia zmienna `BROK_GAME`.
  - Kolejne etapy: dopasowanie tekstów, synteza przez SAPI (`synth.ps1`), konwersja ffmpeg do ogg vorbis 24 kHz mono o głośności −24,5 LUFS oraz mapa dla dodatku NVDA.
  - Wymaga zainstalowanego głosu IVONA 2 Jacek i programu ffmpeg.
- `tools/dlc_pl.txt` to polskie tłumaczenie DLC, a `tools/extra_pl.txt` to kilka tekstów dopisanych ręcznie.
- `installer/brok_instalator.py` to instalator. Plik exe buduje się poleceniem `pyinstaller --onefile --console brok_instalator.py`.
- `nvda_addon/` to dodatek NVDA.

## Zastrzeżenia

Projekt jest nieoficjalny i nie jest związany z twórcami gry (COWCAT). Gra, jej teksty i tłumaczenia należą do ich właścicieli. Nagrania są syntezą mowy oficjalnego polskiego tłumaczenia gry, a tłumaczenie DLC zostało przygotowane w tym projekcie.
