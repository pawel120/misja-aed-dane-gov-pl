"""
Walidacje wykazu defibrylatorów AED i sklejanie wykazów w raport zbiorczy.

Wykaz DGA sprawdza tylko, czy zasób ma wymagane kolumny i niepuste wartości.
Dla AED to za mało: błędny punkt na mapie prowadzi ratownika w złe miejsce.
Dlatego każdy wiersz przechodzi własne walidacje AED:

* wymagane kolumny wzorca (zasób bez nich jest pomijany w całości),
* identyfikator, nazwa miejsca, miejscowość i współrzędne są wypełnione,
* współrzędne są liczbami WGS84 i leżą w Polsce; zamienione szerokość
  i długość są rozpoznawane i zgłaszane wprost,
* TAK/NIE, daty rrrr-mm-dd, kod pocztowy 00-000, godziny w dniach tygodnia,
  położenie (wewnątrz / na zewnątrz),
* identyfikator urządzenia jest unikalny w wykazie dostawcy,
* spójność: urządzenie „dostępne 24h” nie może mieć dnia „nieczynne”.

Wiersz z błędem nie trafia do raportu zbiorczego, a dostawca dostaje listę
powodów. Ostrzeżenia (np. elektrody tracące ważność w ciągu 90 dni, możliwy
duplikat u innego dostawcy) nie blokują wiersza.

Moduł nie zależy od Django: działa na samym pandas.
"""

import csv
import datetime
import io
import math
import re
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from mcod.resources.aed_constants import (
    AED_COLUMNS,
    AED_DATE_COLUMNS,
    AED_DUPLICATE_DISTANCE_METERS,
    AED_EMPTY_VALUE,
    AED_EXPIRY_WARNING_DAYS,
    AED_HOURS_SPECIAL_VALUES,
    AED_LOCATION_VALUES,
    AED_POLAND_LATITUDE,
    AED_POLAND_LONGITUDE,
    AED_REQUIRED_VALUE_COLUMNS,
    AED_RESIDENTS_RADIUS_METERS,
    AED_RESIDENTS_SQUARE_METERS,
    AED_WEEKDAY_COLUMNS,
    AED_YES_NO_COLUMNS,
    AED_YES_NO_VALUES,
    MAIN_AED_COLUMNS,
    MAIN_AED_DUPLICATE_COLUMN,
    MAIN_AED_PROVIDER_COLUMN,
    MAIN_AED_PROVIDER_REGON_COLUMN,
    MAIN_AED_WARNINGS_COLUMN,
)

POSTAL_CODE_RE = re.compile(r"^\d{2}-\d{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HOURS_RANGE_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-4]):[0-5]\d$")


class MainAEDColumnsError(Exception):
    """Nagłówki zasobu nie pozwalają sprawdzić wykazu AED (cały wykaz jest pomijany)."""


class MainAEDMissingRequiredColumnError(MainAEDColumnsError):
    """Zasób nie ma kolumn wzorcowego zakresu danych AED."""

    def __init__(self, column_names: Sequence[str]):
        self.column_names = list(column_names)
        super().__init__(f"Brak wymaganych kolumn: {', '.join(self.column_names)}")


class MainAEDDuplicatedColumnError(MainAEDColumnsError):
    """Ta sama kolumna występuje w nagłówku więcej niż raz (np. „ID_URZADZENIA” i „id_urzadzenia”)."""

    def __init__(self, column_names: Sequence[str]):
        self.column_names = list(column_names)
        super().__init__(f"Powtórzone kolumny: {', '.join(self.column_names)}")


@dataclass
class AEDRowIssue:
    row_number: int  # numer wiersza w pliku dostawcy (nagłówek to wiersz 1)
    device_id: str
    reasons: List[str]


