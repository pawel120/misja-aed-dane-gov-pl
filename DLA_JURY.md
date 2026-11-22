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
| Konto dla jury | e-mail i hasło podane w zgłoszeniu (HackTribe) |

To środowisko testowe (pasek u góry każdej strony), nie serwis dane.gov.pl.

## Kroki dla jury (ok. 5 minut)

0. Bez logowania: wejdź na stronę publiczną, wpisz w wyszukiwarkę „defibrylator”, otwórz
   „Wykaz defibrylatorów AED” i zakładkę **Mapa** – 775 AED od 5 dostawców na mapie portalu.
   Strona działa także na telefonie (układ portalu jest responsywny).
1. Zaloguj się do panelu. Wejdź w **Dane → Resources**.
2. Otwórz „Wykaz AED – Urząd Miasta Legionowo”. Pod polem DGA „Contains protected data list”
   jest nasze pole **„Contains AED list: Tak”** z opisem mechanizmu.
3. Otwórz „Wykaz AED – Fundacja Przykładowa (dane testowe)”: 4 urządzenia, w tym 3 z celowymi błędami.
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
| Responsywność, WCAG | strona publiczna portalu (ich frontend: przełączniki kontrastu i wielkości czcionki) | otwórz na telefonie |

## Kroki użytkownika

**Dostawca danych** (samorząd, urząd, firma, fundacja, OSP), w panelu portalu, tak jak przy każdym innym zasobie:
1. Pobiera wzorzec `WYKAZ_AED_-_dostawca_XYZ.xlsx` i wpisuje swoje urządzenia (jeden wiersz = jeden AED; puste pole = „X”).
2. Dodaje zasób z plikiem (csv, xls, xlsx) i zaznacza „Zawiera wykaz defibrylatorów AED: TAK”.
3. Jeśli plik ma błędy, formularz nie zapisuje zasobu i wypisuje numery wierszy z powodami
   (np. „zamienione współrzędne”, „data w formacie rrrr-mm-dd”). Dostawca poprawia plik i wgrywa go ponownie.
4. Kiedy zmieni się stan urządzeń, podmienia plik w tym samym zasobie.

**Portal** codziennie o 05:00 skleja opublikowane wykazy w raport zbiorczy (administrator może to zrobić od razu akcją w panelu).
Ten sam zasób raportu dostaje nowy plik, więc adres strony, mapy i API się nie zmienia.

**Obywatel i służby**: wyszukiwarka portalu („defibrylator”), mapa raportu, plik CSV do pobrania, API portalu (`/geo`, `/data`).

## Walidacje AED (`mcod/resources/aed_validation.py`)

Wiersz z błędem nie trafia do raportu, a dostawca dostaje powód. Sprawdzamy:
- wymagane kolumny wzorca (wykaz bez nich jest pomijany w całości) i brak powtórzonych kolumn;
- identyfikator, nazwa miejsca, miejscowość i współrzędne są wypełnione; identyfikator nie powtarza się w wykazie;
- współrzędne to liczby WGS84 z kropką i leżą w Polsce; zamienione szerokość i długość są wykrywane wprost;
- TAK/NIE, daty rrrr-mm-dd, kod pocztowy 00-000, godziny w każdym dniu tygodnia (`08:00-16:00`, `24h`, `nieczynne`),
  położenie (`wewnątrz`, `na zewnątrz`), spójność „dostęp 24h” z dniami „nieczynne”.

Ostrzeżenia nie blokują wiersza: elektrody lub bateria tracące ważność w ciągu 90 dni, możliwy duplikat
(urządzenie innego dostawcy bliżej niż 15 m).

Odczyt pliku idzie drogą portalu: komórki Excela (daty, liczby) są czytane jako tekst wzorca, kodowanie CSV
(UTF-8, Windows-1250, ISO-8859-2) rozpoznajemy tymi samymi bajtami co `mcod.resources.guess.file_encoding`,
a komunikaty formularza idą przez tłumaczenia portalu, jak w wykazie DGA.

## Testy

Testy modułu AED (113 przechodzi, bez bazy danych): `mcod/resources/tests/test_aed_validation.py`, `test_aed_files.py`, `test_aed_forms.py`.
Obejmują pliki z repozytorium (wzorzec, dane demo), pliki zapisane przez Excel, CSV z różnych programów
i kodowań, wartości skrajne, raport 20 000 AED oraz walidację danych samego portalu (goodtables), którą zasób
musi przejść, żeby trafić do raportu. Kolejne 6 testów oznaczonych `xfail` opisuje znane ograniczenia (niżej).

```
python -m pytest mcod/resources/tests/test_aed_validation.py mcod/resources/tests/test_aed_files.py mcod/resources/tests/test_aed_forms.py --noconftest -o addopts=""
```
(w kontenerze aplikacji portalu, z zainstalowanym `pytest` i `pytest-django`)

## Użycie sztucznej inteligencji

Kod modułu, testy i dokumentację pisaliśmy z asystentem AI (Claude Code, Anthropic), który pracował na
naszych poleceniach w lokalnym repozytorium. Decyzje należały do zespołu: wybór zadania i podejścia
(moduł w kodzie portalu na wzór DGA zamiast osobnej aplikacji), zakres wzorca danych (m.in. godziny w siedmiu
kolumnach i położenie urządzenia), dobór źródeł danych, nazwa i hasło kampanii. Każdą zmianę sprawdzaliśmy
na działającym portalu (zrzuty ekranu w prezentacji) i testami; przegląd kodu przed oddaniem wykrył i poprawił
błędy w obsłudze plików z Excela i w komunikatach formularza.

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
- Wartości słownikowe muszą mieć zapis ze wzorca: „Wewnątrz” albo „24H” są odrzucane z podaniem powodu.
- „Dostęp 24h: TAK” przy ograniczonych godzinach w dniu tygodnia nie jest jeszcze zgłaszany.
- Dostawcy w raporcie są rozróżniani po nazwie instytucji, nie po jej identyfikatorze.
- Raport CSV nie zabezpiecza komórek zaczynających się od „=” przed otwarciem jako formuła w arkuszu.
- Flaga „wykaz AED” jest tylko w panelu. Automatyczny import portalu (harvester XML/CKAN) nie ma jeszcze
  pola AED; następny krok to jedno pole, tak jak `containsProtectedData` dla DGA.

## Uruchomienie u siebie

`demo_aed/README.md` (Docker Compose, porty tylko na 127.0.0.1).
