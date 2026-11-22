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

| Co | Adres |
|---|---|
| Panel administracyjny portalu (z modułem) | https://admin.145-239-30-81.sslip.io |
| API portalu: zbiór raportu zbiorczego (Ministerstwo Cyfryzacji) | https://api.145-239-30-81.sslip.io/1.4/datasets/6 |
| API portalu: punkty mapy raportu zbiorczego | https://api.145-239-30-81.sslip.io/1.4/resources/ID/geo (ID = numer zasobu „Wykaz defibrylatorów AED” z panelu; zmienia się po każdym przeliczeniu raportu) |
| Konto dla jury | e-mail i hasło podane w zgłoszeniu (HackTribe) |

To środowisko testowe (pasek u góry każdej strony), nie serwis dane.gov.pl.

## Kroki dla jury (ok. 5 minut)

1. Zaloguj się do panelu. Wejdź w **Dane → Resources**.
2. Otwórz „Wykaz AED – Urząd Miasta Legionowo”. Pod polem DGA „Contains protected data list”
   jest nasze pole **„Contains AED list: Tak”** z opisem mechanizmu.
3. Otwórz „Wykaz AED – Fundacja Przykładowa (dane testowe)”: 4 urządzenia, w tym 3 z celowymi błędami.
4. Na liście zasobów wybierz dowolny wiersz, z menu akcji wybierz
   **„Utwórz teraz zbiorczy wykaz defibrylatorów AED”** i kliknij „Wykonaj”.
   Komunikat pokaże: ile AED od ilu dostawców, ile wierszy odrzucono u każdego dostawcy.
5. Wejdź w **Dane → Datasets → „Wykaz defibrylatorów AED – raport zbiorczy”** (instytucja: Ministerstwo Cyfryzacji).
   Zasób „Wykaz defibrylatorów AED” ma plik CSV, widok tabeli i mapę.
6. Otwórz w przeglądarce API `/1.4/resources/ID/geo` (ID zasobu z kroku 5) – punkty mapy z raportu zbiorczego.
7. (Opcjonalnie) Dodaj zasób z plikiem `demo_aed/dane/wykaz_aed_testowy_z_bledami.csv`
   i zaznacz „Contains AED list: Tak” – formularz nie zapisze pliku i wypisze błędy w wierszach.

## Gdzie sprawdzić każde wymaganie z treści zadania

| Wymaganie (pkt 4 i 5 treści) | Gdzie | Jak sprawdzić |
|---|---|---|
| Integracja informacji od wielu dysponentów w jednym zbiorze | `mcod/resources/aed_utils.py`, `aed_validation.py` (`build_main_aed_df`) | krok 4–5 |
| Zgodność z zasadami działania dane.gov.pl | zmiany w kodzie portalu: `git diff f90a02f` (pierwszy commit = czysty kod portalu) | pole w panelu (krok 2), raport jako zwykły zasób portalu, mapa portalu |
| Wzorcowy zakres danych (xlsx) | `wzorcowy_zakres_AED.xlsx` w zgłoszeniu; kolumny w `mcod/resources/aed_constants.py` | plik xlsx |
| Format odczytywalny maszynowo | raport zbiorczy: CSV UTF-8, API JSON | krok 5–6 |
| Kod źródłowy | to repozytorium | `git log` |
| Prototyp | panel pod adresem wyżej | kroki 1–7 |

## Dane

Wykazy 4 instytucji z otwartych zbiorów (Legionowo, Krosno, Przemyśl: CC0 1.0; Warszawa: CC BY 4.0),
przepisane na wzorcowy zakres danych, oraz jeden wykaz testowy z celowymi błędami (nie jest to prawdziwa instytucja).

## Ograniczenia

- Strona publiczna portalu (frontend Angular) nie jest uruchomiona; mapę raportu pokazuje API i panel.
- Wyszukiwarka API (`/datasets/ID/resources`) w demo zwraca błąd indeksu Elasticsearch; szczegóły zbioru i zasobu działają.
- Raport zbiorczy powstaje w zadaniu Celery o 05:00; w demo jury uruchamia go akcją w panelu.
- Dane demo to 5 dostawców; w Polsce wykazy AED publikuje dziś kilkanaście miast, w różnych formatach.
- Godziny dostępności w danych miast są nieustrukturyzowane; w wykazach demo wpisaliśmy „24h” tylko tam,
  gdzie źródło podaje dostęp całodobowy, w pozostałych „X”.

## Uruchomienie u siebie

`demo_aed/README.md` (Docker Compose, porty tylko na 127.0.0.1).
