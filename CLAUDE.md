# CLAUDE.md — Misja AED, repo `dane-gov-aed`

Kod backendu dane.gov.pl 2.63.0 z dopisanym modułem „Wykaz AED” (HackNation 21–22.11.2026, zadanie Ministerstwa Cyfryzacji). Pierwszy commit to kod portalu bez zmian; nasze zmiany są w kolejnych commitach. Instrukcja dla jury: `DLA_JURY.md`. Zgłoszenie w HackTribe do niedzieli 11:00 wysyła tylko Paweł.

## Trzy repozytoria, sprawdzaj wszystkie

| Repo | Ścieżka | Co tam jest |
|---|---|---|
| `HackNation_winners` | `C:\Users\pawel\hacknation` | **wiedza i stan, czytaj najpierw:** `AED_WNIOSKI.md` (sekcja STAN na górze), `AED_PLAN_FINAL.md`, `AED_KAMPANIA_PLAYBOOK.md`, treść zadania w `HackNation2026_materialy/`, dane w `aed_dane/` |
| `nie-chowaj-serca` | `C:\Users\pawel\nie-chowaj-serca` | narzędzie dostawcy, **wzorzec XLSX** w `dane/` (lista kolumn musi się zgadzać z `mcod/resources/aed_constants.py`), kampania, strona zasięgu `zasieg/` |
| `dane-gov-aed` (to) | `C:\Users\pawel\dane-gov-aed` | moduł AED w `mcod/resources/aed_*`; **brak remote'a na GitHubie** |

Kampania (decyzja Pawła 22.11): nazwa **„Podziel się życiem”**, hasło **„Nie mów nam, gdzie jest AED. Powiedz wszystkim.”**

## Zasady
- Serwery lokalnie tylko na 127.0.0.1. Żadnych sekretów ani haseł w repo (konto jury tylko w HackTribe).
- Nie przebudowujemy mechaniki portalu; dopisujemy moduł na wzór Main DGA.
- Po ważnej zmianie dopisz linijkę w sekcji STAN w `C:\Users\pawel\hacknation\AED_WNIOSKI.md`.
