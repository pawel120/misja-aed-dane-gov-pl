# Dla Jury: Misja AED – wykaz defibrylatorów w kodzie dane.gov.pl

Nie budujemy aplikacji obok portalu. Dopisaliśmy do **otwartego kodu dane.gov.pl** (backend 2.63.0)
mechanizm „Wykaz AED”, wzorowany na istniejącym w portalu wykazie chronionych danych DGA:

1. instytucja (samorząd, urząd, firma, fundacja, OSP) publikuje **własny zasób** z wykazem swoich AED
   i zaznacza „Zawiera wykaz defibrylatorów AED: TAK” – odpowiada za swoje dane;
2. portal sprawdza plik **walidacjami AED** i od razu pokazuje dostawcy, które wiersze poprawić;
3. raz na dobę portal skleja wszystkie poprawne wykazy w zbiór
   **„Wykaz defibrylatorów AED – raport zbiorczy”** na profilu Ministerstwa Cyfryzacji,
   z kolumnami „Nazwa dostawcy”, „Możliwy duplikat”, „Ostrzeżenia walidacji”;
4. raport ma od razu ustawioną **mapę portalu** (szerokość, długość, nazwa miejsca).

## Klikalny prototyp

**Jeden link: https://portal.145-239-30-81.sslip.io/aed** – raport zbiorczy AED na mapie portalu (przewiń w dół do zakładki „Mapa”).

| Co | Adres |
|---|---|
| **Strona publiczna portalu** (frontend dane.gov.pl bez zmian): raport zbiorczy z mapą | https://portal.145-239-30-81.sslip.io/pl/dataset/6,wykaz-defibrylatorow-aed-raport-zbiorczy |
| Wyszukiwarka portalu | https://portal.145-239-30-81.sslip.io/pl/search?q=defibrylator |
| Panel administracyjny portalu (z modułem) | https://admin.145-239-30-81.sslip.io |
| API portalu: zbiór raportu zbiorczego (Ministerstwo Cyfryzacji) | https://api.145-239-30-81.sslip.io/1.4/datasets/6 |
| API portalu: punkty mapy raportu zbiorczego | https://api.145-239-30-81.sslip.io/1.4/resources/8/geo (zasób raportu jest stały; codzienne przeliczenie podmienia tylko jego plik) |
| API portalu: wiersze raportu z wyszukiwaniem | https://api.145-239-30-81.sslip.io/1.4/resources/8/data?q=Krosno |
| **Wejście do panelu jednym kliknięciem** | link podany w zgłoszeniu (HackTribe), ważny do 22.11.2026, 23:59; loguje na konto jury bez wpisywania hasła |
| Konto dla jury (zapasowo) | e-mail i hasło podane w zgłoszeniu (HackTribe) |

To środowisko testowe (pasek u góry każdej strony), nie serwis dane.gov.pl.

## Kroki dla jury (ok. 5 minut)

0. Bez logowania: wejdź na stronę publiczną, wpisz w wyszukiwarkę „defibrylator”, otwórz
   „Wykaz defibrylatorów AED” i zakładkę **Mapa** – 775 AED od 5 dostawców na mapie portalu.
   Strona działa także na telefonie (układ portalu jest responsywny).
1. Otwórz link ze zgłoszenia – od razu jesteś w panelu, na liście zasobów (**Dane → Zasoby**).
   Bez linku: zaloguj się e-mailem i hasłem ze zgłoszenia.
2. Otwórz „Wykaz AED – Urząd Miasta Legionowo”. Pod polem wykazu chronionych danych (DGA)
   jest nasze pole **„Zawiera wykaz defibrylatorów AED: Tak”** z opisem mechanizmu.
   Kliknij **„Zapisz i kontynuuj edycję”**: panel podziękuje dostawcy
   („Dzięki Tobie 12 797 mieszkańców ma AED w promieniu 200 m w otwartych danych”).
   Jeśli pole „Dane na dzień” jest puste, kliknij „Dzisiaj”.
3. Otwórz „Wykaz AED – Fundacja Przykładowa (dane testowe)”: 4 urządzenia, w tym 3 z celowymi błędami.
   Kliknij „Zapisz”: formularz nie zapisze zasobu i wypisze 3 błędne wiersze z powodami
   (zamienione współrzędne, zły zapis godzin, zła wartość TAK/NIE).
