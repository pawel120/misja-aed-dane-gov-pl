import logging

from mcod.core.tasks import extended_shared_task
from mcod.resources.aed_utils import create_main_aed_file, publish_main_aed_resource

logger = logging.getLogger("mcod")


@extended_shared_task(
    atomic=False,
    name="mcod.resources.tasks.create_main_aed_resource_task",
)
def create_main_aed_resource_task() -> str:
    """
    Skleja opublikowane wykazy AED instytucji w raport zbiorczy i publikuje go
    jako zasób zbioru „Wykaz defibrylatorów AED – raport zbiorczy”.
    Zwraca podsumowanie: ile AED od ilu dostawców, ile wierszy odrzucono i dlaczego.
    """
    logger.info("Starting main AED resource creation.")
    file_path, result = create_main_aed_file()
    resource = publish_main_aed_resource(file_path)
    try:
        file_path.unlink()
    except OSError as exc:
        logger.warning("Cannot remove temporary main AED file %s: %s", file_path, exc)
    summary = result.summary()
    logger.info("Main AED resource %s published. %s", resource.pk, summary)
    return summary