@dataclass
class AEDValidationResult:
    accepted: pd.DataFrame
    rejected: List[AEDRowIssue] = field(default_factory=list)
    warnings: List[AEDRowIssue] = field(default_factory=list)

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    def summary(self) -> str:
        lines = [f"Przyjęte: {self.accepted_count}, odrzucone: {self.rejected_count}, z ostrzeżeniami: {len(self.warnings)}."]
        for issue in self.rejected:
            lines.append(f"Wiersz {issue.row_number} ({issue.device_id}): odrzucony – {'; '.join(issue.reasons)}")
        for issue in self.warnings:
            lines.append(f"Wiersz {issue.row_number} ({issue.device_id}): ostrzeżenie – {'; '.join(issue.reasons)}")
        return "\n".join(lines)


def _is_empty(value: str) -> bool:
    return value == "" or value.upper() == AED_EMPTY_VALUE


def _parse_coordinate(value: str) -> Optional[float]:
    # Mapa portalu czyta współrzędne przez float() (IndexedData._get_point),
    # więc przecinek dziesiętny dałby wiersz bez punktu na mapie.
    try:
        number = float(value)
    except ValueError:
        return None
    if math.isnan(number):
        return None
    return number


def _in_range(value: float, bounds: Tuple[float, float]) -> bool:
    return bounds[0] <= value <= bounds[1]


def _parse_date(value: str) -> Optional[datetime.date]:
    if not DATE_RE.match(value):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _valid_hours(value: str) -> bool:
    if value in AED_HOURS_SPECIAL_VALUES:
        return True
    ranges = [part.strip() for part in value.split(",")]
    return all(HOURS_RANGE_RE.match(part) for part in ranges)


def _excel_value_to_text(value: Any) -> str:
    """
    Komórka Excela jako tekst wzorca. Excel sam zamienia wpisane „2027-06-30”
    na datę; bez tej zamiany wiersz miałby „2027-06-30 00:00:00”.
    """
    if isinstance(value, (datetime.datetime, pd.Timestamp)):
        if value.time() == datetime.time(0, 0):
            return value.date().isoformat()
        return value.isoformat(sep=" ")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# Te same bajty co w ``mcod.resources.guess.file_encoding``: polskie litery,
# które w ISO-8859-2 i Windows-1250 mają różne kody (np. „ą”: 0xB1 i 0xB9).
ISO_8859_2_ONLY_BYTES = (b"\xb1", b"\xac", b"\xbc", b"\xa1", b"\xb6", b"\xa6")
CP1250_ONLY_BYTES = (b"\xb9", b"\xa5", b"\x9f", b"\x8f", b"\x8c", b"\x9c")


def _decode_csv(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    iso_count = sum(raw.count(byte) for byte in ISO_8859_2_ONLY_BYTES)
    cp_count = sum(raw.count(byte) for byte in CP1250_ONLY_BYTES)
    encodings = ("iso-8859-2", "cp1250") if iso_count > cp_count else ("cp1250", "iso-8859-2")
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Nie rozpoznano kodowania pliku CSV")


def read_aed_file(file: BinaryIO, extension: str) -> pd.DataFrame:
    """
    Czyta wykaz AED jako tekst (bez zgadywania typów), żeby nie zgubić zer
    wiodących w kodach TERYT i REGON ani nie zamienić „13” w „13.0”.
    """
    extension = extension.lower().lstrip(".")
    if extension in ("xls", "xlsx"):
        df = pd.read_excel(file, dtype=object, keep_default_na=False)
        return df.applymap(_excel_value_to_text)
    if extension == "csv":
        text = _decode_csv(file.read())
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;	").delimiter
        except csv.Error:
            delimiter = ","
        return pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, sep=delimiter)
    raise ValueError(f"Nieobsługiwany format pliku: {extension}")


