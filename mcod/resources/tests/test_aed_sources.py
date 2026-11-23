"""Zakres referencyjny źródła w raporcie zbiorczym AED (bez bazy danych)."""

import datetime

import pandas as pd

from mcod.resources.aed_constants import (
    AED_COLUMNS,
    MAIN_AED_COLUMNS,
    MAIN_AED_SOURCE_COLUMN,
    MAIN_AED_SOURCE_DATE_COLUMN,
    MAIN_AED_SOURCE_LICENSE_COLUMN,
)
from mcod.resources.aed_validation import AEDProviderList, build_main_aed_df

TODAY = datetime.date(2026, 11, 22)


def _df(device_id: str, lat: str, lon: str) -> pd.DataFrame:
    row = {column: "X" for column in AED_COLUMNS}
    row.update(id_urzadzenia=device_id, nazwa_miejsca="Urząd", miejscowosc="Legionowo",
               szerokosc_geograficzna=lat, dlugosc_geograficzna=lon)
    return pd.DataFrame([row], columns=AED_COLUMNS)


def test_main_report_shows_source_license_and_date_for_every_row():
    lists = [
        AEDProviderList("Urząd Miasta Legionowo", "000000000", _df("L1", "52.40", "20.93"), provider_id=1,
                        source_url="https://dane.gov.pl/pl/dataset/1/resource/11", source_license="CC0 1.0",
                        source_date="2026-11-22"),
        AEDProviderList("Urząd Miasta Krosna", "", _df("K1", "49.70", "21.77"), provider_id=2),
    ]
    main_df = build_main_aed_df(lists, today=TODAY).main_df
    assert list(main_df.columns) == MAIN_AED_COLUMNS
    legionowo, krosno = main_df.iloc[0], main_df.iloc[1]
    assert legionowo[MAIN_AED_SOURCE_COLUMN] == "https://dane.gov.pl/pl/dataset/1/resource/11"
    assert legionowo[MAIN_AED_SOURCE_LICENSE_COLUMN] == "CC0 1.0"
    assert legionowo[MAIN_AED_SOURCE_DATE_COLUMN] == "2026-11-22"
    # Brak metadanych to „X”, jak każda pusta komórka wzorca.
    assert krosno[MAIN_AED_SOURCE_COLUMN] == "X"
    assert krosno[MAIN_AED_SOURCE_LICENSE_COLUMN] == "X"


def test_source_columns_come_right_after_provider():
    assert MAIN_AED_COLUMNS[1:6] == [
        "Nazwa dostawcy",
        "REGON dostawcy",
        MAIN_AED_SOURCE_COLUMN,
        MAIN_AED_SOURCE_LICENSE_COLUMN,
        MAIN_AED_SOURCE_DATE_COLUMN,
    ]
