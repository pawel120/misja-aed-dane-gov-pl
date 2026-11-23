"""
Konwerter wykazu AED: plik w dowolnym układzie kolumn -> wzorcowy zakres danych.

Treść zadania mówi: „zbierz dane z wielu rozproszonych źródeł”. Dane o AED
już istnieją, ale każde miasto publikuje je inaczej: inne nazwy kolumn, adres
w jednej komórce, zamienione współrzędne, cały wiersz ujęty w cudzysłów.
Konwerter przenosi taki plik do wzorca, a każdą zmianę zapisuje, żeby dostawca
widział, co portal poprawił, a czego nie zgadywał.

Czego konwerter nie robi: nie zgaduje danych, których w źródle nie ma
(REGON, godziny, daty przeglądów). Wpisuje „X” i wymienia te kolumny wprost.
Nie geokoduje adresów: punkt bez współrzędnych zostanie odrzucony przez
walidację, bo zła pozycja AED na mapie jest gorsza niż jej brak.

Moduł nie zależy od Django: działa na samym pandas, jak ``aed_validation.py``.
"""

import csv
import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from mcod.resources.aed_constants import (
    AED_COLUMNS,
    AED_DATE_COLUMNS,
    AED_EMPTY_VALUE,
    AED_POLAND_LATITUDE,
    AED_POLAND_LONGITUDE,
    AED_REQUIRED_VALUE_COLUMNS,
    AED_WEEKDAY_COLUMNS,
    AED_YES_NO_COLUMNS,
)

# Kolumny, które nie mają jednego odpowiednika we wzorcu i są rozbijane osobno.
_ADDRESS = "__adres__"
_COORDINATES = "__wspolrzedne__"
_HOURS = "__godziny__"


def header_key(header: str) -> str:
    """„Szerokość geograficzna ” -> „szerokosc_geograficzna”."""
    text = str(header).strip().lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


# Nagłówki spotykane w wykazach AED miast na dane.gov.pl i w eksportach z map.
# Klucze są po ``header_key``. Celowo bez „x” i „y”: w układzie PL-1992 „x” to
# kierunek północny, więc takie kolumny łatwo pomylić.
HEADER_SYNONYMS: Dict[str, str] = {
    **{column: column for column in AED_COLUMNS},
    # współrzędne
    "szerokosc": "szerokosc_geograficzna",
    "szer_geogr": "szerokosc_geograficzna",
    "lat": "szerokosc_geograficzna",
    "latitude": "szerokosc_geograficzna",
    "dlugosc": "dlugosc_geograficzna",
    "dl_geogr": "dlugosc_geograficzna",
    "lon": "dlugosc_geograficzna",
    "lng": "dlugosc_geograficzna",
    "long": "dlugosc_geograficzna",
    "longitude": "dlugosc_geograficzna",
    "wspolrzedne": _COORDINATES,
    "wspolrzedne_geograficzne": _COORDINATES,
    "geolokalizacja": _COORDINATES,
    "coordinates": _COORDINATES,
    # miejsce i adres
    "nazwa": "nazwa_miejsca",
    "nazwa_obiektu": "nazwa_miejsca",
    "obiekt": "nazwa_miejsca",
    "lokalizacja": "nazwa_miejsca",
    "miejsce": "nazwa_miejsca",
    "nazwa_lokalizacji": "nazwa_miejsca",
    "adres": _ADDRESS,
    "adres_obiektu": _ADDRESS,
    "ulica": "nazwa_ulicy",
    "numer": "nr_budynku",
    "nr": "nr_budynku",
    "numer_budynku": "nr_budynku",
    "nr_domu": "nr_budynku",
    "numer_lokalu": "nr_lokalu",
    "kod": "kod_pocztowy",
    "miasto": "miejscowosc",
    "miejscowosc": "miejscowosc",
    "opis": "opis_lokalizacji",
    "opis_miejsca": "opis_lokalizacji",
    "dokladna_lokalizacja": "opis_lokalizacji",
    "umiejscowienie": "opis_lokalizacji",
    "gdzie": "opis_lokalizacji",
    "polozenie_urzadzenia": "polozenie",
    "umieszczenie": "polozenie",
    "wewnatrz_zewnatrz": "polozenie",
    # identyfikator i dysponent
    "id": "id_urzadzenia",
    "numer_id": "id_urzadzenia",
    "identyfikator": "id_urzadzenia",
    "id_aed": "id_urzadzenia",
    "nr_aed": "id_urzadzenia",
    "regon": "regon_dysponenta",
    "dysponent": "nazwa_dysponenta",
    "wlasciciel": "nazwa_dysponenta",
    "podmiot": "nazwa_dysponenta",
    "instytucja": "nazwa_dysponenta",
    # dostępność
    "calodobowy": "dostep_24h",
    "czynny_24h": "dostep_24h",
    "dostepnosc_24h": "dostep_24h",
    "24h": "dostep_24h",
    "dostepny_publicznie": "dostep_publiczny",
    "ogolnodostepny": "dostep_publiczny",
    "publiczny": "dostep_publiczny",
    "zamkniety": "urzadzenie_zamkniete",
    "w_szafce_zamknietej": "urzadzenie_zamkniete",
    "godziny": _HOURS,
    "godziny_dostepnosci": _HOURS,
    "godziny_otwarcia": _HOURS,
    "dostepnosc": _HOURS,
    # urządzenie
    "model": "model_urzadzenia",
    "typ": "model_urzadzenia",
    "typ_urzadzenia": "model_urzadzenia",
    "przeglad": "data_ostatniego_przegladu",
    "data_przegladu": "data_ostatniego_przegladu",
    "elektrody": "data_waznosci_elektrod",
    "waznosc_elektrod": "data_waznosci_elektrod",
    "bateria": "data_waznosci_baterii",
    "waznosc_baterii": "data_waznosci_baterii",
    "telefon": "telefon_kontaktowy",
    "tel": "telefon_kontaktowy",
    "kontakt": "telefon_kontaktowy",
    "aktualizacja": "data_aktualizacji",
}