def normalize_aed_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ujednolica nagłówki i wartości: tekst bez spacji na brzegach, puste jako „X”."""
    df = df.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]
    df = df.astype(object).where(pd.notna(df), "")
    for column in df.columns:
        df[column] = df[column].map(lambda value: str(value).strip())
        df[column] = df[column].map(lambda value: AED_EMPTY_VALUE if value == "" else value)
    for column in AED_YES_NO_COLUMNS:
        if column in df.columns:
            df[column] = df[column].str.upper()
    return df


def check_aed_columns(df: pd.DataFrame) -> None:
    duplicated = sorted(set(df.columns[df.columns.duplicated()]))
    if duplicated:
        raise MainAEDDuplicatedColumnError(duplicated)
    missing = [column for column in AED_COLUMNS if column not in df.columns]
    if missing:
        raise MainAEDMissingRequiredColumnError(missing)


def _validate_row(row: pd.Series, today: datetime.date) -> Tuple[List[str], List[str], Optional[Tuple[float, float]]]:
    errors: List[str] = []
    warnings: List[str] = []

    for column in AED_REQUIRED_VALUE_COLUMNS:
        if _is_empty(row[column]):
            errors.append(f"brak wartości w kolumnie {column}")

    point: Optional[Tuple[float, float]] = None
    lat_raw, lon_raw = row["szerokosc_geograficzna"], row["dlugosc_geograficzna"]
    if not _is_empty(lat_raw) and not _is_empty(lon_raw):
        lat, lon = _parse_coordinate(lat_raw), _parse_coordinate(lon_raw)
        if lat is None or lon is None:
            errors.append("współrzędne muszą być liczbami z kropką dziesiętną (stopnie WGS84, np. 52.2297)")
        elif _in_range(lat, AED_POLAND_LATITUDE) and _in_range(lon, AED_POLAND_LONGITUDE):
            point = (lat, lon)
        elif _in_range(lon, AED_POLAND_LATITUDE) and _in_range(lat, AED_POLAND_LONGITUDE):
            errors.append("zamienione współrzędne: szerokość i długość geograficzna są w odwrotnych kolumnach")
        else:
            errors.append(f"punkt ({lat}, {lon}) leży poza Polską")

    for column in AED_YES_NO_COLUMNS:
        value = row[column]
        if not _is_empty(value) and value not in AED_YES_NO_VALUES:
            errors.append(f"{column}: dozwolone TAK, NIE albo X, jest „{value}”")

    for column in AED_DATE_COLUMNS:
        value = row[column]
        if not _is_empty(value) and _parse_date(value) is None:
            errors.append(f"{column}: data w formacie rrrr-mm-dd, jest „{value}”")

    postal_code = row["kod_pocztowy"]
    if not _is_empty(postal_code) and not POSTAL_CODE_RE.match(postal_code):
        errors.append(f"kod_pocztowy: format 00-000, jest „{postal_code}”")

    location = row["polozenie"]
    if not _is_empty(location) and location not in AED_LOCATION_VALUES:
        errors.append(f"polozenie: dozwolone „wewnątrz”, „na zewnątrz” albo X, jest „{location}”")

    closed_days = []
    for column in AED_WEEKDAY_COLUMNS:
        value = row[column]
        if _is_empty(value):
            continue
        if not _valid_hours(value):
            errors.append(f"{column}: dozwolone HH:MM-HH:MM, 24h, nieczynne albo X, jest „{value}”")
        elif value == "nieczynne":
            closed_days.append(column)
    if row["dostep_24h"] == "TAK" and closed_days:
        errors.append(f"dostep_24h = TAK, ale {', '.join(closed_days)} = nieczynne")

    for column, label in (("data_waznosci_elektrod", "elektrody"), ("data_waznosci_baterii", "bateria")):
        expiry = _parse_date(row[column])
        if expiry is None:
            continue
        if expiry < today:
            warnings.append(f"{label}: termin ważności minął {expiry.isoformat()}")
        elif (expiry - today).days <= AED_EXPIRY_WARNING_DAYS:
            warnings.append(f"{label}: termin ważności mija {expiry.isoformat()}")

    return errors, warnings, point


def validate_aed_df(df: pd.DataFrame, today: Optional[datetime.date] = None) -> AEDValidationResult:
    """
    Sprawdza wykaz AED jednego dostawcy.

    Raises:
        MainAEDMissingRequiredColumnError: gdy brakuje kolumn wzorca.
    """
    today = today or datetime.date.today()
    df = df.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]
    check_aed_columns(df)
    df = normalize_aed_df(df[AED_COLUMNS])

    accepted_indexes: List[int] = []
    warnings_per_row: List[str] = []
    rejected: List[AEDRowIssue] = []
    warnings: List[AEDRowIssue] = []
    seen_ids = {}

    for position, (index, row) in enumerate(df.iterrows()):
        row_number = position + 2
        device_id = row["id_urzadzenia"]
        errors, row_warnings, _ = _validate_row(row, today)
        if not _is_empty(device_id):
            if device_id in seen_ids:
                errors.append(f"identyfikator {device_id} powtarza się (wiersz {seen_ids[device_id]})")
            else:
                seen_ids[device_id] = row_number
        if errors:
            rejected.append(AEDRowIssue(row_number, device_id, errors))
            continue
        accepted_indexes.append(index)
        warnings_per_row.append("; ".join(row_warnings) or AED_EMPTY_VALUE)
        if row_warnings:
            warnings.append(AEDRowIssue(row_number, device_id, row_warnings))

    accepted = df.loc[accepted_indexes].copy()
    for column in ("szerokosc_geograficzna", "dlugosc_geograficzna"):
        accepted[column] = accepted[column].map(float)
    accepted[MAIN_AED_WARNINGS_COLUMN] = warnings_per_row
    accepted = accepted.reset_index(drop=True)
    return AEDValidationResult(accepted=accepted, rejected=rejected, warnings=warnings)


def distance_meters(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Odległość po kuli ziemskiej (haversine) w metrach."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def mark_cross_provider_duplicates(main_df: pd.DataFrame, max_distance: float = AED_DUPLICATE_DISTANCE_METERS) -> pd.DataFrame:
    """
    Oznacza punkty, które leżą bliżej niż ``max_distance`` od punktu innego
    dostawcy. Rekord zostaje w raporcie: o tym, który jest właściwy, decydują
    dostawcy, a nie portal.
    """
    main_df = main_df.copy()
    main_df[MAIN_AED_DUPLICATE_COLUMN] = AED_EMPTY_VALUE
    if main_df.empty:
        return main_df
    # Siatka ok. 0,001° (ok. 70–110 m) ogranicza porównania do sąsiednich komórek.
    cells = {}
    points = list(
        zip(
            main_df.index,
            main_df["szerokosc_geograficzna"].astype(float),
            main_df["dlugosc_geograficzna"].astype(float),
            main_df[MAIN_AED_PROVIDER_COLUMN],
        )
    )
    for index, lat, lon, provider in points:
        cells.setdefault((int(lat * 1000), int(lon * 1000)), []).append((index, lat, lon, provider))

    for index, lat, lon, provider in points:
        cell = (int(lat * 1000), int(lon * 1000))
        matches = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other_index, other_lat, other_lon, other_provider in cells.get((cell[0] + dx, cell[1] + dy), []):
                    if other_index == index or other_provider == provider:
                        continue
                    if distance_meters((lat, lon), (other_lat, other_lon)) <= max_distance:
                        matches.append(f"{other_provider}: {main_df.at[other_index, 'id_urzadzenia']}")
        main_df.at[index, MAIN_AED_DUPLICATE_COLUMN] = "; ".join(sorted(matches)) or AED_EMPTY_VALUE
    return main_df


@dataclass
class AEDProviderList:
    provider_name: str
    provider_regon: str
    df: pd.DataFrame


@dataclass
class MainAEDResult:
    main_df: pd.DataFrame
    results: List[Tuple[str, Optional[AEDValidationResult], Optional[str]]]
    # Mieszkańcy w promieniu 200 m: per dostawca i łącznie (bez podwójnego liczenia).
    residents: Dict[str, int] = field(default_factory=dict)
    residents_total: Optional[int] = None

    def add_residents(self, grid: "PopulationGrid") -> None:
        for provider, result, _skip_reason in self.results:
            if result is not None:
                self.residents[provider] = grid.residents_for_aed_df(result.accepted)
        self.residents_total = grid.residents_for_aed_df(self.main_df)

    def summary(self) -> str:
        lines = [f"Raport zbiorczy: {len(self.main_df)} AED od {self.main_df[MAIN_AED_PROVIDER_COLUMN].nunique()} dostawców."]
        if self.residents_total is not None:
            lines[0] += (
                f" W promieniu {AED_RESIDENTS_RADIUS_METERS} m od tych AED mieszka "
                f"{format_residents(self.residents_total)} osób."
            )
        for provider, result, skip_reason in self.results:
            if skip_reason:
                lines.append(f"- {provider}: wykaz pominięty – {skip_reason}")
                continue
            line = f"- {provider}: przyjęte {result.accepted_count}, odrzucone {result.rejected_count}"
            if provider in self.residents:
                residents = format_residents(self.residents[provider])
                line += f", {residents} mieszkańców w promieniu {AED_RESIDENTS_RADIUS_METERS} m"
            lines.append(line)
        return "\n".join(lines)


def build_main_aed_df(lists: Iterable[AEDProviderList], today: Optional[datetime.date] = None) -> MainAEDResult:
    """
    Skleja wykazy wielu dostawców w jeden raport zbiorczy.

    Wykaz bez kolumn wzorca jest pomijany w całości (jak w DGA); z pozostałych
    do raportu trafiają tylko wiersze, które przeszły walidacje AED.
    """
    frames: List[pd.DataFrame] = []
    results: List[Tuple[str, Optional[AEDValidationResult], Optional[str]]] = []
    for provider_list in lists:
        try:
            result = validate_aed_df(provider_list.df, today=today)
        except MainAEDColumnsError as exc:
            results.append((provider_list.provider_name, None, str(exc)))
            continue
        results.append((provider_list.provider_name, result, None))
        if result.accepted.empty:
            continue
        frame = result.accepted.copy()
        frame.insert(0, MAIN_AED_PROVIDER_REGON_COLUMN, provider_list.provider_regon or AED_EMPTY_VALUE)
        frame.insert(0, MAIN_AED_PROVIDER_COLUMN, provider_list.provider_name)
        frames.append(frame)

    if frames:
        main_df = pd.concat(frames, ignore_index=True)
    else:
        main_df = pd.DataFrame(columns=[c for c in MAIN_AED_COLUMNS if c not in ("Lp.", MAIN_AED_DUPLICATE_COLUMN)])
    main_df = mark_cross_provider_duplicates(main_df)
    main_df.insert(0, "Lp.", range(1, len(main_df) + 1))
    main_df = main_df[MAIN_AED_COLUMNS]
    return MainAEDResult(main_df=main_df, results=results)


# Kolumny mapy portalu (GEO_TYPES): szerokość „b”, długość „l”, etykieta „label”.
AED_SCHEMA_GEO: Dict[str, str] = {
    "szerokosc_geograficzna": "b",
    "dlugosc_geograficzna": "l",
    "nazwa_miejsca": "label",
}
AED_SCHEMA_NUMBER_COLUMNS = ("szerokosc_geograficzna", "dlugosc_geograficzna", "Lp.")


def apply_aed_schema(tds: Optional[Dict[str, Any]], set_template_types: bool = False) -> Optional[Dict[str, Any]]:
    """
    Oznacza kolumny mapy, żeby portal od razu rysował punkty AED.

    Typy kolumn ze wzorca (``set_template_types``) ustawiamy tylko dla raportu
    zbiorczego: to CSV, który portal pisze sam, same teksty, a przy ponad
    5000 wierszy ``infer_schema`` mógłby zgadnąć np. „nr_budynku” jako liczbę
    i odrzucić „25/27”. W pliku dostawcy zostają typy zgadnięte przez portal:
    tabulator czyta komórki Excela jako daty i liczby, a typ „string” dla
    takiej komórki kończy się błędem walidacji danych zasobu.
    """
    if not tds or not tds.get("fields"):
        return tds
    known = set(MAIN_AED_COLUMNS)
    geo: Dict[str, Dict[str, Any]] = {}
    for index, schema_field in enumerate(tds["fields"]):
        name = str(schema_field.get("name", "")).strip()
        if name not in known:
            continue
        if set_template_types:
            schema_field["type"] = "number" if name in AED_SCHEMA_NUMBER_COLUMNS else "string"
            schema_field["format"] = "default"
        if name in AED_SCHEMA_GEO:
            schema_field["geo"] = AED_SCHEMA_GEO[name]
            geo[AED_SCHEMA_GEO[name]] = {"col_name": schema_field["name"], "col_index": index}
    if set(geo) == {"b", "l", "label"}:
        tds["geo"] = geo
    return tds


_SQUARE_KEY_FACTOR = 10_000_000


@dataclass
class PopulationGrid:
    """
    Siatka ludności 1 km w EPSG:3035 (spis 2021, Eurostat GISCO, dane GUS).
    Wiersz ``i`` obejmuje y od ``y0 - i * cell`` do ``y0 - (i + 1) * cell``.
    """

    population: Any  # numpy.ndarray
    x0: float
    y0: float
    cell: float

    @classmethod
    def from_npz(cls, path: str) -> "PopulationGrid":
        import numpy as np

        with np.load(path) as data:
            return cls(
                population=data["ludnosc"].astype("float64"),
                x0=float(data["x0"]),
                y0=float(data["y0"]),
                cell=float(data["rozmiar"]),
            )

    def residents_within(
        self,
        latitudes: Iterable[float],
        longitudes: Iterable[float],
        radius: float = AED_RESIDENTS_RADIUS_METERS,
    ) -> int:
        """
        Mieszkańcy w promieniu ``radius`` od dowolnego z punktów. Okrąg wokół
        każdego punktu dzielimy na kwadraty 50 x 50 m na wspólnej siatce, a kwadrat
        dostaje część ludności swojej komórki 1 km. Kwadraty sumujemy bez powtórzeń,
        więc AED blisko siebie nie liczą tych samych ludzi dwa razy.
        """
        import numpy as np
        from pyproj import Transformer

        latitudes = np.asarray(list(latitudes), dtype="float64")
        longitudes = np.asarray(list(longitudes), dtype="float64")
        if latitudes.size == 0:
            return 0
        step = AED_RESIDENTS_SQUARE_METERS
        n = int(radius // step) + 1
        offsets = np.arange(-n, n + 1) * step
        dx, dy = np.meshgrid(offsets, offsets)
        inside = dx**2 + dy**2 <= radius**2
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
        x, y = transformer.transform(longitudes, latitudes)
        square_x = np.round((np.asarray(x)[:, None] + dx[inside]) / step).astype(np.int64).ravel()
        square_y = np.round((np.asarray(y)[:, None] + dy[inside]) / step).astype(np.int64).ravel()
        keys = np.unique(square_x * _SQUARE_KEY_FACTOR + square_y)
        centre_x = (keys // _SQUARE_KEY_FACTOR) * step
        centre_y = (keys % _SQUARE_KEY_FACTOR) * step
        rows = np.floor((self.y0 - centre_y) / self.cell).astype(np.int64)
        cols = np.floor((centre_x - self.x0) / self.cell).astype(np.int64)
        on_grid = (rows >= 0) & (rows < self.population.shape[0]) & (cols >= 0) & (cols < self.population.shape[1])
        share = step * step / (self.cell * self.cell)
        return int(round(float(self.population[rows[on_grid], cols[on_grid]].sum()) * share))

    def residents_for_aed_df(self, df: pd.DataFrame, radius: float = AED_RESIDENTS_RADIUS_METERS) -> int:
        """Mieszkańcy w zasięgu AED z wierszy wykazu, które przeszły walidację (``AEDValidationResult.accepted``)."""
        if df.empty:
            return 0
        return self.residents_within(
            df["szerokosc_geograficzna"].astype(float),
            df["dlugosc_geograficzna"].astype(float),
            radius,
        )


def format_residents(count: int) -> str:
    """12797 -> „12 797” (twarda spacja, zapis polski)."""
    return f"{count:,}".replace(",", "\u00a0")