4. Na liście zasobów wybierz dowolny wiersz, z menu akcji wybierz
   **„Utwórz teraz zbiorczy wykaz defibrylatorów AED”** i kliknij „Wykonaj”.
   Komunikat pokaże: ile AED od ilu dostawców, ile wierszy odrzucono u każdego dostawcy.
5. Wejdź w **Dane → Datasets → „Wykaz defibrylatorów AED – raport zbiorczy”** (instytucja: Ministerstwo Cyfryzacji).
   Zasób „Wykaz defibrylatorów AED” ma plik CSV, widok tabeli i mapę.
6. Otwórz w przeglądarce API `/1.4/resources/8/geo` – punkty mapy z raportu zbiorczego.
7. (Opcjonalnie) Dodaj zasób z plikiem `demo_aed/dane/wykaz_aed_testowy_z_bledami.csv`
   i zaznacz „Contains AED list: Tak” – formularz nie zapisze pliku i wypisze błędy w wierszach.

## Gdzie sprawdzić każde wymaganie z treści zadania

| Wymaganie (pkt 4 i 5 treści) | Gdzie | Jak sprawdzić |
|---|---|---|
| Integracja informacji od wielu dysponentów w jednym zbiorze | `mcod/resources/aed_utils.py`, `aed_validation.py` (`build_main_aed_df`) | krok 4–5 |
| Zgodność z zasadami działania dane.gov.pl | zmiany w kodzie portalu: `git diff f90a02f` (pierwszy commit = czysty kod portalu) | pole w panelu (krok 2), raport jako zwykły zasób portalu, mapa portalu |
| Wzorcowy zakres danych (xlsx) | `wzorzec/WYKAZ_AED_-_dostawca_XYZ.xlsx` (32 kolumny, 2 przykładowe wiersze) i `wzorzec/opis_kolumn_wykazu_AED.xlsx`; te same kolumny w kodzie: `mcod/resources/aed_constants.py` | test `TestFilesFromRepository` sprawdza, że wzorzec ma kolumny z kodu i przechodzi walidacje |
| Format odczytywalny maszynowo | raport zbiorczy: CSV UTF-8, API JSON | krok 5–6 |
| Kod źródłowy | to repozytorium | `git log`, testy niżej |
| Prototyp | strona publiczna i panel pod adresami wyżej | kroki 0–7 |
| Logotyp (jpg, png, pdf, format otwarty) i księga znaku (pdf) | `kampania/`: logo pełne, pionowe i znak mały w wersjach kolor, czerń, negatyw (SVG, PNG, JPG, PDF); `kampania/ksiega_znaku.pdf` | otwórz pliki |
| Responsywność, WCAG | strona publiczna portalu (ich frontend: przełączniki kontrastu i wielkości czcionki) | otwórz na telefonie |

## Kroki użytkownika

**Dostawca danych** (samorząd, urząd, firma, fundacja, OSP), w panelu portalu, tak jak przy każdym innym zasobie:
1. Pobiera wzorzec `WYKAZ_AED_-_dostawca_XYZ.xlsx` i wpisuje swoje urządzenia (jeden wiersz = jeden AED; puste pole = „X”).
2. Dodaje zasób z plikiem (csv, xls, xlsx) i zaznacza „Zawiera wykaz defibrylatorów AED: TAK”.
3. Jeśli plik ma błędy, formularz nie zapisuje zasobu i wypisuje numery wierszy z powodami
   (np. „zamienione współrzędne”, „data w formacie rrrr-mm-dd”). Dostawca poprawia plik i wgrywa go ponownie.
4. Po zapisaniu poprawnego wykazu panel dziękuje i pokazuje, ilu mieszkańców ma dzięki niemu AED w otwartych danych:
   „Dziękujemy. Dzięki Tobie 12 797 mieszkańców ma AED w promieniu 200 m w otwartych danych.” (Legionowo, 24 AED).
5. Kiedy zmieni się stan urządzeń, podmienia plik w tym samym zasobie.

**Portal** codziennie o 05:00 skleja opublikowane wykazy w raport zbiorczy (administrator może to zrobić od razu akcją w panelu).
Ten sam zasób raportu dostaje nowy plik, więc adres strony, mapy i API się nie zmienia.
Komunikat akcji podaje przy każdym dostawcy liczbę mieszkańców w promieniu 200 m i sumę dla całego raportu
(dane demo: 775 AED, 509 266 osób).

