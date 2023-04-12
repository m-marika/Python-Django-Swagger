from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from api.common.db import reset_sequences

from api.common.models import User
from ...models import Classifier

created_by = User(id=1)
created_at = timezone.now()


class _Template:
    entity = None


class _ClassifierTemplate(_Template):
    def __init__(self, name, details=None):
        self.name = name
        self.details = details


class Command(BaseCommand):
    # noinspection PyMethodMayBeStatic
    def __create_or_update_entity(self, model, id, **kwargs):
        obj, created = model.objects.update_or_create(
            id=id, defaults={"created_by": created_by, "created_at": created_at, **kwargs}
        )
        return obj, created

    classifier_index = 1

    def __create_classifier(self, classifier_templates):
        result = []
        for classifier_template in classifier_templates:
            if classifier_template.entity is not None:
                result.append((classifier_templates.entity, False, classifier_templates))
            else:
                pathology, o_created = self.__create_or_update_entity(
                    Classifier,
                    self.classifier_index,
                    name=classifier_template.name,
                )
                result.append((pathology, o_created, classifier_template))
                classifier_template.entity = pathology
                self.classifier_index += 1
        return result

    def handle(self, *args, **options):
        with transaction.atomic():

            def after_commit():
                reset_sequences("ecg")

            transaction.on_commit(after_commit)

            self.__create_classifier(
                [
                    _ClassifierTemplate(name="SCP"),
                    _ClassifierTemplate(name="TIS"),
                ]
            )
