"""
Generuje wzorcowy zakres danych o AED (xlsx i csv) oraz opis kolumn
z tej samej listy kolumn, której używa portal (mcod/resources/aed_constants.py).

Uruchomienie: python wzorzec/generuj_wzorzec.py
Plik wzorca ma jeden arkusz, jeden wiersz nagłówka i dwa przykładowe wiersze
(zasady przygotowania danych dane.gov.pl). Puste wartości: „X”.
"""

import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent))
from mcod.resources.aed_constants import (  # noqa: E402
    AED_COLUMNS,
    AED_REQUIRED_VALUE_COLUMNS,
)

DZIEN = {"pn": "poniedziałek", "wt": "wtorek", "sr": "środa", "cz": "czwartek", "pt": "piątek", "so": "sobota", "nd": "niedziela"}

OPIS = {
    "id_urzadzenia": ("tekst", "Identyfikator urządzenia nadany przez dysponenta, unikalny w jego wykazie"),
    "regon_dysponenta": ("tekst (9 lub 14 cyfr)", "REGON podmiotu, u którego wisi urządzenie, jeśli inny niż dostawca danych; inaczej X"),
    "nazwa_dysponenta": ("tekst", "Nazwa podmiotu, który odpowiada za urządzenie"),
    "nazwa_miejsca": ("tekst", "Nazwa obiektu, w którym jest AED; etykieta punktu na mapie portalu"),
    "cecha_ulicy": ("tekst", "ulica, aleja, plac, osiedle albo X"),
    "nazwa_ulicy": ("tekst", "Nazwa ulicy bez cechy"),
    "nr_budynku": ("tekst", "Numer budynku (także z literą lub ułamkiem, np. 2A, 25/27)"),
    "nr_lokalu": ("tekst", "Numer lokalu albo X"),
    "kod_pocztowy": ("tekst 00-000", "Kod pocztowy"),
    "miejscowosc": ("tekst", "Miejscowość"),
    "kod_terc": ("tekst (7 cyfr)", "Kod gminy z rejestru TERYT (TERC) albo X"),
    "kod_simc": ("tekst (7 cyfr)", "Identyfikator miejscowości z rejestru TERYT (SIMC) albo X"),
    "szerokosc_geograficzna": ("liczba", "WGS84, stopnie dziesiętne z kropką, np. 52.3170; kolumna mapy portalu"),
    "dlugosc_geograficzna": ("liczba", "WGS84, stopnie dziesiętne z kropką, np. 21.1041; kolumna mapy portalu"),
    "polozenie": ("wewnątrz / na zewnątrz / X", "Czy AED jest w budynku, czy na zewnątrz (np. w szafce na elewacji)"),
    "opis_lokalizacji": ("tekst", "Jak dojść: piętro, wejście, gablota"),
    "dostep_24h": ("TAK / NIE / X", "Czy urządzenie jest dostępne całą dobę"),
    "dostep_publiczny": ("TAK / NIE / X", "Czy może z niego skorzystać osoba z zewnątrz"),
    "urzadzenie_zamkniete": ("TAK / NIE / X", "Czy AED jest zamknięty na klucz lub w zamykanym pomieszczeniu"),
    "model_urzadzenia": ("tekst", "Producent i model albo X"),
    "data_ostatniego_przegladu": ("data rrrr-mm-dd", "Data ostatniego przeglądu albo X"),
    "data_waznosci_elektrod": ("data rrrr-mm-dd", "Termin ważności elektrod albo X; portal ostrzega 90 dni wcześniej"),
    "data_waznosci_baterii": ("data rrrr-mm-dd", "Termin ważności baterii albo X; portal ostrzega 90 dni wcześniej"),
    "telefon_kontaktowy": ("tekst", "Telefon do opiekuna urządzenia (służbowy) albo X"),
    "data_aktualizacji": ("data rrrr-mm-dd", "Data ostatniej aktualizacji rekordu"),
}
for skrot, nazwa in DZIEN.items():
    OPIS[f"godziny_{skrot}"] = (
        "HH:MM-HH:MM / 24h / nieczynne / X",
        f"Godziny dostępu – {nazwa}; kilka przedziałów po przecinku, np. 08:00-12:00, 13:00-16:00",
    )

