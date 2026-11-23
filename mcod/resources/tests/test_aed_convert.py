"""Testy konwertera wykazu AED (bez bazy danych), na fragmentach prawdziwych plików z dane.gov.pl."""

import datetime
import io

import pandas as pd

from mcod.resources.aed_constants import AED_COLUMNS
from mcod.resources.aed_convert import convert_to_aed, header_key
from mcod.resources.aed_validation import read_aed_file, validate_aed_df

TODAY = datetime.date(2026, 11, 22)

# Fragmenty wykazów AED z dane.gov.pl, pobrane 21.11.2026.
KROSNO = (
    "Długość geograficzna,Szerokość geograficzna, Nazwa, Lokalizacja, Adres, Numer Id\n"
    '21.72034402175176,49.718809346153336,"Defibrylator","Zespół  Krytych Pływalni","ul. Jasna, 38-400 Krosno","1"\n'
    '21.71133598253567,49.719088753029276,"Defibrylator","Kampus Sportowo-dydaktyczny, portiernia",'
    '"ul. Stanisława Wyspiańskiego 20, 38-400 Krosno","2"\n'
    '21.715090873839404,49.72174399261284,"Defibrylator","OSP Turaszówka","ul. Rzeszowska, 38-400 Krosno","3"\n'
).encode("utf-8")

# Marki: każdy wiersz w całości w cudzysłowie, a w kolumnie „Długość” jest szerokość.
MARKI = (
    '"Długość geograficzna,Szerokość geograficzna, Nazwa, Lokalizacja, Adres, Numer Id"\n'
    '"52.326697, 21.107557,""Defibrylator"",""Urząd Miasta Marki "",""Al.. Piłsudskiego 95, 05-270 Marki"",""1"""\n'
    '"52.323960, 21.098185,""Defibrylator"",""Szkoła Podstawowa nr 1 "",""ul. Okólna 14, 05-270 Marki"",""2"""\n'
    '"52.317014, 21.104131,""Defibrylator"",""Szkoła Podstawowa nr 2 "",""ul. Szkolna 9, 05-270 Marki"",""3"""\n'
).encode("utf-8")


def _read(raw: bytes, extension: str = "csv") -> pd.DataFrame:
    return read_aed_file(io.BytesIO(raw), extension)


def test_header_key_ignores_case_spaces_and_polish_letters():
    assert header_key(" Szerokość geograficzna ") == "szerokosc_geograficzna"
    assert header_key("Długość") == "dlugosc"
    assert header_key("Numer Id") == "numer_id"


def test_marki_is_unwrapped_unswapped_and_split():
    result = convert_to_aed(_read(MARKI))
    row = result.df.iloc[0]
    assert list(result.df.columns) == AED_COLUMNS
    assert row["szerokosc_geograficzna"] == "52.326697"
    assert row["dlugosc_geograficzna"] == "21.107557"
    assert row["nazwa_miejsca"] == "Urząd Miasta Marki"
    assert row["cecha_ulicy"] == "aleja"
    assert row["nazwa_ulicy"] == "Piłsudskiego"
    assert row["nr_budynku"] == "95"
    assert row["kod_pocztowy"] == "05-270"
    assert row["miejscowosc"] == "Marki"
    assert row["id_urzadzenia"] == "1"
    assert row["regon_dysponenta"] == "X"
    assert any("cudzysłów" in change for change in result.changes)
    assert any("Zamieniono miejscami" in change for change in result.changes)
    assert "regon_dysponenta" in result.missing


def test_krosno_picks_location_over_constant_name_and_splits_address_without_number():
    result = convert_to_aed(_read(KROSNO))
    first, second = result.df.iloc[0], result.df.iloc[1]
    assert first["nazwa_miejsca"] == "Zespół  Krytych Pływalni"
    assert first["nazwa_ulicy"] == "Jasna"
    assert first["nr_budynku"] == "X"
    assert second["nazwa_ulicy"] == "Stanisława Wyspiańskiego"
    assert second["nr_budynku"] == "20"
    assert "Nazwa" in result.unmapped
    assert not any("Zamieniono miejscami" in change for change in result.changes)


