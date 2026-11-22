"""
Wykaz AED tak, jak przychodzi od dostawców (bez bazy danych).

Pliki z repozytorium (wzorzec, dane demo), pliki zapisane przez Excel
i różne programy do CSV, przypadki skrajne oraz walidacja danych portalu
(goodtables), którą zasób musi przejść, żeby trafić do raportu zbiorczego.
"""

import datetime
import io
import random
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from mcod.resources.aed_constants import (
    AED_COLUMNS,
    MAIN_AED_COLUMNS,
    MAIN_AED_DUPLICATE_COLUMN,
    MAIN_AED_PROVIDER_COLUMN,
)
from mcod.resources.aed_validation import (
    AEDProviderList,
    MainAEDDuplicatedColumnError,
    MainAEDMissingRequiredColumnError,
    apply_aed_schema,
    build_main_aed_df,
    read_aed_file,
    validate_aed_df,
)

TODAY = datetime.date(2026, 11, 22)
REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = REPO_ROOT / "wzorzec"
DEMO_DIR = REPO_ROOT / "demo_aed" / "dane"


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
            "dostep_publiczny": "TAK",
            "urzadzenie_zamkniete": "NIE",
            "data_aktualizacji": "2026-11-21",
        }
    )
    row.update(overrides)
    return row


def rows(count, **overrides):
    return [aed_row(id_urzadzenia=f"AED-{number}", **overrides) for number in range(1, count + 1)]


def csv_bytes(data_rows, columns=None, delimiter=",", encoding="utf-8", line_end="\n"):
    columns = columns or AED_COLUMNS
    buffer = io.StringIO()
    pd.DataFrame(data_rows, columns=columns).to_csv(buffer, index=False, sep=delimiter, lineterminator=line_end)
    return buffer.getvalue().encode(encoding)