**Mieszkańcy w zasięgu AED** (`PopulationGrid` w `aed_validation.py`): okrąg 200 m wokół każdego AED dzielimy
na kwadraty 50 × 50 m na wspólnej siatce; kwadrat dostaje 1/400 ludności swojej komórki 1 km. Kwadraty sumujemy
bez powtórzeń, więc urządzenia blisko siebie nie liczą tych samych osób dwa razy. Źródło ludności: siatka 1 km
ze spisu powszechnego 2021 (Eurostat GISCO, Census grid 2021, dane GUS), przycięta do Polski
(`data/aed/ludnosc_pl_1km_epsg3035.npz`, EPSG:3035). Liczba jest szacunkiem do komunikatów w panelu,
nie trafia do publicznego raportu.

**Obywatel i służby**: wyszukiwarka portalu („defibrylator”), mapa raportu, plik CSV do pobrania, API portalu (`/geo`, `/data`).

## Zasilanie ręczne i automatyczne

Wykaz AED dostawca może publikować tak samo jak każdy zasób portalu:

- **ręcznie** w panelu: zasób z plikiem i pole „Zawiera wykaz defibrylatorów AED: Tak” (kroki wyżej);
- **automatycznie** przez import portalu (harvester), na wzór pola `containsProtectedData` wykazu DGA:
  - plik XML w nowej wersji schematu **1.14** (`data/harvester/xml_import_otwarte_dane_1_14.xsd` = 1.13 +
    element `<containsAedList>true</containsAedList>` w zasobie; przykład:
    `data/test_samples/harvester/import_example1.14.xml`); starsze wersje 1.0–1.13 działają bez zmian,
  - katalog CKAN: pole zasobu `contains_aed_list`.

  Zasób z importu dostaje flagę „wykaz AED” i trafia do raportu zbiorczego jak zasób z panelu
  (w panelu flaga jest wtedy tylko do odczytu, jak inne pola z importu). Sprawdzone importem pliku XML 1.14
  w lokalnym portalu i testami `mcod/harvester/tests/test_aed_harvester.py`.

## Walidacje AED (`mcod/resources/aed_validation.py`)

Wiersz z błędem nie trafia do raportu, a dostawca dostaje powód. Sprawdzamy:
- wymagane kolumny wzorca (wykaz bez nich jest pomijany w całości) i brak powtórzonych kolumn;
- identyfikator, nazwa miejsca, miejscowość i współrzędne są wypełnione; identyfikator nie powtarza się w wykazie;
- współrzędne to liczby WGS84 z kropką i leżą w Polsce; zamienione szerokość i długość są wykrywane wprost;
- TAK/NIE, daty rrrr-mm-dd, kod pocztowy 00-000, godziny w każdym dniu tygodnia (`08:00-16:00`, `24h`, `nieczynne`),
  położenie (`wewnątrz`, `na zewnątrz`), spójność „dostęp 24h” z dniami „nieczynne”.

Ostrzeżenia nie blokują wiersza: elektrody lub bateria tracące ważność w ciągu 90 dni, możliwy duplikat
(urządzenie innego dostawcy bliżej niż 15 m; dostawca to instytucja w portalu, nie sama nazwa, więc dwa
„Urzędy Gminy” są różnymi dostawcami, a dwa wykazy jednej instytucji – jednym).

Wartości wpisane przez dostawców są ujednolicane do zapisu wzorca: „Wewnątrz” → „wewnątrz”, „24H” → „24h”, „8:00 - 16:00” → „08:00-16:00”.
Komórki raportu zaczynające się od `=`, `+`, `-`, `@` dostają apostrof, żeby arkusz nie wykonał ich jako formuły
(ochrona przed CSV injection).

Odczyt pliku idzie drogą portalu: komórki Excela (daty, liczby) są czytane jako tekst wzorca, kodowanie CSV
(UTF-8, Windows-1250, ISO-8859-2) rozpoznajemy tymi samymi bajtami co `mcod.resources.guess.file_encoding`,
a komunikaty formularza idą przez tłumaczenia portalu, jak w wykazie DGA.

## Testy

Testy modułu AED (163 przechodzi, bez bazy danych): `mcod/resources/tests/test_aed_validation.py`, `test_aed_files.py`, `test_aed_forms.py`, `test_aed_residents.py`, `test_aed_demo_login.py` i `mcod/harvester/tests/test_aed_harvester.py`.
Obejmują pliki z repozytorium (wzorzec, dane demo), pliki zapisane przez Excel, CSV z różnych programów
i kodowań, wartości skrajne, raport 20 000 AED oraz walidację danych samego portalu (goodtables), którą zasób
musi przejść, żeby trafić do raportu. Jeden test oznaczony `xfail` opisuje znane ograniczenie (niżej).

