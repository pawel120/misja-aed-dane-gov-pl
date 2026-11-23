"""Dane dla strony konwertera AED w panelu (``ResourceAdmin.aed_converter_view``)."""

import base64
import os
from typing import Any, Dict, List

from mcod.resources.aed_constants import AED_FORM_MAX_SHOWN_ISSUES
from mcod.resources.aed_convert import SPECIAL_TARGET_LABELS, convert_to_aed
from mcod.resources.aed_validation import format_residents, read_aed_file, validate_aed_df

# Plik wynikowy idzie do przeglądarki w linku data:, więc trzymamy rozsądny limit.
AED_CONVERTER_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
AED_CONVERTER_EXTENSIONS = ("csv", "xls", "xlsx")
AED_CONVERTER_PREVIEW_COLUMNS = [
    "id_urzadzenia",
    "nazwa_miejsca",
    "cecha_ulicy",
    "nazwa_ulicy",
    "nr_budynku",
    "kod_pocztowy",
    "miejscowosc",
    "szerokosc_geograficzna",
    "dlugosc_geograficzna",
]
AED_CONVERTER_PREVIEW_ROWS = 10


def build_aed_converter_context(upload) -> Dict[str, Any]:
    """Konwertuje wgrany plik i zwraca to, co pokazuje strona: zmiany, walidację, podgląd i plik do pobrania."""
    name = os.path.basename(getattr(upload, "name", "") or "wykaz")
    extension = os.path.splitext(name)[1].lower().lstrip(".")
    if extension not in AED_CONVERTER_EXTENSIONS:
        return {"error": "Konwerter przyjmuje pliki csv, xls i xlsx."}
    if getattr(upload, "size", 0) > AED_CONVERTER_MAX_UPLOAD_BYTES:
        return {"error": "Plik jest większy niż 5 MB. Podziel wykaz na mniejsze pliki."}
    try:
        df = read_aed_file(upload, extension)
    except Exception:
        return {"error": "Nie udało się odczytać tabeli z pliku. Sprawdź, czy to csv, xls albo xlsx z nagłówkiem."}

    conversion = convert_to_aed(df)
    validation = validate_aed_df(conversion.df)
    mapping: List[Dict[str, str]] = [
        {"source": source, "target": SPECIAL_TARGET_LABELS.get(target, target)}
        for source, target in conversion.mapping.items()
    ]
    preview = conversion.df[AED_CONVERTER_PREVIEW_COLUMNS].head(AED_CONVERTER_PREVIEW_ROWS)
    context: Dict[str, Any] = {
        "file_name": name,
        "rows_total": len(conversion.df),
        "mapping": mapping,
        "changes": conversion.changes,
        "accepted_count": validation.accepted_count,
        "rejected_count": validation.rejected_count,
        "rejected": validation.rejected[:AED_FORM_MAX_SHOWN_ISSUES],
        "rejected_more": max(validation.rejected_count - AED_FORM_MAX_SHOWN_ISSUES, 0),
        "preview_columns": AED_CONVERTER_PREVIEW_COLUMNS,
        "preview_rows": preview.values.tolist(),
        "download_name": f"{os.path.splitext(name)[0]}_wzorzec_AED.csv",
        "download_data": base64.b64encode(conversion.to_csv_bytes()).decode("ascii"),
    }
    try:
        from mcod.resources.aed_utils import count_aed_residents

        residents = count_aed_residents(validation.accepted)
    except Exception:
        residents = None
    if residents is not None:
        context["residents"] = format_residents(residents)
    return context
