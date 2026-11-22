"""Testy walidacji wykazu AED i sklejania w raport zbiorczy (bez bazy danych)."""

import datetime

import pandas as pd
import pytest

from mcod.resources.aed_constants import (
    AED_COLUMNS,
    MAIN_AED_COLUMNS,
    MAIN_AED_DUPLICATE_COLUMN,
    MAIN_AED_PROVIDER_COLUMN,
    MAIN_AED_WARNINGS_COLUMN,
)
from mcod.resources.aed_validation import (
    AEDProviderList,
    MainAEDMissingRequiredColumnError,
    build_main_aed_df,
    distance_meters,
    validate_aed_df,
)

TODAY = datetime.date(2026, 11, 22)


def aed_row(**overrides):
    row = {column: "X" for column in AED_COLUMNS}
    row.update(
        {
            "id_urzadzenia": "AED-1",
            "nazwa_dysponenta": "Urząd Miasta Przykładowo",
            "nazwa_miejsca": "Szkoła Podstawowa nr 2",
            "nazwa_ulicy": "Szkolna",
            "nr_budynku": "9",
            "kod_pocztowy": "05-270",
            "miejscowosc": "Marki",
            "szerokosc_geograficzna": "52.317014",
            "dlugosc_geograficzna": "21.104131",
            "polozenie": "wewnątrz",
            "dostep_24h": "NIE",
            "godziny_pn": "07:00-17:00",
            "godziny_so": "nieczynne",
            "dostep_publiczny": "TAK",
            "urzadzenie_zamkniete": "NIE",
            "data_waznosci_elektrod": "2027-06-30",
            "data_aktualizacji": "2026-11-21",
        }
    )
    row.update(overrides)
    return row


def aed_df(*rows):
    return pd.DataFrame(list(rows), columns=AED_COLUMNS)


class TestValidateAedDf:
    def test_valid_row_is_accepted(self):
        result = validate_aed_df(aed_df(aed_row()), today=TODAY)
        assert result.accepted_count == 1
        assert result.rejected == []
        assert result.accepted.loc[0, "szerokosc_geograficzna"] == pytest.approx(52.317014)
        assert result.accepted.loc[0, MAIN_AED_WARNINGS_COLUMN] == "X"

    def test_missing_template_column_rejects_whole_list(self):
        df = aed_df(aed_row()).drop(columns=["godziny_pn", "polozenie"])
        with pytest.raises(MainAEDMissingRequiredColumnError) as exc:
            validate_aed_df(df, today=TODAY)
        assert exc.value.column_names == ["polozenie", "godziny_pn"]

    def test_headers_and_empty_cells_are_normalized(self):
        df = aed_df(aed_row(dostep_publiczny="tak", nr_lokalu=None, szerokosc_geograficzna="52,317014"))
        df.columns = [f" {column.upper()} " for column in df.columns]
        result = validate_aed_df(df, today=TODAY)
        assert result.accepted_count == 1
        assert result.accepted.loc[0, "dostep_publiczny"] == "TAK"
        assert result.accepted.loc[0, "nr_lokalu"] == "X"

    @pytest.mark.parametrize("column", ["id_urzadzenia", "nazwa_miejsca", "miejscowosc", "szerokosc_geograficzna"])
    def test_required_value_cannot_be_x(self, column):
        result = validate_aed_df(aed_df(aed_row(**{column: "X"})), today=TODAY)
        assert result.accepted_count == 0
        assert f"brak wartości w kolumnie {column}" in result.rejected[0].reasons

    def test_swapped_coordinates_are_detected(self):
        result = validate_aed_df(
            aed_df(aed_row(szerokosc_geograficzna="21.104131", dlugosc_geograficzna="52.317014")), today=TODAY
        )
        assert "zamienione współrzędne" in result.rejected[0].reasons[0]

    def test_point_outside_poland_is_rejected(self):
        result = validate_aed_df(aed_df(aed_row(szerokosc_geograficzna="48.8566", dlugosc_geograficzna="2.3522")), today=TODAY)
        assert "poza Polską" in result.rejected[0].reasons[0]

    def test_non_numeric_coordinates_are_rejected(self):
        result = validate_aed_df(aed_df(aed_row(szerokosc_geograficzna="52°19'N")), today=TODAY)
        assert "liczbami" in result.rejected[0].reasons[0]

    @pytest.mark.parametrize(
        "overrides, fragment",
        [
            ({"dostep_24h": "czasami"}, "dostep_24h"),
            ({"data_aktualizacji": "21.11.2026"}, "data_aktualizacji"),
            ({"data_waznosci_baterii": "2026-02-30"}, "data_waznosci_baterii"),
            ({"kod_pocztowy": "05270"}, "kod_pocztowy"),
            ({"polozenie": "w holu"}, "polozenie"),
            ({"godziny_pn": "pn-pt 7-17"}, "godziny_pn"),
            ({"godziny_wt": "25:00-26:00"}, "godziny_wt"),
        ],
    )
    def test_format_errors_reject_row_with_reason(self, overrides, fragment):
        result = validate_aed_df(aed_df(aed_row(**overrides)), today=TODAY)
        assert result.accepted_count == 0
        assert any(reason.startswith(fragment) for reason in result.rejected[0].reasons)

    def test_multiple_hour_ranges_and_24h_are_valid(self):
        row = aed_row(godziny_pn="08:00-12:00, 13:00-16:00", godziny_nd="24h")
        assert validate_aed_df(aed_df(row), today=TODAY).accepted_count == 1

    def test_24h_device_cannot_have_closed_day(self):
        result = validate_aed_df(aed_df(aed_row(dostep_24h="TAK", godziny_so="nieczynne")), today=TODAY)
        assert "dostep_24h = TAK" in result.rejected[0].reasons[0]

    def test_duplicate_device_id_is_rejected(self):
        result = validate_aed_df(aed_df(aed_row(), aed_row(nazwa_miejsca="Hala sportowa")), today=TODAY)
        assert result.accepted_count == 1
        assert result.rejected[0].row_number == 3
        assert "powtarza się (wiersz 2)" in result.rejected[0].reasons[0]

    def test_expiring_electrodes_and_expired_battery_are_warnings(self):
        row = aed_row(data_waznosci_elektrod="2026-12-31", data_waznosci_baterii="2026-01-31")
        result = validate_aed_df(aed_df(row), today=TODAY)
        assert result.accepted_count == 1
        warning = result.accepted.loc[0, MAIN_AED_WARNINGS_COLUMN]
        assert "elektrody: termin ważności mija 2026-12-31" in warning
        assert "bateria: termin ważności minął 2026-01-31" in warning

    def test_summary_lists_rejection_reasons(self):
        result = validate_aed_df(aed_df(aed_row(), aed_row(id_urzadzenia="AED-2", kod_pocztowy="abc")), today=TODAY)
        assert "Wiersz 3 (AED-2): odrzucony – kod_pocztowy" in result.summary()