```
python -m pytest mcod/resources/tests/test_aed_validation.py mcod/resources/tests/test_aed_files.py mcod/resources/tests/test_aed_forms.py mcod/resources/tests/test_aed_residents.py mcod/resources/tests/test_aed_demo_login.py mcod/harvester/tests/test_aed_harvester.py --noconftest -o addopts=""
```
(w kontenerze aplikacji portalu, z zainstalowanym `pytest` i `pytest-django`)

## Użycie sztucznej inteligencji

Kod modułu, testy i dokumentację pisaliśmy z asystentem AI (Claude Code, Anthropic), który pracował na
naszych poleceniach w lokalnym repozytorium. Decyzje należały do zespołu: wybór zadania i podejścia
(moduł w kodzie portalu na wzór DGA zamiast osobnej aplikacji), zakres wzorca danych (m.in. godziny w siedmiu
kolumnach i położenie urządzenia), dobór źródeł danych, nazwa i hasło kampanii. Każdą zmianę sprawdzaliśmy
na działającym portalu (zrzuty ekranu w prezentacji) i testami; przegląd kodu przed oddaniem wykrył i poprawił
błędy w obsłudze plików z Excela i w komunikatach formularza.

## Kampania „Twoje dane, czyjeś serce”

Znak to serce narysowane jak arkusz danych: każda czerwona kratka to AED, którego dane trafiły na dane.gov.pl.
Koncepcja, kolorystyka, pole ochronne, minimalna wielkość, niedozwolone użycia i zastosowania są w
`kampania/ksiega_znaku.pdf`. Kampania jest wpięta w portal: po zapisaniu wykazu dostawca dostaje w panelu
podziękowanie z liczbą mieszkańców, którzy dzięki niemu mają AED w promieniu 200 m w otwartych danych
(krok 2 wyżej); tę liczbę można przenieść na plakat z księgi znaku.

## Dane

Wykazy 4 instytucji z otwartych zbiorów (Legionowo, Krosno, Przemyśl: CC0 1.0; Warszawa: CC BY 4.0),
przepisane na wzorcowy zakres danych, oraz jeden wykaz testowy z celowymi błędami (nie jest to prawdziwa instytucja).

## Ograniczenia

- Nie stawialiśmy CMS portalu (Wagtail). Treści stron informacyjnych i aktualności strona testowa czyta tylko do odczytu z publicznego API CMS dane.gov.pl.
- Frontend portalu jest zbudowany bez zmian; wyłączyliśmy tylko wysyłanie raportów błędów do Sentry ministerstwa.
- Raport zbiorczy powstaje w zadaniu Celery o 05:00; w demo jury uruchamia go akcją w panelu.
- Dane demo to 5 dostawców; w Polsce wykazy AED publikuje dziś kilkanaście miast, w różnych formatach.
- Godziny dostępności w danych miast są nieustrukturyzowane; w wykazach demo wpisaliśmy „24h” tylko tam,
  gdzie źródło podaje dostęp całodobowy, w pozostałych „X”.
- „Dostęp 24h: TAK” przy ograniczonych godzinach w dniu tygodnia nie jest jeszcze zgłaszany.
- Liczba mieszkańców to szacunek z siatki 1 km (ludność rozłożona równo w komórce); przy samej granicy
  prostokąt siatki obejmuje też komórki krajów sąsiednich.
- Automatyczny import ustawia samą flagę „wykaz AED”; walidacje AED dostawca widzi przy imporcie dopiero
  w podsumowaniu raportu zbiorczego, nie w raporcie importu (w panelu dostaje je od razu przy wgraniu pliku).

## Uruchomienie u siebie

Logowanie jednym kliknięciem działa tylko w ustawieniach demo (`mcod/settings/aed_demo.py`,
`mcod/resources/aed_demo_login.py`). Kodu linku nie ma w repozytorium: ustawia się go w zmiennej
`AED_DEMO_LOGIN_TOKEN` albo w pliku `data/aed/demo_login_token.txt` (w `.gitignore`). Bez kodu adres nie działa.

`demo_aed/README.md` (Docker Compose, porty tylko na 127.0.0.1).