_ADDRESS_RE = re.compile(
    r"^\s*(?:(?P<cecha>ul|al|pl|os)\.*\s*)?(?P<ulica>.+?)(?:\s+(?P<nr>\d+[A-Za-z]?(?:/\d+[A-Za-z]?)?))?"
    r"\s*,\s*(?P<kod>\d{2}-\d{3})\s+(?P<miejscowosc>.+?)\s*$",
    re.IGNORECASE,
)
_STREET_TYPES = {"ul": "ulica", "al": "aleja", "pl": "plac", "os": "osiedle"}
_DATE_DMY_RE = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$")
_DATE_YMD_DOTS_RE = re.compile(r"^(\d{4})[./](\d{1,2})[./](\d{1,2})$")
_PAIR_RE = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*[,; ]\s*(-?\d+(?:[.,]\d+)?)\s*$")
# Porównywane po ``header_key``, więc „24/7” to „24_7”, a „Całodobowo” to „calodobowo”.
_FULL_DAY_RE = re.compile(r"^(24h|24_h|24_7|calodobowo|calodobowy|cala_doba|00_00_24_00|0_24)$")

# Opis kolumn specjalnych do pokazania dostawcy.
SPECIAL_TARGET_LABELS: Dict[str, str] = {
    _ADDRESS: "adres → ulica, numer, kod pocztowy, miejscowość",
    _COORDINATES: "współrzędne w jednej kolumnie → szerokość i długość",
    _HOURS: "godziny → dni tygodnia (gdy całodobowo) albo opis lokalizacji",
}

_YES = {"tak", "t", "yes", "y", "true", "1", "prawda"}
_NO = {"nie", "n", "no", "false", "0", "falsz"}
_INSIDE = {"wewnatrz", "w_budynku", "wewnetrzny", "wewnatrz_budynku"}
_OUTSIDE = {"na_zewnatrz", "zewnatrz", "zewnetrzny", "na_elewacji", "na_zewnatrz_budynku"}


@dataclass
class AEDConversion:
    """Plik we wzorcu i opis tego, co konwerter zrobił."""

    df: pd.DataFrame
    mapping: Dict[str, str] = field(default_factory=dict)  # nagłówek źródła -> kolumna wzorca
    unmapped: List[str] = field(default_factory=list)  # kolumny źródła pominięte
    changes: List[str] = field(default_factory=list)  # zmiany po polsku, do pokazania dostawcy
    missing: List[str] = field(default_factory=list)  # kolumny wzorca bez danych w źródle

    def to_csv_bytes(self) -> bytes:
        return self.df.to_csv(index=False).encode("utf-8")


