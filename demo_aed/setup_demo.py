"""
Dane demo wykazu AED w lokalnym portalu (HackNation 2026).

Uruchomienie w kontenerze aplikacji:
    python manage.py shell < demo_aed/setup_demo.py

Tworzy:
- konto administratora (login z AED_DEMO_ADMIN_EMAIL, hasło z AED_DEMO_ADMIN_PASSWORD),
- instytucję „Ministerstwo Cyfryzacji” (właściciel raportu zbiorczego, pk z
  MAIN_AED_DATASET_OWNER_ORGANIZATION_PK),
- 4 instytucje z prawdziwymi wykazami AED na otwartej licencji (CC0 / CC BY)
  i 1 instytucję testową z wykazem z błędami,
- dla każdej: zbiór „Defibrylatory AED” i zasób z flagą „wykaz AED”.

Skrypt można uruchamiać wielokrotnie: istniejące obiekty są pomijane.
Zasoby wgrywa jak dostawca (pliki przechodzą zwykłe walidacje portalu w Celery),
z pominięciem formularza: wykaz testowy z błędami trafia do portalu, a raport
zbiorczy go odfiltrowuje.
"""

import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from mcod.categories.models import Category
from mcod.datasets.models import Dataset
from mcod.organizations.models import Organization
from mcod.resources.models import Resource, ResourceFile

DANE = Path(settings.BASE_DIR if hasattr(settings, "BASE_DIR") else ".") / "demo_aed" / "dane"
if not DANE.exists():
    DANE = Path("/usr/src/mcod_backend/demo_aed/dane")

DOSTAWCY = [
    # (plik, nazwa instytucji, typ, REGON, licencja zbioru)
    ("wykaz_aed_legionowo.csv", "Urząd Miasta Legionowo", "local", "000524832", "CC0 1.0"),
    ("wykaz_aed_krosno.csv", "Urząd Miasta Krosna", "local", "000526989", "CC0 1.0"),
    ("wykaz_aed_przemysl.csv", "Urząd Miejski w Przemyślu", "local", "650900341", "CC0 1.0"),
    ("wykaz_aed_warszawa.csv", "Urząd m.st. Warszawy", "local", "015259640", "CC BY 4.0"),
    ("wykaz_aed_testowy_z_bledami.csv", "Fundacja Przykładowa (dane testowe)", "other", "", "CC0 1.0"),
]

User = get_user_model()
email = os.environ.get("AED_DEMO_ADMIN_EMAIL", "admin@aed.demo")
password = os.environ["AED_DEMO_ADMIN_PASSWORD"]
admin = User.objects.filter(email=email).first()
if not admin:
    admin = User.objects.create_superuser(email=email, password=password)
    print(f"Utworzono administratora {email}")
admin.is_staff = True
admin.is_superuser = True
admin.state = "active"
admin.save()

owner_pk = int(settings.MAIN_AED_DATASET_OWNER_ORGANIZATION_PK)
mc = Organization.raw.filter(pk=owner_pk).first()
if not mc:
    mc = Organization.objects.create(
        pk=owner_pk,
        title="Ministerstwo Cyfryzacji",
        slug="ministerstwo-cyfryzacji",
        institution_type="state",
        regon="147124734",
        status="published",
    )
    print(f"Utworzono instytucję {mc.title} (pk={mc.pk})")

category = Category.objects.filter(title__in=settings.MAIN_AED_DATASET_CATEGORIES_TITLES).first()
if not category:
    category = Category.objects.create(title=settings.MAIN_AED_DATASET_CATEGORIES_TITLES[0], code="HEAL", status="published")
    print(f"Utworzono kategorię {category.title}")

for plik, nazwa, typ, regon, licencja in DOSTAWCY:
    organization = Organization.raw.filter(title=nazwa).first()
    if not organization:
        organization = Organization.objects.create(
            title=nazwa,
            slug=nazwa.lower().replace(" ", "-").replace(".", "")[:90],
            institution_type=typ,
            regon=regon or None,
            status="published",
        )
        organization.users.add(admin)
        print(f"Utworzono instytucję {nazwa}")

    dataset = Dataset.raw.filter(organization=organization, title="Defibrylatory AED").first()
    if not dataset:
        dataset = Dataset.objects.create(
            title="Defibrylatory AED",
            notes=f"Wykaz automatycznych defibrylatorów zewnętrznych (AED), za które odpowiada {nazwa}. Licencja: {licencja}.",
            organization=organization,
            has_dynamic_data=False,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            update_frequency="monthly",
            status="published",
        )
        dataset.categories.set([category])
        print(f"Utworzono zbiór {nazwa}: {dataset.title}")

    if Resource.raw.filter(dataset=dataset, contains_aed_list=True).exists():
        continue
    resource = Resource.objects.create(
        title=f"Wykaz AED – {nazwa}",
        description=f"Aktualny wykaz defibrylatorów AED: {nazwa}. Kolumny zgodne ze wzorcowym zakresem danych o AED.",
        dataset=dataset,
        has_dynamic_data=False,
        has_high_value_data=False,
        has_high_value_data_from_ec_list=False,
        has_research_data=False,
        contains_aed_list=True,
        status="published",
    )
    content = (DANE / plik).read_bytes()
    ResourceFile.objects.create(
        resource=resource, is_main=True, file=SimpleUploadedFile(name=plik, content=content, content_type="text/csv")
    )
    print(f"Wgrano zasób {resource.pk}: {resource.title}")

print("Gotowe. Status walidacji zasobów: Resource.raw.filter(contains_aed_list=True).values_list('pk', 'file_tasks_last_status', 'data_tasks_last_status', 'link_tasks_last_status')")
