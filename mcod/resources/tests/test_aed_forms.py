"""Walidacja pliku wykazu AED w formularzu zasobu (bez bazy danych)."""

from django.core.files.uploadedfile import SimpleUploadedFile

from mcod.resources.aed_constants import AED_COLUMNS
from mcod.resources.forms import ResourceForm


class _FormErrors:
    """Zbiera błędy tak jak ``ResourceForm.add_error``, bez budowania całego formularza."""

    def __init__(self):
        self.errors = []

    def add_error(self, field, error):
        self.errors.append((field, str(error)))


def _aed_csv(**overrides):
    row = {column: "X" for column in AED_COLUMNS}
    row.update(
        id_urzadzenia="AED-1",
        nazwa_miejsca="Szkoła",
        miejscowosc="Marki",
        szerokosc_geograficzna="52.317014",
        dlugosc_geograficzna="21.104131",
    )
    row.update(overrides)
    content = ",".join(AED_COLUMNS) + "\n" + ",".join(row[column] for column in AED_COLUMNS) + "\n"
    return SimpleUploadedFile("wykaz.csv", content.encode("utf-8"), content_type="text/csv")


def test_valid_aed_file_has_no_errors():
    form = _FormErrors()
    ResourceForm._validate_aed_file(form, _aed_csv(), error_field="file")
    assert form.errors == []


def test_rejected_rows_are_listed_with_escaped_cell_values():
    form = _FormErrors()
    payload = "<img src=x onerror=alert(1)>"
    ResourceForm._validate_aed_file(form, _aed_csv(id_urzadzenia=payload, dostep_24h=payload), error_field="file")
    [(field, message)] = form.errors
    assert field == "file"
    assert "<ul><li>" in message
    assert payload not in message
    assert "&lt;img src=x onerror=alert(1)&gt;" in message


def test_errors_go_to_given_field_on_update():
    form = _FormErrors()
    ResourceForm._validate_aed_file(form, _aed_csv(szerokosc_geograficzna="X"), error_field="contains_aed_list")
    assert [field for field, _ in form.errors] == ["contains_aed_list"]


def test_duplicated_columns_give_form_error_not_crash():
    content = ",".join(AED_COLUMNS + ["ID_URZADZENIA"]) + "\n" + ",".join(["X"] * (len(AED_COLUMNS) + 1)) + "\n"
    form = _FormErrors()
    ResourceForm._validate_aed_file(
        form, SimpleUploadedFile("wykaz.csv", content.encode("utf-8"), content_type="text/csv"), error_field="file"
    )
    assert len(form.errors) == 1
    assert "id_urzadzenia" in form.errors[0][1]
