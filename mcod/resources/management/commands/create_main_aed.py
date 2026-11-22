from django.core.management.base import BaseCommand

from mcod.resources.tasks.aed import create_main_aed_resource_task


class Command(BaseCommand):
    help = "Tworzy od razu raport zbiorczy wykazów AED (bez czekania na harmonogram Celery)."

    def handle(self, *args, **options):
        summary = create_main_aed_resource_task.apply().get()
        self.stdout.write(summary)
