from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from api.common.db import reset_sequences

from api.common.models import User
from ...models import (
    EcgInterpretationRule,
    EcgInterpretationRuleItem,
    AnswerOption,
    HeartDiagnosis,
    Questionnaire,
    Classifier,
)
from ....questionnaire.models import Answer, Option

created_by = User(id=1)
created_at = timezone.now()


class _Template:
    entity = None


class _RuleTemplate(_Template):
    def __init__(self, name, classifier=None, questionnaire=None, details=None):
        self.name = name
        self.details = details
        self.classifier = classifier
        self.questionnaire = questionnaire


class _ItemTemplate(_Template):
    def __init__(self, condition_kind, answer_option, diagnoses, rule, group=None):
        self.condition_kind = condition_kind
        self.answer_option = [answer_option]
        self.diagnoses = diagnoses
        self.rule = rule
        self.group = group


class Command(BaseCommand):
    # noinspection PyMethodMayBeStatic
    def __create_or_update_entity(self, model, id, **kwargs):
        obj, created = model.objects.update_or_create(
            id=id, defaults={"created_by": created_by, "created_at": created_at, **kwargs}
        )
        return obj, created

    rule_index = 1
    item_index = 1
    answer_option_index = 1

    def __create_rule(self, rule_templates):
        result = []
        for rule_template in rule_templates:
            if rule_template.entity is not None:
                result.append((rule_templates.entity, False, rule_templates))
            else:
                rule, o_created = self.__create_or_update_entity(
                    EcgInterpretationRule,
                    self.rule_index,
                    name=rule_template.name,
                    classifier=rule_template.classifier,
                    questionnaire=rule_template.questionnaire,
                )
                result.append((rule, o_created, rule_template))
                rule_template.entity = rule
                self.rule_index += 1
        return result

    def __create_item(self, item_templates):
        result = []
        for item_template in item_templates:
            if item_template.entity is not None:
                result.append((item_templates.entity, False, item_templates))
            else:
                item, o_created = self.__create_or_update_entity(
                    EcgInterpretationRuleItem,
                    self.item_index,
                    condition_kind=item_template.condition_kind,
                    diagnoses=item_template.diagnoses,
                    rule=item_template.rule,
                    group=item_template.group,
                )
                for i in item_template.answer_option:
                    EcgInterpretationRuleItem(id=self.item_index).answer_option.set(i)

                result.append((item, o_created, item_template))
                item_template.entity = item
                self.item_index += 1
        return result

    def handle(self, *args, **options):
        with transaction.atomic():

            def after_commit():
                reset_sequences("ecg")
                reset_sequences("questionnaire")

            transaction.on_commit(after_commit)

            answer_option = EcgInterpretationRuleItem.objects.all()
            answer_option.delete()

            self.__create_rule(
                [
                    _RuleTemplate(
                        name="Правила к пошаговой разметке 12-канальной ЭКГ",
                        questionnaire=Questionnaire(id=1),
                        classifier=Classifier(id=1),
                    ),
                    _RuleTemplate(
                        name="Правила к разметке 12-канальной ЭКГ по 7-ми патологиям (AFIB, STACH, SBRAD, RBBB, LBBB, 1AVB, PVC)",
                        questionnaire=Questionnaire(id=3),
                        classifier=Classifier(id=1),
                    ),
                    _RuleTemplate(
                        name="Правила к разметке 1-канальной ЭКГ по 6-ми патологиям (AFIB, STACH, SBRAD, SARRH, PVC, 1AVB)",
                        questionnaire=Questionnaire(id=4),
                        classifier=Classifier(id=1),
                    ),
                ]
            )

            rule_1 = EcgInterpretationRule(id=1)
            rule_2 = EcgInterpretationRule(id=2)
            rule_3 = EcgInterpretationRule(id=3)

            option_yes = Option.objects.get(id=2).id

            self.__create_item(
                [
                    _ItemTemplate(
                        condition_kind=2,
                        answer_option=[AnswerOption(id=4)],
                        diagnoses=HeartDiagnosis(id=19),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=1,
                        answer_option=[
                            AnswerOption(id=2),
                            AnswerOption(id=1),
                            AnswerOption(id=3),
                        ],
                        diagnoses=HeartDiagnosis(id=11),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=2,
                        group=1,
                        answer_option=[AnswerOption(id=15)],
                        diagnoses=HeartDiagnosis(id=11),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=2,
                        answer_option=[
                            AnswerOption(id=21),
                            AnswerOption(id=22),
                            AnswerOption(id=27),
                            AnswerOption(id=28),
                            AnswerOption(id=29),
                            AnswerOption(id=31),
                            AnswerOption(id=30),
                        ],
                        diagnoses=HeartDiagnosis(id=180),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=2,
                        answer_option=[
                            AnswerOption(id=45),
                            AnswerOption(id=47),
                        ],
                        diagnoses=HeartDiagnosis(id=180),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=3,
                        answer_option=[
                            AnswerOption(id=21),
                            AnswerOption(id=18),
                            AnswerOption(id=27),
                            AnswerOption(id=25),
                            AnswerOption(id=26),
                            AnswerOption(id=31),
                            AnswerOption(id=30),
                        ],
                        diagnoses=HeartDiagnosis(id=118),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=3,
                        answer_option=[
                            AnswerOption(id=46),
                            AnswerOption(id=48),
                        ],
                        diagnoses=HeartDiagnosis(id=118),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=4,
                        answer_option=[
                            AnswerOption(id=1),
                            AnswerOption(id=2),
                            AnswerOption(id=3),
                            AnswerOption(id=8),
                            AnswerOption(id=12),
                        ],
                        diagnoses=HeartDiagnosis(id=81),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=2,
                        group=4,
                        answer_option=[
                            AnswerOption(id=54),
                        ],
                        diagnoses=HeartDiagnosis(id=81),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=4,
                        group=4,
                        answer_option=[
                            AnswerOption(id=34),
                            AnswerOption(id=35),
                        ],
                        diagnoses=HeartDiagnosis(id=81),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=5,
                        answer_option=[
                            AnswerOption(id=1),
                            AnswerOption(id=2),
                            AnswerOption(id=3),
                            AnswerOption(id=4),
                            AnswerOption(id=8),
                            AnswerOption(id=11),
                            AnswerOption(id=12),
                        ],
                        diagnoses=HeartDiagnosis(id=54),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=5,
                        answer_option=[
                            AnswerOption(id=73),
                            AnswerOption(id=74),
                        ],
                        diagnoses=HeartDiagnosis(id=54),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=6,
                        answer_option=[
                            AnswerOption(id=1),
                            AnswerOption(id=2),
                            AnswerOption(id=3),
                        ],
                        diagnoses=HeartDiagnosis(id=80),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=6,
                        answer_option=[AnswerOption(id=34)],
                        diagnoses=HeartDiagnosis(id=80),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=7,
                        answer_option=[
                            AnswerOption(id=1),
                            AnswerOption(id=2),
                            AnswerOption(id=3),
                        ],
                        diagnoses=HeartDiagnosis(id=9),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=1,
                        group=7,
                        answer_option=[AnswerOption(id=16)],
                        diagnoses=HeartDiagnosis(id=9),
                        rule=rule_1,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Фибрилляция предсердий (AFIB)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=19),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Синусовая тахикардия (STACH)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=11),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Синусовая брадикардия (SBRAD)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=9),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Блокада правой ножки пучка Гиса (RBBB, CRBBB, IRBBB)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=180),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Блокада левой ножки пучка Гиса (LBBB, CLBBB, ILBBB)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=118),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="AV-блокада первой степени (1AVB)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=81),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Желудочковая экстрасистола - импульс (PVC)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=54),
                        rule=rule_2,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Фибрилляция предсердий (AFIB)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=19),
                        rule=rule_3,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Синусовая тахикардия (STACH)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=11),
                        rule=rule_3,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Синусовая брадикардия (SBRAD)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=9),
                        rule=rule_3,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Синусовая аритмия (SARRH)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=8),
                        rule=rule_3,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="Желудочковая экстрасистола - импульс (PVC)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=54),
                        rule=rule_3,
                    ),
                    _ItemTemplate(
                        condition_kind=3,
                        answer_option=[
                            AnswerOption.objects.filter(
                                answer__in=Answer.objects.filter(question__text="AV-блокада первой степени (1AVB)"),
                                option=option_yes
                            ).get().id
                        ],
                        diagnoses=HeartDiagnosis(id=81),
                        rule=rule_3,
                    ),
                ]
            )
