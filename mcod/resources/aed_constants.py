"""
Stałe wykazu defibrylatorów AED (Main AED).

Mechanizm działa na wzór wykazu chronionych danych DGA (``dga_constants.py``):
każda instytucja publikuje własny zasób oznaczony jako „aktualny wykaz AED”,
a portal raz na dobę skleja poprawne zasoby w jeden raport zbiorczy.

AED_COLUMNS opisuje wzorcowy zakres danych, który musi mieć zasób dostawcy.
MAIN_AED_COLUMNS opisuje strukturę raportu zbiorczego.
"""

from typing import Dict, List, Tuple

# Moduł celowo nie importuje modeli Django: walidację AED da się uruchomić
# i przetestować na samym pandas (``aed_validation.py``).

# Znak pustej komórki według wskazówek przygotowania danych dane.gov.pl.
AED_EMPTY_VALUE = "X"

AED_WEEKDAY_COLUMNS: List[str] = [
    "godziny_pn",
    "godziny_wt",
    "godziny_sr",
    "godziny_cz",
    "godziny_pt",
    "godziny_so",
    "godziny_nd",
]

# Wzorcowy zakres danych o AED (kolejność kolumn w pliku dostawcy).
AED_COLUMNS: List[str] = [
    "id_urzadzenia",
    "regon_dysponenta",
    "nazwa_dysponenta",
    "nazwa_miejsca",
    "cecha_ulicy",
    "nazwa_ulicy",
    "nr_budynku",
    "nr_lokalu",
    "kod_pocztowy",
    "miejscowosc",
    "kod_terc",
    "kod_simc",
    "szerokosc_geograficzna",
    "dlugosc_geograficzna",
    "polozenie",
    "opis_lokalizacji",
    "dostep_24h",
    *AED_WEEKDAY_COLUMNS,
    "dostep_publiczny",
    "urzadzenie_zamkniete",
    "model_urzadzenia",
    "data_ostatniego_przegladu",
    "data_waznosci_elektrod",
    "data_waznosci_baterii",
    "telefon_kontaktowy",
    "data_aktualizacji",
]

# Kolumny, w których „X” nie wystarcza: bez nich punktu nie da się znaleźć.
AED_REQUIRED_VALUE_COLUMNS: List[str] = [
    "id_urzadzenia",
    "nazwa_miejsca",
    "miejscowosc",
    "szerokosc_geograficzna",
    "dlugosc_geograficzna",
]

AED_YES_NO_COLUMNS: List[str] = ["dostep_24h", "dostep_publiczny", "urzadzenie_zamkniete"]
AED_YES_NO_VALUES: Tuple[str, str] = ("TAK", "NIE")

AED_DATE_COLUMNS: List[str] = [
    "data_ostatniego_przegladu",
    "data_waznosci_elektrod",
    "data_waznosci_baterii",
    "data_aktualizacji",
]

AED_LOCATION_VALUES: Tuple[str, str] = ("wewnątrz", "na zewnątrz")
AED_HOURS_SPECIAL_VALUES: Tuple[str, str] = ("24h", "nieczynne")

# Zasięg Polski w WGS84 z niewielkim marginesem.
AED_POLAND_LATITUDE: Tuple[float, float] = (48.9, 55.0)
AED_POLAND_LONGITUDE: Tuple[float, float] = (14.0, 24.2)

# Punkty bliżej niż ta odległość u różnych dostawców oznaczamy jako możliwy duplikat.
AED_DUPLICATE_DISTANCE_METERS: float = 15.0
# Elektrody lub bateria, których termin mija w tym horyzoncie, trafiają do ostrzeżeń.
AED_EXPIRY_WARNING_DAYS: int = 90

# W przeciwieństwie do DGA wykaz AED może prowadzić każda instytucja, która
# odpowiada za urządzenia: samorząd, administracja, firma, fundacja, OSP.
# Wartości odpowiadają Organization.INSTITUTION_TYPE_LOCAL, _STATE, _PRIVATE, _OTHER.
ALLOWED_AED_INSTITUTIONS: List[str] = ["local", "state", "private", "other"]

MAIN_AED_PROVIDER_COLUMN = "Nazwa dostawcy"
MAIN_AED_PROVIDER_REGON_COLUMN = "REGON dostawcy"
MAIN_AED_DUPLICATE_COLUMN = "Możliwy duplikat"
MAIN_AED_WARNINGS_COLUMN = "Ostrzeżenia walidacji"

MAIN_AED_COLUMNS: List[str] = [
    "Lp.",
    MAIN_AED_PROVIDER_COLUMN,
    MAIN_AED_PROVIDER_REGON_COLUMN,
    *AED_COLUMNS,
    MAIN_AED_DUPLICATE_COLUMN,
    MAIN_AED_WARNINGS_COLUMN,
]

AED_COLUMN_LABELS: Dict[str, str] = {
    "szerokosc_geograficzna": "szerokość geograficzna (WGS84)",
    "dlugosc_geograficzna": "długość geograficzna (WGS84)",
}