PRZYKLADY = [
    {
        "id_urzadzenia": "AED-001", "regon_dysponenta": "X", "nazwa_dysponenta": "Dostawca XYZ (przykład)",
        "nazwa_miejsca": "Szkoła Podstawowa nr 2", "cecha_ulicy": "ulica", "nazwa_ulicy": "Szkolna", "nr_budynku": "9",
        "nr_lokalu": "X", "kod_pocztowy": "00-001", "miejscowosc": "Przykładowo", "kod_terc": "X", "kod_simc": "X",
        "szerokosc_geograficzna": 52.2297, "dlugosc_geograficzna": 21.0122, "polozenie": "wewnątrz",
        "opis_lokalizacji": "Parter, przy portierni", "dostep_24h": "NIE", "godziny_pn": "07:00-17:00",
        "godziny_wt": "07:00-17:00", "godziny_sr": "07:00-17:00", "godziny_cz": "07:00-17:00", "godziny_pt": "07:00-15:00",
        "godziny_so": "nieczynne", "godziny_nd": "nieczynne", "dostep_publiczny": "TAK", "urzadzenie_zamkniete": "NIE",
        "model_urzadzenia": "X", "data_ostatniego_przegladu": "2026-05-10", "data_waznosci_elektrod": "2027-03-31",
        "data_waznosci_baterii": "2029-01-31", "telefon_kontaktowy": "X", "data_aktualizacji": "2026-11-22",
    },
    {
        "id_urzadzenia": "AED-002", "regon_dysponenta": "X", "nazwa_dysponenta": "Dostawca XYZ (przykład)",
        "nazwa_miejsca": "Rynek, szafka przy ratuszu", "cecha_ulicy": "plac", "nazwa_ulicy": "Rynek", "nr_budynku": "1",
        "nr_lokalu": "X", "kod_pocztowy": "00-001", "miejscowosc": "Przykładowo", "kod_terc": "X", "kod_simc": "X",
        "szerokosc_geograficzna": 52.2310, "dlugosc_geograficzna": 21.0150, "polozenie": "na zewnątrz",
        "opis_lokalizacji": "Szafka na ścianie ratusza od strony rynku", "dostep_24h": "TAK",
        **{f"godziny_{d}": "24h" for d in DZIEN}, "dostep_publiczny": "TAK", "urzadzenie_zamkniete": "NIE",
        "model_urzadzenia": "X", "data_ostatniego_przegladu": "X", "data_waznosci_elektrod": "X",
        "data_waznosci_baterii": "X", "telefon_kontaktowy": "X", "data_aktualizacji": "2026-11-22",
    },
]


def zapisz_xlsx(sciezka, naglowek, wiersze, arkusz):
    wb = Workbook()
    ws = wb.active
    ws.title = arkusz
    ws.append(naglowek)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for wiersz in wiersze:
        ws.append(wiersz)
    ws.freeze_panes = "A2"
    wb.save(sciezka)


def zapisz_csv(sciezka, naglowek, wiersze):
    with open(sciezka, "w", encoding="utf-8", newline="") as plik:
        writer = csv.writer(plik)
        writer.writerow(naglowek)
        writer.writerows(wiersze)


def main():
    assert set(OPIS) == set(AED_COLUMNS), set(AED_COLUMNS) ^ set(OPIS)
    wiersze = [[p[k] for k in AED_COLUMNS] for p in PRZYKLADY]
    zapisz_xlsx(KATALOG / "WYKAZ_AED_-_dostawca_XYZ.xlsx", AED_COLUMNS, wiersze, "WYKAZ_AED")
    zapisz_csv(KATALOG / "WYKAZ_AED_-_dostawca_XYZ.csv", AED_COLUMNS, wiersze)

    naglowek = ["kolumna", "typ_i_format", "wymagana_wartosc", "opis", "przyklad"]
    opis = [
        [k, OPIS[k][0], "TAK" if k in AED_REQUIRED_VALUE_COLUMNS else "NIE (X, gdy brak)", OPIS[k][1], str(PRZYKLADY[0][k])]
        for k in AED_COLUMNS
    ]
    zapisz_xlsx(KATALOG / "opis_kolumn_wykazu_AED.xlsx", naglowek, opis, "opis_kolumn")
    zapisz_csv(KATALOG / "opis_kolumn_wykazu_AED.csv", naglowek, opis)
    print(f"Kolumn: {len(AED_COLUMNS)}, przykładowych wierszy: {len(wiersze)}")


if __name__ == "__main__":
    main()
