"""
Zbiorczy wykaz defibrylatorów AED (Main AED), na wzór wykazu DGA.

1. Każda instytucja publikuje własny zasób oznaczony jako „wykaz AED”
   (``Resource.contains_aed_list``) i odpowiada za jego treść.
2. Raz na dobę zadanie ``create_main_aed_resource_task`` zbiera opublikowane
   wykazy, które przeszły walidację portalu, sprawdza je walidacjami AED
   (``aed_validation.py``) i skleja w jeden raport zbiorczy.
3. Raport jest publikowany jako zasób zbioru „Wykaz defibrylatorów AED – raport
   zbiorczy” instytucji z ``MAIN_AED_DATASET_OWNER_ORGANIZATION_PK``
   (domyślnie ta sama, co raport DGA: Ministerstwo Cyfryzacji).
"""

import datetime
import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.models import QuerySet

from mcod.resources.aed_constants import ALLOWED_AED_INSTITUTIONS
from mcod.resources.aed_validation import AEDProviderList, MainAEDResult, build_main_aed_df, read_aed_file

logger = logging.getLogger("mcod")


def get_main_aed_dataset() -> Optional["Dataset"]:  # noqa: F821
    Dataset = apps.get_model("datasets", "Dataset")
    return (
        Dataset.objects.filter(
            organization_id=settings.MAIN_AED_DATASET_OWNER_ORGANIZATION_PK,
            title=settings.MAIN_AED_DATASET_DEFAULT_TITLE,
        )
        .order_by("pk")
        .first()
    )


def is_aed_resource(resource: "Resource") -> bool:  # noqa: F821
    """Wykaz AED dostawcy albo raport zbiorczy: oba mają kolumny wzorca AED."""
    if resource.contains_aed_list:
        return True
    dataset = resource.dataset
    return bool(
        dataset
        and dataset.title == settings.MAIN_AED_DATASET_DEFAULT_TITLE
        and str(dataset.organization_id) == str(settings.MAIN_AED_DATASET_OWNER_ORGANIZATION_PK)
    )


def get_all_aed_resources_sorted_by_organizations() -> QuerySet:
    """Opublikowane wykazy AED, które przeszły walidację pliku, danych i linku."""
    Resource = apps.get_model("resources", "Resource")
    main_dataset = get_main_aed_dataset()
    resources = Resource.objects.filter(
        contains_aed_list=True,
        status="published",
        data_tasks_last_status="SUCCESS",
        file_tasks_last_status="SUCCESS",
        link_tasks_last_status="SUCCESS",
        dataset__organization__institution_type__in=ALLOWED_AED_INSTITUTIONS,
    )
    if main_dataset:
        resources = resources.exclude(dataset=main_dataset)
    return resources.select_related("dataset__organization").order_by("dataset__organization__title", "pk")


def read_aed_resource_df(resource: "Resource") -> Optional[pd.DataFrame]:  # noqa: F821
    main_file = resource.main_file
    if not main_file:
        logger.error("Skipping AED resource %s: no main file.", resource.pk)
        return None
    extension = os.path.splitext(main_file.name)[1]
    try:
        with main_file.open("rb") as file:
            return read_aed_file(file, extension)
    except Exception as exc:
        logger.error("Skipping AED resource %s: cannot read file (%s).", resource.pk, exc)
        return None


def collect_aed_provider_lists(resources: QuerySet) -> List[AEDProviderList]:
    lists: List[AEDProviderList] = []
    for resource in resources:
        df = read_aed_resource_df(resource)
        if df is None:
            continue
        organization = resource.institution
        lists.append(AEDProviderList(organization.title, organization.regon or "", df))
    return lists


def get_main_aed_path() -> Path:
    directory = Path(settings.MAIN_AED_RESOURCE_FILE_CREATION_ROOT)
    directory.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y%m%d")
    return directory / f"{settings.MAIN_AED_FILE_NAME_PREFIX} {today}.csv"


def create_main_aed_file() -> Tuple[Path, MainAEDResult]:
    """Tworzy plik CSV (UTF-8) raportu zbiorczego i zwraca go razem z podsumowaniem walidacji."""
    resources = get_all_aed_resources_sorted_by_organizations()
    result = build_main_aed_df(collect_aed_provider_lists(resources))
    logger.info("Main AED: %s", result.summary())
    file_path = get_main_aed_path()
    result.main_df.to_csv(file_path, index=False, encoding="utf-8")
    return file_path, result


def get_or_create_main_aed_dataset() -> "Dataset":  # noqa: F821
    dataset = get_main_aed_dataset()
    if dataset:
        return dataset
    Organization = apps.get_model("organizations", "Organization")
    Dataset = apps.get_model("datasets", "Dataset")
    Category = apps.get_model("categories", "Category")
    Tag = apps.get_model("tags", "Tag")
    institution = Organization.objects.get(pk=settings.MAIN_AED_DATASET_OWNER_ORGANIZATION_PK)
    with transaction.atomic():
        dataset = Dataset.objects.create(
            title=settings.MAIN_AED_DATASET_DEFAULT_TITLE,
            notes=settings.MAIN_AED_DATASET_DEFAULT_DESC,
            organization=institution,
            update_notification_recipient_email=settings.MAIN_AED_DATASET_UPDATE_NOTIFICATION_EMAIL,
            has_dynamic_data=False,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            update_frequency="daily",
            status="published",
        )
        dataset.categories.set(Category.objects.filter(title__in=settings.MAIN_AED_DATASET_CATEGORIES_TITLES))
        pl_lang = settings.LANGUAGES[0][0]
        dataset.tags.set(
            [Tag.objects.get_or_create(name=name, language=pl_lang)[0] for name in settings.MAIN_AED_DATASET_TAGS_NAMES]
        )
        dataset.save()
    logger.info("Created main AED dataset %s.", dataset.pk)
    return dataset


def publish_main_aed_resource(file_path: Path) -> "Resource":  # noqa: F821
    """
    Publikuje nowy zasób raportu zbiorczego i usuwa poprzedni. Zapis pliku
    uruchamia zwykłe walidacje portalu (plik, dane, widok tabelaryczny).
    """
    Resource = apps.get_model("resources", "Resource")
    ResourceFile = apps.get_model("resources", "ResourceFile")
    dataset = get_or_create_main_aed_dataset()
    old_resources = list(Resource.objects.filter(dataset=dataset))
    with transaction.atomic(), open(file_path, "rb") as file:
        resource = Resource.objects.create(
            title=settings.MAIN_AED_RESOURCE_DEFAULT_TITLE,
            description=settings.MAIN_AED_RESOURCE_DEFAULT_DESC,
            dataset=dataset,
            has_dynamic_data=False,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            status="published",
            data_date=datetime.date.today(),
        )
        django_file = SimpleUploadedFile(name=os.path.basename(file.name), content=file.read(), content_type="text/csv")
        ResourceFile.objects.create(resource=resource, is_main=True, file=django_file)
    for old in old_resources:
        old.delete()
        logger.info("Previous main AED resource %s deleted.", old.pk)
    logger.info("Published main AED resource %s.", resource.pk)
    return resource
