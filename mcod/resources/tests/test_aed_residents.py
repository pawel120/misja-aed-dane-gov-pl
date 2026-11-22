"""Mieszkańcy w promieniu 200 m od AED (komunikaty w panelu, bez bazy danych)."""

from pathlib import Path

import pandas as pd
import pytest

from mcod.resources.aed_constants import AED_COLUMNS
from mcod.resources.aed_validation import (
    AEDProviderList,
    PopulationGrid,
    build_main_aed_df,
    format_residents,
    read_aed_file,
    validate_aed_df,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GRID_PATH = REPO_ROOT / "data" / "aed" / "ludnosc_pl_1km_epsg3035.npz"
DEMO_DIR = REPO_ROOT / "demo_aed" / "dane"


@pytest.fixture(scope="module")
def grid():
    return PopulationGrid.from_npz(str(GRID_PATH))


def demo_accepted(name):
    with open(DEMO_DIR / name, "rb") as file:
        return validate_aed_df(read_aed_file(file, "csv")).accepted


@pytest.mark.parametrize(
    "name, expected",
    [
        # Wyniki referencyjne skryptu kampanii (hacknation/aed_dane/zasieg.py, raster GISCO).
        ("wykaz_aed_legionowo.csv", 12797),
        ("wykaz_aed_warszawa.csv", 480342),
    ],
)
def test_reference_results_for_demo_lists(grid, name, expected):
    assert grid.residents_for_aed_df(demo_accepted(name)) == pytest.approx(expected, rel=0.001)


def test_devices_close_to_each_other_do_not_count_people_twice(grid):
    single = grid.residents_within([52.4046], [20.9497])
    assert single > 0
    assert grid.residents_within([52.4046, 52.4046], [20.9497, 20.9497]) == single
    near = grid.residents_within([52.4046, 52.40469], [20.9497, 20.9497])  # ok. 10 m dalej
    assert single <= near < 2 * single


def test_larger_radius_covers_more_people(grid):
    assert grid.residents_within([52.2297], [21.0122], radius=500) > grid.residents_within([52.2297], [21.0122], radius=200)


@pytest.mark.parametrize(
    "latitude, longitude",
    [
        (40.0, 0.0),  # daleko poza siatką
        (55.05, 14.0),  # przy rogu siatki
        (49.0, 24.15),  # przy granicy wschodniej
    ],
)
def test_points_at_or_beyond_grid_edge_do_not_fail(grid, latitude, longitude):
    assert grid.residents_within([latitude], [longitude]) >= 0


def test_no_devices_no_residents(grid):
    assert grid.residents_within([], []) == 0
    assert grid.residents_for_aed_df(pd.DataFrame(columns=AED_COLUMNS)) == 0


def test_main_report_counts_each_provider_and_poland_once(grid):
    legionowo = demo_accepted("wykaz_aed_legionowo.csv")[AED_COLUMNS]
    result = build_main_aed_df(
        [AEDProviderList("Urząd Miasta Legionowo", "1", legionowo), AEDProviderList("Kopia Legionowa", "2", legionowo)]
    )
    result.add_residents(grid)
    assert result.residents["Urząd Miasta Legionowo"] == result.residents["Kopia Legionowa"]
    assert result.residents_total == result.residents["Urząd Miasta Legionowo"]
    summary = result.summary()
    assert f"mieszka {format_residents(result.residents_total)} osób" in summary
    assert f"{format_residents(result.residents['Kopia Legionowa'])} mieszkańców w promieniu 200 m" in summary


def test_summary_without_grid_has_no_residents():
    result = build_main_aed_df([AEDProviderList("A", "1", demo_accepted("wykaz_aed_krosno.csv")[AED_COLUMNS])])
    assert "mieszkańców" not in result.summary()


def test_format_residents():
    assert format_residents(12797) == "12\u00a0797"
    assert format_residents(480342) == "480\u00a0342"
    assert format_residents(7) == "7"