class TestBuildMainAedDf:
    def test_lists_from_three_providers_are_merged(self):
        lists = [
            AEDProviderList("Urząd Miasta A", "000000001", aed_df(aed_row(), aed_row(id_urzadzenia="AED-2", szerokosc_geograficzna="52.3"))),
            AEDProviderList("Fundacja B", "000000002", aed_df(aed_row(szerokosc_geograficzna="50.06", dlugosc_geograficzna="19.94"))),
            AEDProviderList("OSP C", "", aed_df(aed_row(szerokosc_geograficzna="54.35", dlugosc_geograficzna="18.65"))),
        ]
        result = build_main_aed_df(lists, today=TODAY)
        main_df = result.main_df
        assert list(main_df.columns) == MAIN_AED_COLUMNS
        assert list(main_df["Lp."]) == [1, 2, 3, 4]
        assert list(main_df[MAIN_AED_PROVIDER_COLUMN]) == ["Urząd Miasta A", "Urząd Miasta A", "Fundacja B", "OSP C"]
        assert main_df.loc[3, "REGON dostawcy"] == "X"
        assert "4 AED od 3 dostawców" in result.summary()

    def test_list_without_template_columns_is_skipped(self):
        broken = aed_df(aed_row()).drop(columns=["polozenie"])
        result = build_main_aed_df(
            [AEDProviderList("Dobry", "1", aed_df(aed_row())), AEDProviderList("Zły", "2", broken)], today=TODAY
        )
        assert len(result.main_df) == 1
        assert "Zły: wykaz pominięty – Brak wymaganych kolumn: polozenie" in result.summary()

    def test_invalid_rows_do_not_enter_report(self):
        df = aed_df(aed_row(), aed_row(id_urzadzenia="AED-2", szerokosc_geograficzna="2.35", dlugosc_geograficzna="48.85"))
        result = build_main_aed_df([AEDProviderList("A", "1", df)], today=TODAY)
        assert list(result.main_df["id_urzadzenia"]) == ["AED-1"]
        assert "przyjęte 1, odrzucone 1" in result.summary()

    def test_close_points_of_different_providers_are_marked_as_duplicates(self):
        near = aed_row(id_urzadzenia="B-7", szerokosc_geograficzna="52.317050", dlugosc_geograficzna="21.104131")
        far = aed_row(id_urzadzenia="B-8", szerokosc_geograficzna="52.40", dlugosc_geograficzna="21.10")
        result = build_main_aed_df(
            [AEDProviderList("A", "1", aed_df(aed_row())), AEDProviderList("B", "2", aed_df(near, far))], today=TODAY
        )
        duplicates = list(result.main_df[MAIN_AED_DUPLICATE_COLUMN])
        assert duplicates == ["B: B-7", "A: AED-1", "X"]

    def test_close_points_of_same_provider_are_not_duplicates(self):
        second = aed_row(id_urzadzenia="AED-2", szerokosc_geograficzna="52.317050")
        result = build_main_aed_df([AEDProviderList("A", "1", aed_df(aed_row(), second))], today=TODAY)
        assert list(result.main_df[MAIN_AED_DUPLICATE_COLUMN]) == ["X", "X"]

    def test_no_valid_lists_gives_empty_report_with_columns(self):
        result = build_main_aed_df([], today=TODAY)
        assert result.main_df.empty
        assert list(result.main_df.columns) == MAIN_AED_COLUMNS


def test_distance_meters():
    assert distance_meters((52.317014, 21.104131), (52.317050, 21.104131)) == pytest.approx(4.0, abs=0.5)