def _text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def unwrap_quoted_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
    """
    Plik, w którym każdy wiersz jest w całości w cudzysłowie (np. wykaz AED z Marek),
    czyta się jako jedną kolumnę. Rozdzielamy go jeszcze raz.
    """
    if len(df.columns) != 1:
        return df, False
    header = str(df.columns[0])
    delimiter = ";" if header.count(";") > header.count(",") else ","
    if delimiter not in header:
        return df, False
    lines = [header] + [_text(value) for value in df.iloc[:, 0]]
    rows = list(csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter, skipinitialspace=True))
    width = len(rows[0])
    body = [(row + [""] * width)[:width] for row in rows[1:] if any(cell.strip() for cell in row)]
    return pd.DataFrame(body, columns=[cell.strip() for cell in rows[0]], dtype=object), True


def _choose_sources(df: pd.DataFrame) -> Tuple[Dict[str, str], List[str]]:
    """
    Kolumna wzorca -> kolumna źródła. Gdy pasuje kilka (np. „Nazwa” i „Lokalizacja”),
    wygrywa ta z największą liczbą różnych wartości: w Krośnie „Nazwa” to zawsze
    „Defibrylator”, a nazwa miejsca jest w „Lokalizacji”.
    """
    candidates: Dict[str, List[str]] = {}
    unmapped: List[str] = []
    for column in df.columns:
        target = HEADER_SYNONYMS.get(header_key(column))
        if target:
            candidates.setdefault(target, []).append(column)
        elif str(column).strip():
            unmapped.append(str(column).strip())
    chosen: Dict[str, str] = {}
    for target, sources in candidates.items():
        best = max(sources, key=lambda column: df[column].map(_text).nunique())
        chosen[target] = best
        unmapped.extend(str(source).strip() for source in sources if source != best)
    return chosen, unmapped


def _number(value: str) -> Optional[float]:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _in(value: Optional[float], bounds: Tuple[float, float]) -> bool:
    return value is not None and bounds[0] <= value <= bounds[1]


def _split_address(value: str) -> Optional[Dict[str, str]]:
    match = _ADDRESS_RE.match(value)
    if not match:
        return None
    street_type = (match.group("cecha") or "").lower()
    return {
        "cecha_ulicy": _STREET_TYPES.get(street_type, ""),
        "nazwa_ulicy": match.group("ulica").strip(" .,"),
        "nr_budynku": match.group("nr") or "",
        "kod_pocztowy": match.group("kod"),
        "miejscowosc": match.group("miejscowosc").strip(),
    }


def _fix_date(value: str) -> str:
    match = _DATE_DMY_RE.match(value)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = _DATE_YMD_DOTS_RE.match(value)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return value


def _yes_no(value: str) -> str:
    key = header_key(value)
    if key in _YES:
        return "TAK"
    if key in _NO:
        return "NIE"
    return value


def _location(value: str) -> str:
    key = header_key(value)
    if key in _INSIDE:
        return "wewnątrz"
    if key in _OUTSIDE:
        return "na zewnątrz"
    return value