def xlsx_file(data_rows, columns=None, before_header=None, extra_sheets=()):
    """Plik xlsx zapisany komórka po komórce, jak przez Excel (typy komórek zostają)."""
    columns = columns or AED_COLUMNS
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for line in before_header or []:
        sheet.append(line)
    sheet.append(columns)
    for row in data_rows:
        sheet.append([row.get(column) for column in columns])
    for title in extra_sheets:
        workbook.create_sheet(title).append(["instrukcja"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def check(file, extension):
    return validate_aed_df(read_aed_file(file, extension), today=TODAY)


class TestFilesFromRepository:
    def test_template_xlsx_and_csv_pass_and_have_template_columns(self):
        for name in ("WYKAZ_AED_-_dostawca_XYZ.xlsx", "WYKAZ_AED_-_dostawca_XYZ.csv"):
            path = TEMPLATE_DIR / name
            with open(path, "rb") as file:
                df = read_aed_file(file, path.suffix)
            assert list(df.columns) == AED_COLUMNS, name
            result = validate_aed_df(df, today=TODAY)
            assert result.rejected == [], result.summary()
            assert result.accepted_count == 2

    def test_column_description_lists_every_template_column(self):
        with open(TEMPLATE_DIR / "opis_kolumn_wykazu_AED.xlsx", "rb") as file:
            description = pd.read_excel(file, dtype=str)
        assert description.iloc[:, 0].str.strip().tolist() == AED_COLUMNS

    @pytest.mark.parametrize(
        "name, accepted, rejected",
        [
            ("wykaz_aed_krosno.csv", 21, 0),
            ("wykaz_aed_legionowo.csv", 24, 0),
            ("wykaz_aed_przemysl.csv", 21, 0),
            ("wykaz_aed_warszawa.csv", 708, 0),
            ("wykaz_aed_testowy_z_bledami.csv", 1, 3),
        ],
    )
    def test_demo_lists(self, name, accepted, rejected):
        with open(DEMO_DIR / name, "rb") as file:
            result = check(file, "csv")
        assert (result.accepted_count, result.rejected_count) == (accepted, rejected), result.summary()


class TestExcelFiles:
    def test_cells_typed_by_excel(self):
        # Excel zamienia wpisane daty na daty i liczby na liczby.
        row = aed_row(
            szerokosc_geograficzna=52.317014,
            dlugosc_geograficzna=21.104131,
            nr_budynku=9,
            kod_terc=1465011,
            data_ostatniego_przegladu=datetime.datetime(2026, 5, 10),
            data_waznosci_elektrod=datetime.date(2027, 6, 30),
        )
        result = check(xlsx_file([row]), "xlsx")
        assert result.rejected == [], result.summary()
        accepted = result.accepted.loc[0]
        assert accepted["data_ostatniego_przegladu"] == "2026-05-10"
        assert accepted["data_waznosci_elektrod"] == "2027-06-30"
        assert accepted["nr_budynku"] == "9"

    def test_date_with_time_is_rejected_with_reason(self):
        row = aed_row(data_aktualizacji=datetime.datetime(2026, 11, 21, 14, 30))
        result = check(xlsx_file([row]), "xlsx")
        assert any(reason.startswith("data_aktualizacji") for reason in result.rejected[0].reasons)

    def test_postal_code_typed_as_number_is_rejected(self):
        # „05-270” wpisane bez kreski Excel zapisze jako liczbę 5270.
        result = check(xlsx_file([aed_row(kod_pocztowy=5270)]), "xlsx")
        assert any(reason.startswith("kod_pocztowy") for reason in result.rejected[0].reasons)

    def test_empty_cells_become_x(self):
        row = aed_row(nr_lokalu=None, model_urzadzenia=None, telefon_kontaktowy="")
        result = check(xlsx_file([row]), "xlsx")
        assert result.accepted.loc[0, ["nr_lokalu", "model_urzadzenia", "telefon_kontaktowy"]].tolist() == ["X"] * 3

    def test_only_first_sheet_is_read(self):
        result = check(xlsx_file(rows(3), extra_sheets=("Instrukcja", "Słowniki")), "xlsx")
        assert result.accepted_count == 3

    def test_title_rows_above_header_reject_whole_list(self):
        with pytest.raises(MainAEDMissingRequiredColumnError):
            check(xlsx_file(rows(1), before_header=[["Wykaz AED gminy Przykładowo"], []]), "xlsx")

    def test_trailing_empty_rows_are_ignored(self):
        file = xlsx_file(rows(2) + [{column: None for column in AED_COLUMNS}] * 3)
        result = check(file, "xlsx")
        assert result.accepted_count == 2

    def test_old_xls_format(self, tmp_path):
        pytest.importorskip("xlwt")
        path = tmp_path / "wykaz.xls"
        pd.DataFrame(rows(2), columns=AED_COLUMNS).to_excel(path, index=False, engine="xlwt")
        with open(path, "rb") as file:
            assert check(file, "xls").accepted_count == 2


class TestCsvFiles:
    @pytest.mark.parametrize(
        "delimiter, encoding, line_end",
        [
            (",", "utf-8", "\n"),  # LibreOffice, skrypty
            (",", "utf-8-sig", "\r\n"),  # Excel „CSV UTF-8”
            (";", "cp1250", "\r\n"),  # polski Excel „CSV (rozdzielany średnikami)”
            (";", "iso-8859-2", "\n"),
            ("\t", "utf-8", "\n"),  # kopia z arkusza
        ],
    )
    def test_dialects_and_polish_encodings(self, delimiter, encoding, line_end):
        data = rows(3, nazwa_miejsca='Żłobek "Słoneczko", parter, wewnątrz', miejscowosc="Łódź")
        result = check(io.BytesIO(csv_bytes(data, delimiter=delimiter, encoding=encoding, line_end=line_end)), "csv")
        assert result.accepted_count == 3, result.summary()
        assert result.accepted.loc[0, "miejscowosc"] == "Łódź"

    def test_quoted_values_with_delimiters_and_line_breaks(self):
        data = [aed_row(opis_lokalizacji='parter; przy portierni, obok windy\n"wejście B"')]
        result = check(io.BytesIO(csv_bytes(data, delimiter=";")), "csv")
        assert result.accepted.loc[0, "opis_lokalizacji"] == 'parter; przy portierni, obok windy\n"wejście B"'

    def test_leading_zeros_stay(self):
        data = [aed_row(id_urzadzenia="007", regon_dysponenta="012345678", kod_terc="0201011", kod_simc="0986283")]
        accepted = check(io.BytesIO(csv_bytes(data)), "csv").accepted.loc[0]
        assert accepted[["id_urzadzenia", "regon_dysponenta", "kod_terc", "kod_simc"]].tolist() == [
            "007",
            "012345678",
            "0201011",
            "0986283",
        ]

    def test_headers_with_spaces_upper_case_other_order_and_extra_columns(self):
        columns = list(reversed(AED_COLUMNS)) + ["uwagi_wewnetrzne"]
        data = [dict(aed_row(), uwagi_wewnetrzne="nie publikować")]
        content = csv_bytes(data, columns=columns).decode()
        header, body = content.split("\n", 1)
        header = ",".join(f" {name.upper()} " for name in header.split(","))
        result = check(io.BytesIO(f"{header}\n{body}".encode()), "csv")
        assert result.accepted_count == 1
        assert list(result.accepted.columns[: len(AED_COLUMNS)]) == AED_COLUMNS
        assert "uwagi_wewnetrzne" not in result.accepted.columns

    def test_non_breaking_spaces_and_padding_are_trimmed(self):
        data = [aed_row(miejscowosc="\xa0Marki ", dostep_24h=" nie ", szerokosc_geograficzna=" 52.317014\xa0")]
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert result.rejected == [], result.summary()
        assert result.accepted.loc[0, "dostep_24h"] == "NIE"

    def test_header_only(self):
        result = check(io.BytesIO(csv_bytes([])), "csv")
        assert (result.accepted_count, result.rejected_count) == (0, 0)

    def test_duplicated_header(self):
        content = ",".join(AED_COLUMNS + ["Id_Urzadzenia"]) + "\n" + ",".join(["X"] * (len(AED_COLUMNS) + 1)) + "\n"
        with pytest.raises(MainAEDDuplicatedColumnError):
            check(io.BytesIO(content.encode()), "csv")

    @pytest.mark.parametrize("content", [b"", b"\x00\x01\x02\xff\xfe binary", "jedna kolumna\nwartość\n".encode()])
    def test_not_a_list_never_passes(self, content):
        with pytest.raises(Exception):
            check(io.BytesIO(content), "csv")

    def test_unsupported_extension(self):
        with pytest.raises(ValueError):
            read_aed_file(io.BytesIO(b"{}"), "json")


class TestRowValues:
    @pytest.mark.parametrize(
        "latitude, longitude",
        [
            ("54.8358", "18.3364"),  # Jastrzębia Góra, północ
            ("49.0020", "22.8970"),  # Bieszczady, południe
            ("51.7592", "14.6200"),  # zachód
            ("50.8670", "24.1450"),  # wschód
            ("52.2297000000001", "21.0122"),  # dużo miejsc po przecinku
            ("5.22297E1", "2.10122e+01"),  # zapis naukowy z arkusza
        ],
    )
    def test_points_in_poland_are_accepted(self, latitude, longitude):
        data = [aed_row(szerokosc_geograficzna=latitude, dlugosc_geograficzna=longitude)]
        assert check(io.BytesIO(csv_bytes(data)), "csv").accepted_count == 1

    @pytest.mark.parametrize(
        "latitude, longitude, fragment",
        [
            ("21.104131", "52.317014", "zamienione"),
            ("-52.317014", "21.104131", "poza Polską"),
            ("0", "0", "poza Polską"),
            ("55.5", "21.0", "poza Polską"),
            ("52,317014", "21,104131", "kropką"),
            ("52°19'N", "21°06'E", "liczbami"),
            ("nan", "21.1", "liczbami"),
            ("inf", "21.1", "poza Polską"),
            ("X", "21.1", "szerokosc_geograficzna"),
        ],
    )
    def test_wrong_points_are_rejected_with_reason(self, latitude, longitude, fragment):
        data = [aed_row(szerokosc_geograficzna=latitude, dlugosc_geograficzna=longitude)]
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert result.accepted_count == 0
        assert any(fragment in reason for reason in result.rejected[0].reasons), result.rejected[0].reasons

    @pytest.mark.parametrize(
        "overrides",
        [
            {"godziny_pn": "00:00-24:00"},
            {"godziny_pn": "08:00-12:00, 13:00-16:00, 18:00-20:00"},
            {"dostep_24h": "TAK", **{column: "24h" for column in AED_COLUMNS if column.startswith("godziny_")}},
            {"data_waznosci_baterii": "2028-02-29"},
            {"kod_pocztowy": "00-001"},
            {"polozenie": "na zewnątrz"},
            {"dostep_publiczny": "tak", "urzadzenie_zamkniete": "Nie"},
        ],
    )
    def test_valid_variants(self, overrides):
        result = check(io.BytesIO(csv_bytes([aed_row(**overrides)])), "csv")
        assert result.rejected == [], result.summary()

    @pytest.mark.parametrize(
        "overrides, column",
        [
            ({"godziny_pn": "8-16"}, "godziny_pn"),
            ({"godziny_pn": "25:00-26:00"}, "godziny_pn"),
            ({"godziny_pn": "08:00-16:00,"}, "godziny_pn"),
            ({"data_waznosci_baterii": "2027-02-29"}, "data_waznosci_baterii"),
            ({"data_aktualizacji": "21.11.2026"}, "data_aktualizacji"),
            ({"data_aktualizacji": "2026-11-21T10:00"}, "data_aktualizacji"),
            ({"kod_pocztowy": "05 270"}, "kod_pocztowy"),
            ({"dostep_publiczny": "T"}, "dostep_publiczny"),
            ({"dostep_24h": "TAK", "godziny_nd": "nieczynne"}, "dostep_24h"),
        ],
    )
    def test_invalid_variants(self, overrides, column):
        result = check(io.BytesIO(csv_bytes([aed_row(**overrides)])), "csv")
        assert any(reason.startswith(column) for reason in result.rejected[0].reasons), result.summary()

    def test_all_errors_of_a_row_are_listed_at_once(self):
        row = aed_row(nazwa_miejsca="X", kod_pocztowy="5270", dostep_24h="?", godziny_wt="zawsze")
        reasons = check(io.BytesIO(csv_bytes([row])), "csv").rejected[0].reasons
        assert len(reasons) == 4

    def test_row_numbers_match_spreadsheet_rows(self):
        data = rows(5)
        data[3]["kod_pocztowy"] = "bad"
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert [(issue.row_number, issue.device_id) for issue in result.rejected] == [(5, "AED-4")]

    def test_repeated_ids_reject_later_rows_only(self):
        data = rows(3)
        data[2]["id_urzadzenia"] = "AED-1"
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert result.accepted["id_urzadzenia"].tolist() == ["AED-1", "AED-2"]
        assert "wiersz 2" in result.rejected[0].reasons[0]

    def test_expired_parts_warn_but_row_stays(self):
        data = [aed_row(data_waznosci_elektrod="2025-01-01", data_waznosci_baterii="2027-01-15")]
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert result.accepted_count == 1
        assert len(result.warnings[0].reasons) == 2

    @pytest.mark.parametrize(
        "column, written, stored",
        [
            ("polozenie", "Wewnątrz", "wewnątrz"),
            ("polozenie", "NA ZEWNĄTRZ", "na zewnątrz"),
            ("godziny_pn", "24H", "24h"),
            ("godziny_pn", "Nieczynne", "nieczynne"),
            ("godziny_pn", "8:00-16:00", "08:00-16:00"),
            ("godziny_pn", "08:00 - 16:00", "08:00-16:00"),
            ("godziny_pn", "8:00-12:00,13:00-16:00", "08:00-12:00, 13:00-16:00"),
        ],
    )
    def test_spelling_variants_people_use_are_stored_in_template_form(self, column, written, stored):
        result = check(io.BytesIO(csv_bytes([aed_row(**{column: written})])), "csv")
        assert result.rejected == [], result.summary()
        assert result.accepted.loc[0, column] == stored

    def test_24h_device_with_closed_day_written_in_capitals_is_still_rejected(self):
        data = [aed_row(dostep_24h="TAK", godziny_nd="NIECZYNNE")]
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert any(reason.startswith("dostep_24h") for reason in result.rejected[0].reasons)

    @pytest.mark.parametrize("hours", ["08:00-16:00", "00:00-12:00, 12:30-24:00", "8:00 - 16:00"])
    def test_24h_device_with_limited_hours_is_rejected(self, hours):
        data = [aed_row(dostep_24h="TAK", godziny_pn=hours)]
        result = check(io.BytesIO(csv_bytes(data)), "csv")
        assert result.accepted_count == 0
        assert any("nie jest całodobowy" in reason and "godziny_pn" in reason for reason in result.rejected[0].reasons)

    @pytest.mark.parametrize("hours", ["24h", "24H", "00:00-24:00", "X"])
    def test_24h_device_with_full_day_or_unknown_hours_is_accepted(self, hours):
        data = [aed_row(dostep_24h="TAK", **{column: hours for column in AED_COLUMNS if column.startswith("godziny_")})]
        assert check(io.BytesIO(csv_bytes(data)), "csv").rejected == []

    def test_device_without_24h_access_may_have_limited_hours(self):
        data = [aed_row(dostep_24h="NIE", godziny_pn="08:00-16:00")]
        assert check(io.BytesIO(csv_bytes(data)), "csv").accepted_count == 1


class TestMainReport:
    def test_many_providers_large_volume(self):
        random.seed(7)
        lists = []
        for number in range(10):
            data = [
                aed_row(
                    id_urzadzenia=f"P{number}-{index}",
                    szerokosc_geograficzna=f"{random.uniform(49.2, 54.7):.6f}",
                    dlugosc_geograficzna=f"{random.uniform(14.3, 23.9):.6f}",
                )
                for index in range(2000)
            ]
            lists.append(AEDProviderList(f"Dostawca {number}", f"{number:09d}", pd.DataFrame(data, columns=AED_COLUMNS)))
        result = build_main_aed_df(lists, today=TODAY)
        assert len(result.main_df) == 20000
        assert result.main_df["Lp."].tolist() == list(range(1, 20001))
        assert list(result.main_df.columns) == MAIN_AED_COLUMNS

    def test_provider_lists_in_mixed_formats(self):
        excel = read_aed_file(xlsx_file([aed_row(szerokosc_geograficzna=52.2297, dlugosc_geograficzna=21.0122)]), "xlsx")
        polish_csv = read_aed_file(io.BytesIO(csv_bytes(rows(2), delimiter=";", encoding="cp1250")), "csv")
        broken = pd.DataFrame([{"id": 1}])
        result = build_main_aed_df(
            [
                AEDProviderList("Gmina A", "1", excel),
                AEDProviderList("Firma B", "", polish_csv),
                AEDProviderList("C", "3", broken),
            ],
            today=TODAY,
        )
        assert result.main_df[MAIN_AED_PROVIDER_COLUMN].value_counts().to_dict() == {"Firma B": 2, "Gmina A": 1}
        assert result.main_df.loc[result.main_df[MAIN_AED_PROVIDER_COLUMN] == "Firma B", "REGON dostawcy"].unique().tolist() == [
            "X"
        ]
        assert "pominięty" in result.summary()

    def test_same_device_reported_by_two_providers_is_marked_on_both(self):
        gmina = pd.DataFrame([aed_row(id_urzadzenia="G-1")], columns=AED_COLUMNS)
        firma = pd.DataFrame(
            [aed_row(id_urzadzenia="F-9", szerokosc_geograficzna="52.317100", dlugosc_geograficzna="21.104131")],
            columns=AED_COLUMNS,
        )
        report = build_main_aed_df(
            [AEDProviderList("Gmina", "1", gmina), AEDProviderList("Firma", "2", firma)], today=TODAY
        ).main_df
        assert report[MAIN_AED_DUPLICATE_COLUMN].tolist() == ["Firma: F-9", "Gmina: G-1"]

    def test_two_institutions_with_the_same_name_are_different_providers(self):
        data = pd.DataFrame([aed_row()], columns=AED_COLUMNS)
        lists = [
            AEDProviderList("Urząd Gminy", "1", data, provider_id=10),
            AEDProviderList("Urząd Gminy", "1", data, provider_id=11),
        ]
        report = build_main_aed_df(lists, today=TODAY).main_df
        assert report[MAIN_AED_DUPLICATE_COLUMN].tolist() == ["Urząd Gminy: AED-1", "Urząd Gminy: AED-1"]

    def test_two_lists_of_one_institution_are_one_provider(self):
        first = pd.DataFrame([aed_row(id_urzadzenia="A-1")], columns=AED_COLUMNS)
        second = pd.DataFrame([aed_row(id_urzadzenia="A-2", szerokosc_geograficzna="52.317050")], columns=AED_COLUMNS)
        lists = [AEDProviderList("Gmina", "1", first, provider_id=10), AEDProviderList("Gmina", "1", second, provider_id=10)]
        report = build_main_aed_df(lists, today=TODAY).main_df
        assert report[MAIN_AED_DUPLICATE_COLUMN].tolist() == ["X", "X"]
        assert "_klucz_dostawcy" not in report.columns

    @pytest.mark.parametrize(
        "value",
        ['=HYPERLINK("http://example.com","AED")', "+48 22 000 00 00", "-1+1", "@SUM(A1:A2)", "\t=1+1"],
    )
    def test_formula_in_cell_does_not_reach_report_as_formula(self, value):
        # Białe znaki na brzegach obcina już normalizacja, więc „\t=1+1” dochodzi jako „=1+1”.
        data = pd.DataFrame([aed_row(nazwa_miejsca=value, opis_lokalizacji=value)], columns=AED_COLUMNS)
        report = build_main_aed_df([AEDProviderList("Gmina", "1", data)], today=TODAY).main_df
        assert report.loc[0, "nazwa_miejsca"] == "'" + value.strip()
        assert report.loc[0, "opis_lokalizacji"] == "'" + value.strip()

    def test_ordinary_values_and_numbers_are_not_changed(self):
        data = pd.DataFrame([aed_row(nazwa_miejsca="Szkoła nr 2 – wejście B", nr_budynku="25/27")], columns=AED_COLUMNS)
        report = build_main_aed_df([AEDProviderList("Gmina", "1", data)], today=TODAY).main_df
        assert report.loc[0, "nazwa_miejsca"] == "Szkoła nr 2 – wejście B"
        assert report.loc[0, "nr_budynku"] == "25/27"
        assert isinstance(report.loc[0, "szerokosc_geograficzna"], float)


class TestPortalDataValidation:
    """Walidacja danych portalu (goodtables) ze schematem, który ustawia moduł AED."""

    def _portal_report(self, path, file_format, main_report=False):
        from goodtables import validate as validate_table
        from tableschema import Table

        table = Table(str(path), format=file_format, ignore_blank_headers=True)
        schema = apply_aed_schema(table.infer(limit=5000, missing_values=["X"]), set_template_types=main_report)
        report = validate_table(str(path), schema=schema, checks=["structure", "schema"], format=file_format, preset="table")
        return report, schema

    def test_provider_excel_with_typed_cells(self, tmp_path):
        path = tmp_path / "wykaz.xlsx"
        typed = aed_row(nr_budynku=9, kod_terc=1465011, szerokosc_geograficzna=52.31, dlugosc_geograficzna=21.1)
        typed["data_waznosci_elektrod"] = datetime.datetime(2027, 6, 30)
        path.write_bytes(xlsx_file([typed, aed_row(id_urzadzenia="AED-2", nr_budynku="25/27")]).getvalue())
        report, schema = self._portal_report(path, "xlsx")
        assert report["valid"], report["tables"][0]["errors"]
        assert set(schema["geo"]) == {"b", "l", "label"}

    def test_provider_polish_csv(self, tmp_path):
        path = tmp_path / "wykaz.csv"
        path.write_bytes(csv_bytes(rows(3), delimiter=";", encoding="utf-8"))
        report, _ = self._portal_report(path, "csv")
        assert report["valid"], report["tables"][0]["errors"]

    def test_main_report_where_building_numbers_change_type_after_5000_rows(self, tmp_path):
        # Bez typów ze wzorca portal zgadłby z pierwszych 5000 wierszy liczbę i odrzucił „25/27”.
        data = rows(5001, nr_budynku="12")
        for index, row in enumerate(data):
            row["szerokosc_geograficzna"] = f"{49.5 + index * 0.0009:.6f}"
        data[-1]["nr_budynku"] = "25/27"
        report_df = build_main_aed_df(
            [AEDProviderList("Gmina", "1", pd.DataFrame(data, columns=AED_COLUMNS))], today=TODAY
        ).main_df
        path = tmp_path / "raport.csv"
        report_df.to_csv(path, index=False, encoding="utf-8")
        report, _ = self._portal_report(path, "csv", main_report=True)
        assert report["valid"], report["tables"][0]["errors"]
