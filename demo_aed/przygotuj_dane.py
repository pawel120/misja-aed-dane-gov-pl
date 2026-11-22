"""
Dzieli zbiór AED (aed_polska.csv) na osobne wykazy dostawców w aktualnym
wzorcu (godziny w 7 kolumnach, położenie) i dokłada jeden wykaz testowy z błędami.

Uruchomienie: python demo_aed/przygotuj_dane.py ŚCIEŻKA_DO/aed_polska.csv
Do demo bierzemy tylko dostawców z otwartą licencją (CC0, CC BY).
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcod.resources.aed_constants import AED_COLUMNS, AED_WEEKDAY_COLUMNS  # noqa: E402

DOSTAWCY = {
    "000524832": "legionowo",
    "000526989": "krosno",
    "650900341": "przemysl",
    "015259640": "warszawa",
}
WYJSCIE = Path(__file__).parent / "dane"


def zapisz(sciezka, wiersze):
    with open(sciezka, "w", encoding="utf-8", newline="") as plik:
        writer = csv.DictWriter(plik, fieldnames=AED_COLUMNS)
        writer.writeheader()
        writer.writerows(wiersze)


def main(zrodlo):
    with open(zrodlo, encoding="utf-8-sig") as plik:
        rekordy = list(csv.DictReader(plik))
    for regon, nazwa in DOSTAWCY.items():
        wiersze = []
        for rekord in (r for r in rekordy if r["regon_dostawcy_danych"] == regon):
            wiersz = {kolumna: rekord.get(kolumna, "X") or "X" for kolumna in AED_COLUMNS}
            for dzien in AED_WEEKDAY_COLUMNS:
                wiersz[dzien] = "24h" if rekord.get("dostep_24h") == "TAK" else "X"
            wiersz["polozenie"] = "X"
            wiersze.append(wiersz)
        zapisz(WYJSCIE / f"wykaz_aed_{nazwa}.csv", wiersze)
        print(nazwa, len(wiersze))

    # Wykaz testowy (nie prawdziwej instytucji) z typowymi błędami do pokazania walidacji.
    baza = {kolumna: "X" for kolumna in AED_COLUMNS}
    baza.update(nazwa_dysponenta="Fundacja Przykładowa (dane testowe)", miejscowosc="Bydgoszcz", dostep_24h="NIE",
                dostep_publiczny="TAK", polozenie="wewnątrz", godziny_pn="08:00-16:00")
    testowe = [
        dict(baza, id_urzadzenia="T-1", nazwa_miejsca="Hala targowa", szerokosc_geograficzna="53.1385",
             dlugosc_geograficzna="18.0566", data_waznosci_elektrod="2026-12-15"),
        dict(baza, id_urzadzenia="T-2", nazwa_miejsca="Dworzec", szerokosc_geograficzna="18.0040",
             dlugosc_geograficzna="53.1350"),
        dict(baza, id_urzadzenia="T-3", nazwa_miejsca="Biblioteka", szerokosc_geograficzna="53.1230",
             dlugosc_geograficzna="18.0084", godziny_pn="pn-pt 8-16"),
        dict(baza, id_urzadzenia="T-4", nazwa_miejsca="Basen", szerokosc_geograficzna="53.1300",
             dlugosc_geograficzna="18.0200", dostep_24h="tak?"),
    ]
    zapisz(WYJSCIE / "wykaz_aed_testowy_z_bledami.csv", testowe)
    print("testowy", len(testowe))


if __name__ == "__main__":
    main(sys.argv[1])
