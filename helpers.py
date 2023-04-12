import threading

from django.db.models import BigIntegerField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import NotFound

from api.common.models import Direction
from api.common.threading import lock_on
from api.questionnaire.models import AnswerOption, QuestionnaireResult
from api.tasks.models import Task
from api.tasks.task_types.questionnaire_task.models import QuestionnaireTaskEcgResult
from .models import (
    Electrocardiogram,
    ElectrocardiogramSet,
    EcgResultInterpretation,
    EcgInterpretationRuleItem,
    EcgInterpretationRule,
    EcgInterpretation,
)


class ECGSetHelper:
    class NextEcgResult:
        def __init__(
            self, ecg, index, len_total, len_available, first_available_index, last_available_index, is_first, is_last
        ):
            self.ecg = ecg
            self.index = index
            self.len_total = len_total
            self.len_available = len_available
            self.fist_available_index = first_available_index
            self.last_available_index = last_available_index
            self.is_first = is_first
            self.is_last = is_last

    @staticmethod
    def get_next_prev_ecg(
        ecg_set, user_set, direction, ecg_id=None, unavailable_ids=None, is_first_strategy=None, is_last_strategy=None
    ):
        """
        Определение ЭКГ следующей по в заданном направлении в наборе

        :param ElectrocardiogramSet ecg_set: набор ЭКГ
        :param ElectrocardiogramSetUserOrder user_set: пользовательская сортировка набора ЭКГ
        :param Direction direction: направление поиска
        :param int ecg_id: идентификатор ЭКГ, с которого начинать поиск
        :param list unavailable_ids: список идентификаторов ЭКГ, которые должны пропускаться при поиске
        :param function is_first_strategy: метод-стратегия определения, является ли ЭКГ первой в наборе. (По умолчанию: первая из доступных)
        :param function is_last_strategy: метод-стратегия определения, является ли ЭКГ последней в наборе. (По умолчанию: последняя из доступных)
        :rtype: ECGSetHelper.NextEcgResult
        :raises NotFound:
        """

        if ecg_set.ordering_type == "1" and user_set.order != "3":
            el_set = ecg_set.electrocardiogram_ids
        else:
            el_set = user_set.electrocardiogram_ids

        next_id, next_index, first_available_index, last_available_index = ECGSetHelper._get_next_prev_id(
            el_set, direction, ecg_id, unavailable_ids
        )

        len_total = len(el_set)
        len_available = len(set(el_set) - set(unavailable_ids))

        if is_first_strategy is not None:
            is_first = is_first_strategy(
                el_set, direction, next_index, len_total, len_available, first_available_index, last_available_index
            )
        else:
            is_first = next_index == first_available_index

        if is_last_strategy is not None:
            is_last = is_last_strategy(
                el_set, direction, next_index, len_total, len_available, first_available_index, last_available_index
            )
        else:
            is_last = next_index == last_available_index

        next_ecg = Electrocardiogram.objects_fully_prefetched.get(id=next_id)

        return ECGSetHelper.NextEcgResult(
            next_ecg,
            next_index,
            len_total,
            len_available,
            first_available_index,
            last_available_index,
            is_first,
            is_last,
        )

    @staticmethod
    def _get_next_prev_id(ids, direction, from_id=None, unavailable_ids=None):
        """
        Поиск следующего доступного идентификатора в наборе в заданном направлении
        """
        if unavailable_ids is None:
            unavailable_ids = []
        unavailable_ids = set(unavailable_ids)

        first_available_index = None
        last_available_index = ECGSetHelper._get_last_available_index(ids, unavailable_ids)

        len_el = len(ids)

        if from_id is None:
            from_id = ids[0]

        for curr_index in range(0, len(ids)):
            curr_id = ids[curr_index]
            if first_available_index is None and curr_id not in unavailable_ids:
                first_available_index = curr_index

            if curr_id == from_id:
                from_index = curr_index
                break
        else:
            raise NotFound("from id is not in set")

        if direction == Direction.NEXT:
            if from_index == len_el - 1:
                raise NotFound("from id is last in set")
            else:
                for i in range(from_index + 1, len_el):
                    next_id = ids[i]
                    if next_id not in unavailable_ids:
                        next_index = i
                        break
                else:
                    raise NotFound("next available id not found")

        elif direction == Direction.PREV:
            if from_index == 0:
                raise NotFound("from id is first in set")
            else:
                for i in range(from_index - 1, -1, -1):
                    next_id = ids[i]
                    if next_id not in unavailable_ids:
                        next_index = i
                        break
                else:
                    raise NotFound("prev available id not found")
        else:
            raise NotFound("Direction is not correct")

        return next_id, next_index, first_available_index, last_available_index

    @staticmethod
    def get_ecg_index(ecg_set, user_set, ecg_id=None):

        if ecg_set.ordering_type == "1" and user_set.order != "3":
            el_set = ecg_set.electrocardiogram_ids
        else:
            el_set = user_set.electrocardiogram_ids

        len_el = len(el_set)

        if ecg_id is None:
            el_index = 0
        else:
            el_index = el_set.index(ecg_id)
            if el_index < 0:
                raise NotFound("current ecg not in set")

        is_first = el_index == 0
        is_last = el_index == len_el - 1

        ecg = Electrocardiogram.objects_fully_prefetched.get(id=el_set[el_index])

        return el_index, len_el, is_first, is_last, ecg

    @staticmethod
    def get_first_available_ecg(ecg_set, user_set, unavailable_ids=None):
        if unavailable_ids is None:
            unavailable_ids = []

        unavailable_ids = set(unavailable_ids)

        if ecg_set.ordering_type == "1" and user_set.order != "3":
            ecg_ids = ecg_set.electrocardiogram_ids
        else:
            ecg_ids = user_set.electrocardiogram_ids

        last_available_ecg_index = ECGSetHelper._get_last_available_index(ecg_ids, unavailable_ids)

        for i in range(0, len(ecg_ids)):
            ecg_id = ecg_ids[i]
            if ecg_id not in unavailable_ids:
                ecg = Electrocardiogram.objects_fully_prefetched.get(id=ecg_id)
                return ecg, i, len(ecg_ids), last_available_ecg_index
        else:
            raise NotFound("there is no available ecg in set")

    @staticmethod
    def _get_last_available_index(ids, unavailable_ids):
        for backward_index in range(len(ids) - 1, -1, -1):
            ecg_id = ids[backward_index]
            if ecg_id not in unavailable_ids:
                last_available_ecg_index = backward_index
                return last_available_ecg_index
        else:
            raise NotFound("available index not found")