def test_converted_city_files_pass_aed_validation():
    for raw in (KROSNO, MARKI):
        result = convert_to_aed(_read(raw))
        validation = validate_aed_df(result.df, today=TODAY)
        assert validation.rejected_count == 0, validation.summary()
        assert validation.accepted_count == 3


def test_converted_file_can_be_read_back_by_the_portal():
    result = convert_to_aed(_read(MARKI))
    again = read_aed_file(io.BytesIO(result.to_csv_bytes()), "csv")
    assert validate_aed_df(again, today=TODAY).accepted_count == 3


def test_synonyms_dates_yes_no_location_and_full_day_hours():
    df = pd.DataFrame(
        {
            "ID": ["A1", "A2"],
            "Nazwa obiektu": ["Basen", "Szkoła"],
            "Miasto": ["Kraków", "Kraków"],
            "lat": ["50,0614", "50.0700"],
            "lng": ["19,9366", "19.9400"],
            "Całodobowy": ["tak", "nie"],
            "Godziny": ["Całodobowo", "pn-pt 8-16"],
            "Umieszczenie": ["Wewnątrz", "na zewnątrz"],
            "Elektrody": ["30.06.2027", "2027.01.05"],
            "Uwagi": ["coś", ""],
        }
    )
    result = convert_to_aed(df)
    first, second = result.df.iloc[0], result.df.iloc[1]
    assert first["szerokosc_geograficzna"] == "50.0614"
    assert first["dlugosc_geograficzna"] == "19.9366"
    assert first["dostep_24h"] == "TAK"
    assert second["dostep_24h"] == "NIE"
    assert first["godziny_pn"] == "24h" and first["godziny_nd"] == "24h"
    assert second["godziny_pn"] == "X"
    assert "godziny: pn-pt 8-16" in second["opis_lokalizacji"]
    assert first["polozenie"] == "wewnątrz"
    assert second["polozenie"] == "na zewnątrz"
    assert first["data_waznosci_elektrod"] == "2027-06-30"
    assert second["data_waznosci_elektrod"] == "2027-01-05"
    assert result.unmapped == ["Uwagi"]
    assert validate_aed_df(result.df, today=TODAY).rejected_count == 0


def test_coordinates_in_one_column_and_missing_ids():
    df = pd.DataFrame({"Nazwa": ["Urząd", "Hala"], "Miejscowość": ["Legionowo", "Legionowo"], "Współrzędne": ["52.40, 20.93", "52.41;20.95"]})
    result = convert_to_aed(df)
    assert list(result.df["szerokosc_geograficzna"]) == ["52.40", "52.41"]
    assert list(result.df["dlugosc_geograficzna"]) == ["20.93", "20.95"]
    assert list(result.df["id_urzadzenia"]) == ["AED-0001", "AED-0002"]
    assert validate_aed_df(result.df, today=TODAY).rejected_count == 0


def test_address_only_file_is_not_geocoded_and_is_rejected_by_validation():
    df = pd.DataFrame({"Nazwa": ["Urząd"], "Adres": ["ul. Jasna 1, 38-400 Krosno"]})
    result = convert_to_aed(df)
    assert result.df.iloc[0]["szerokosc_geograficzna"] == "X"
    assert any("bez których punktu nie da się pokazać" in change for change in result.changes)
    assert validate_aed_df(result.df, today=TODAY).rejected_count == 1


def test_template_file_is_unchanged():
    row = {column: "X" for column in AED_COLUMNS}
    row.update(
        id_urzadzenia="1",
        nazwa_miejsca="Urząd",
        miejscowosc="Legionowo",
        szerokosc_geograficzna="52.4",
        dlugosc_geograficzna="20.9",
    )
    df = pd.DataFrame([row], columns=AED_COLUMNS)
    result = convert_to_aed(df)
    assert result.df.equals(df)
    assert result.unmapped == []