def convert_to_aed(df: pd.DataFrame) -> AEDConversion:
    """Przenosi tabelę o dowolnym układzie kolumn do wzorcowego zakresu danych AED."""
    changes: List[str] = []
    df, unwrapped = unwrap_quoted_rows(df)
    if unwrapped:
        changes.append("Rozdzielono wiersze, które były w całości ujęte w cudzysłów")
    df = df.astype(object).where(pd.notna(df), "")
    sources, unmapped = _choose_sources(df)

    out = pd.DataFrame({column: [""] * len(df) for column in AED_COLUMNS}, dtype=object)
    for target, source in sources.items():
        if target in AED_COLUMNS:
            out[target] = df[source].map(_text).values

    counts: Counter = Counter()

    if _COORDINATES in sources:
        for position, value in enumerate(df[sources[_COORDINATES]].map(_text)):
            match = _PAIR_RE.match(value)
            if match and not out.at[position, "szerokosc_geograficzna"]:
                out.at[position, "szerokosc_geograficzna"], out.at[position, "dlugosc_geograficzna"] = match.groups()
                counts["pair"] += 1
        if counts["pair"]:
            changes.append(f"Rozdzielono współrzędne zapisane w jednej kolumnie ({counts['pair']})")

    if _ADDRESS in sources:
        for position, value in enumerate(df[sources[_ADDRESS]].map(_text)):
            if not value:
                continue
            parts = _split_address(value)
            if parts is None:
                counts["address_unknown"] += 1
                if not out.at[position, "opis_lokalizacji"]:
                    out.at[position, "opis_lokalizacji"] = value
                continue
            for column, part in parts.items():
                if part and not out.at[position, column]:
                    out.at[position, column] = part
            counts["address"] += 1
        if counts["address"]:
            changes.append(f"Rozbito adres na ulicę, numer, kod pocztowy i miejscowość ({counts['address']})")
        if counts["address_unknown"]:
            changes.append(
                f"Nie rozpoznano adresu w {counts['address_unknown']} wierszach; adres trafił do „opis_lokalizacji”"
            )

    if _HOURS in sources:
        for position, value in enumerate(df[sources[_HOURS]].map(_text)):
            if not value:
                continue
            if _FULL_DAY_RE.match(header_key(value)):
                for column in AED_WEEKDAY_COLUMNS:
                    out.at[position, column] = "24h"
                if not out.at[position, "dostep_24h"]:
                    out.at[position, "dostep_24h"] = "TAK"
                counts["hours_24"] += 1
            else:
                note = f"godziny: {value}"
                current = out.at[position, "opis_lokalizacji"]
                out.at[position, "opis_lokalizacji"] = f"{current}; {note}" if current else note
                counts["hours_text"] += 1
        if counts["hours_24"]:
            changes.append(f"Dostęp całodobowy rozpisano na dni tygodnia ({counts['hours_24']})")
        if counts["hours_text"]:
            changes.append(
                f"Godzin zapisanych tekstem nie rozpisano na dni ({counts['hours_text']}); "
                "przeniesiono je do „opis_lokalizacji”, dni tygodnia uzupełnia dysponent"
            )

    for column in ("szerokosc_geograficzna", "dlugosc_geograficzna"):
        commas = out[column].str.contains(",", regex=False)
        if commas.any():
            out.loc[commas, column] = out.loc[commas, column].str.replace(",", ".", regex=False)
            counts["comma"] += int(commas.sum())
    if counts["comma"]:
        changes.append(f"Zamieniono przecinek na kropkę we współrzędnych ({counts['comma']})")

    swapped = correct = 0
    for lat_text, lon_text in zip(out["szerokosc_geograficzna"], out["dlugosc_geograficzna"]):
        lat, lon = _number(lat_text), _number(lon_text)
        if _in(lat, AED_POLAND_LONGITUDE) and _in(lon, AED_POLAND_LATITUDE):
            swapped += 1
        elif _in(lat, AED_POLAND_LATITUDE) and _in(lon, AED_POLAND_LONGITUDE):
            correct += 1
    if swapped > correct:
        out["szerokosc_geograficzna"], out["dlugosc_geograficzna"] = (
            out["dlugosc_geograficzna"].copy(),
            out["szerokosc_geograficzna"].copy(),
        )
        changes.append("Zamieniono miejscami szerokość i długość geograficzną (były w odwrotnych kolumnach)")

    for column in AED_DATE_COLUMNS:
        fixed = out[column].map(_fix_date)
        counts["date"] += int((fixed != out[column]).sum())
        out[column] = fixed
    if counts["date"]:
        changes.append(f"Ujednolicono daty do rrrr-mm-dd ({counts['date']})")

    for column in AED_YES_NO_COLUMNS:
        out[column] = out[column].map(lambda value: _yes_no(value) if value else value)
    out["polozenie"] = out["polozenie"].map(lambda value: _location(value) if value else value)

    if not out["id_urzadzenia"].map(bool).any() and len(out):
        out["id_urzadzenia"] = [f"AED-{number:04d}" for number in range(1, len(out) + 1)]
        changes.append("Plik nie miał identyfikatorów urządzeń; nadano kolejne numery AED-0001, AED-0002…")

    missing: List[str] = []
    for column in AED_COLUMNS:
        empty = out[column] == ""
        if empty.all():
            missing.append(column)
        out.loc[empty, column] = AED_EMPTY_VALUE
    required_missing = [column for column in missing if column in AED_REQUIRED_VALUE_COLUMNS]
    if required_missing:
        changes.append(
            "Brak danych, bez których punktu nie da się pokazać na mapie: " + ", ".join(required_missing)
        )
    optional_missing = [column for column in missing if column not in AED_REQUIRED_VALUE_COLUMNS]
    if optional_missing:
        changes.append(
            "Kolumny wzorca, których nie ma w źródle (wpisano „X”, uzupełnia dysponent): "
            + ", ".join(optional_missing)
        )
    if unmapped:
        changes.append("Pominięto kolumny spoza wzorca: " + ", ".join(unmapped))

    mapping = {str(source).strip(): target for target, source in sources.items()}
    return AEDConversion(df=out, mapping=mapping, unmapped=unmapped, changes=changes, missing=missing)