def leads_splitter_generator(content_with_leads):
    if "leads" not in content_with_leads:
        raise StopIteration

    while len(content_with_leads["leads"]) > 0:
        yield {"leads": [content_with_leads["leads"].pop(0)]}


def leads_to_two_dimensional_array(leads_list):
    if len(leads_list) == 0:
        return []

    max_lead_samples_length = 0

    for lead in leads_list:
        if len(lead["samples"]) > max_lead_samples_length:
            max_lead_samples_length = len(lead["samples"])

    samples_arrs = []
    for lead in leads_list:
        samples = lead["samples"]
        if len(samples) < max_lead_samples_length:
            # NOTE: align samples length to max lead samples length
            samples = samples + [0] * (max_lead_samples_length - len(samples))

        samples_arrs.append(samples)

    return samples_arrs


interpretation_result_lock = threading.Lock()


class ECGInterpretationHelper:
    @lock_on(interpretation_result_lock)
    def interpretation_result(self, rule_id, result_id):
        result = get_object_or_404(QuestionnaireResult, pk=result_id)
        rule = get_object_or_404(EcgInterpretationRule, pk=rule_id)

        try:
            exist_interpretation = EcgResultInterpretation.objects.get(rule_id=rule_id, result_id=result_id)

            result_time = result.created_at
            if result.updated_at:
                result_time = result.updated_at
            exist_interpretation_time = exist_interpretation.created_at
            if exist_interpretation.updated_at:
                exist_interpretation_time = exist_interpretation.updated_at

            update_flag = result_time > exist_interpretation_time

            if update_flag is False:
                return exist_interpretation
            else:
                return ECGInterpretationHelper.update_interpretation(self, result, rule, exist_interpretation)
        except EcgResultInterpretation.DoesNotExist:
            return ECGInterpretationHelper.create_interpretation(self, result, rule)

    def create_interpretation(self, result, rule):

        rules = EcgInterpretationRuleItem.objects.filter(rule_id=rule.id)
        groups = [item.group for item in rules]
        groups = set(groups)
        groups.add(None)

        diagnoses_sucses = ECGInterpretationHelper.interpretation_calc_diagnoses(result, rules, groups)

        interpretation_map = {}
        interpretation_map["rule"] = rule
        interpretation_map["result"] = result
        interpretation_map["created_by"] = self.request.user
        interpretation_map["created_at"] = timezone.now()

        interpretation = EcgResultInterpretation.objects.create(**interpretation_map)  # , created_by=self., created_at=
        interpretation.diagnoses.set(diagnoses_sucses)

        ecg_id = QuestionnaireTaskEcgResult.objects.get(result=result.id)
        interpretation_map.pop("rule")
        interpretation_map.pop("result")

        interpretation_map["ecg"] = ecg_id.ecg
        interpretation_map["source"] = "system"  # Можно поменять
        interpretation_map["result_interpretation"] = interpretation

        interpretation_ecg = EcgInterpretation.objects.create(**interpretation_map)
        interpretation_ecg.diagnoses.set(diagnoses_sucses)

        return interpretation

    def update_interpretation(self, result, rule, exist_interpretetion, force_update=False):

        rules = EcgInterpretationRuleItem.objects.filter(rule_id=rule.id)
        groups = [item.group for item in rules]
        groups = set(groups)
        groups.add(None)

        diagnoses_sucses = ECGInterpretationHelper.interpretation_calc_diagnoses(result, rules, groups)

        exist_interpretetion.updated_at = timezone.now()
        exist_interpretetion.updated_by = self.request.user
        exist_interpretetion.save()
        exist_interpretetion.diagnoses.set(diagnoses_sucses)

        update_inter_ecg = EcgInterpretation.objects.get(result_interpretation=exist_interpretetion.id)
        update_inter_ecg_map = {}
        update_inter_ecg_map["updated_at"] = exist_interpretetion.updated_at
        update_inter_ecg_map["updated_by"] = exist_interpretetion.updated_by

        EcgInterpretation.objects.update(**update_inter_ecg_map)
        update_inter_ecg.diagnoses.set(diagnoses_sucses)

        return exist_interpretetion

    def interpretation_calc_diagnoses(result, rules, groups):

        result_map = []
        condition = []
        diagnoses_in_group = []
        diagnoses_sucses = []
        condition_none = []

        for question in result.data["questions"]:
            if "answers" not in question or len(question["answers"]) == 0:
                continue

            for answer in question["answers"]:
                options = []
                if "options" in answer and len(answer["options"]) > 0:
                    options = answer["options"]

                answer_options = AnswerOption.objects.filter(answer_id=answer["id"], option_id__in=options)
                if answer_options:
                    for answer_option in answer_options:
                        result_map.append(answer_option.id)

        for group in list(groups):
            for item in rules:
                if item.group == group and item.group is not None:
                    condition.append((item.answer_option.all(), item.diagnoses, item.condition_kind))

                elif group is None and item.group is None:
                    condition_none.append((item.answer_option.all(), item.diagnoses, item.condition_kind))

            if len(condition) > 0:
                for (answer_option, diag, kind) in condition:
                    flag_or = False
                    deсision = False
                    flag_not_in = False
                    decision_and = []
                    for answer_opt_cond in answer_option:
                        for answer_option_res in result_map:
                            if answer_opt_cond.id == answer_option_res:
                                deсision = True
                                if kind == 1:
                                    flag_or = True
                                elif kind == 2:
                                    decision_and.append(True)
                                elif kind == 4:
                                    flag_not_in = True
                                break
                    if kind == 2 and len(decision_and) == len(answer_option):
                        diagnoses_in_group.append((True, kind, diag, flag_or, flag_not_in))
                    else:
                        diagnoses_in_group.append((deсision, kind, diag, flag_or, flag_not_in))

            for deсision, kind, diag, flag_or, flag_not_in in diagnoses_in_group:
                if deсision and kind != 4:
                    pass
                elif flag_or and kind == 1:
                    pass
                elif kind == 4 and deсision is False and flag_not_in is False:
                    pass
                elif kind == 4 and (deсision or flag_not_in):
                    diagnoses_in_group = []
                else:
                    diagnoses_in_group = []

            if len(condition_none) > 0:  # special for group None
                for (answer_option, diag, kind) in condition_none:
                    flag_not_in = False
                    decision_map = []
                    for answer_opt_cond in answer_option:
                        for answer_option_res in result_map:
                            if answer_opt_cond.id == answer_option_res:
                                if kind == 1 or kind == 3:
                                    diagnoses_sucses.append(diag)
                                elif kind == 2:
                                    decision_map.append(True)
                                elif kind == 4:
                                    flag_not_in = True
                                break
                    else:
                        if kind == 4 and flag_not_in is False:
                            diagnoses_sucses.append(diag)
                    if kind == 2 and len(decision_map) == len(answer_option):
                        diagnoses_sucses.append(diag)

            if len(diagnoses_in_group) > 0:  # special for group
                for deсision, kind, diag, flag_or, flag_not_in in diagnoses_in_group:
                    diagnoses_sucses.append(diag)

            condition = []
            diagnoses_in_group = []
            condition_none = []

        diagnoses_sucses = set(diagnoses_sucses)
        return list(diagnoses_sucses)


class ECGTaskHelper:
    @staticmethod
    def enrich_ecg_with_task_count_field(ecg_queryset):
        ecg_sets = ElectrocardiogramSet.objects.filter(
            electrocardiograms__in=ecg_queryset,
            id__in=Task.objects.all().values(cast_id=Cast("properties__ecg_set", output_field=BigIntegerField())),
        ).distinct("id")

        ecg_array = []
        result_map = {}
        for ecg_set in ecg_sets:
            ecg_array.extend(ecg_set.electrocardiogram_ids)

        for ecg_id in ecg_array:
            result_map[ecg_id] = result_map.get(ecg_id, 0) + 1

        for ecg in ecg_queryset:
            if result_map.get(ecg.id):
                ecg.task_count = result_map[ecg.id]
            else:
                ecg.task_count = 0
        return ecg_queryset
