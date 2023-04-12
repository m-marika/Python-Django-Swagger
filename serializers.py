from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import empty

from api.common.serializers import CreateUpdateSerializerHelper as Helper
from api.common.serializers import UserSerializer, UserGroupSerializer, CaslJsRawRuleSerializer
from api.questionnaire.serializers import QuestionnaireListSerializer
from api.storage.serializers import FileSerializer, ImageSerializer
from api.tasks.models import Task
from .models import (
    Classifier,
    Diagnosis,
    Patient,
    Eos,
    Electrocardiogram,
    Report,
    HeartDiagnosis,
    ElectrocardiogramSet,
    ElectrocardiogramSetUserOrder,
    ElectrocardiogramSetOrderingField,
    EcgInterpretationRule,
    EcgInterpretationRuleItem,
    EcgResultInterpretation,
    EcgInterpretation,
    EcgDiagnosesPredictionExternalModel,
    EcgType,
)


"""
Diagnoses
"""


class DiagnosesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        exclude = ["updated_by", "is_deleted"]


"""
Patients
"""


class PatientsSerializer(serializers.ModelSerializer):
    gender = serializers.CharField(source="get_gender_display")

    class Meta:
        model = Patient
        exclude = ["updated_by", "is_deleted"]


"""
eos
"""


class EosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eos
        exclude = ["updated_by", "is_deleted"]


class EosNotRequiredSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=255, required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True, required=False)

    class Meta:
        model = Eos
        exclude = ["updated_by", "is_deleted"]


"""
classifier
"""


class ClassifierSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, required=False)

    class Meta:
        model = Classifier
        exclude = ["updated_by", "is_deleted"]


"""
Heart_diagnoses
"""


class Heart_diagnosesSerializer(serializers.ModelSerializer):
    сlassifier = ClassifierSerializer(read_only=True, required=False)
    scp = serializers.CharField(source="code")  # TODO убрать после изменения фронта

    class Meta:
        model = HeartDiagnosis
        exclude = ["updated_by", "is_deleted"]


class Heart_diagnosesNotRequiredSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=255, required=False)
    code = serializers.CharField(max_length=255, required=False)
    сlassifier = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    scp = serializers.CharField(source="code")  # TODO убрать после изменения фронта

    class Meta:
        model = HeartDiagnosis
        exclude = ["updated_by", "is_deleted"]


class QuestionnaireInterpretationRuleSerializer(serializers.ModelSerializer):
    classifier = ClassifierSerializer(read_only=True, required=False)

    class Meta:
        model = EcgInterpretationRule
        exclude = ["updated_by", "is_deleted"]


class QuestionnaireInterpretationRuleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcgInterpretationRuleItem
        exclude = ["updated_by", "is_deleted"]


class QuestionnaireResultInterpretationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcgResultInterpretation
        exclude = ["updated_by", "is_deleted"]


class QuestionnaireResultInterpretationCalcSerializer(serializers.ModelSerializer):
    rule = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    result = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    diagnoses = Heart_diagnosesNotRequiredSerializer(read_only=True, required=False, many=True)

    class Meta:
        model = EcgResultInterpretation
        exclude = ["updated_by", "is_deleted"]


class EcgInterpretationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcgInterpretation
        exclude = ["updated_by", "is_deleted"]


"""
electrocardiograms
"""


class ReportsForELWithHeartsSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    electrocardiogram = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    comment = serializers.CharField(required=False)
    result = serializers.CharField(required=False)
    pq = serializers.FloatField(required=False)
    eos = EosSerializer(read_only=True, required=False)
    aqrs_invalid = serializers.BooleanField(required=False)
    has_artifacts = serializers.BooleanField(required=False)
    heart_rate = serializers.CharField(max_length=255, required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    heart_diagnoses = Heart_diagnosesNotRequiredSerializer(required=False, many=True, read_only=True)

    class Meta:
        model = Report
        exclude = ["updated_by", "is_deleted"]
        depth = 1


class ReportsForELSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)
    electrocardiogram = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    comment = serializers.CharField(required=False)
    result = serializers.CharField(required=False)
    pq = serializers.FloatField(required=False)
    eos = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    aqrs_invalid = serializers.BooleanField(required=False)
    has_artifacts = serializers.BooleanField(required=False)
    heart_rate = serializers.CharField(max_length=255, required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True, required=False)

    class Meta:
        model = Report
        exclude = ["updated_by", "heart_diagnoses", "is_deleted"]
        depth = 1


class ElectrocardiogramsReportsListSerializer(serializers.ModelSerializer):
    electrocardiogram = serializers.IntegerField(source="electrocardiogram.id")
    gender = serializers.CharField(source="electrocardiogram.gender")
    age = serializers.IntegerField(source="electrocardiogram.age")
    p = serializers.FloatField(source="electrocardiogram.p")
    pq = serializers.FloatField(source="electrocardiogram.pq")
    qrs = serializers.CharField(source="electrocardiogram.qrs")
    qt = serializers.IntegerField(source="electrocardiogram.qt")
    rr_best_qrs = serializers.FloatField(source="electrocardiogram.rr_best_qrs")
    delta_rr__rr = serializers.FloatField(source="electrocardiogram.delta_rr_rr")
    aqrs = serializers.IntegerField(source="electrocardiogram.aqrs")
    heart_rate = serializers.IntegerField(source="electrocardiogram.heart_rate")
    user = serializers.CharField(source="created_by.username")
    user_group = UserGroupSerializer(many=True, source="user.groups")
    eos = serializers.CharField(source="eos.title")
    heart_diagnoses = Heart_diagnosesSerializer(many=True)

    class Meta:
        model = Report
        fields = (
            "created_at",
            "electrocardiogram",
            "user",
            "user_group",
            "heart_diagnoses",
            "gender",
            "age",
            "p",
            "pq",
            "qrs",
            "qt",
            "rr_best_qrs",
            "delta_rr__rr",
            "aqrs",
            "heart_rate",
            "comment",
            "result",
            "pq",
            "eos",
            "aqrs_invalid",
            "has_artifacts",
        )


class ElectrocardiogramsDetailNoReportsSerializer(serializers.ModelSerializer):
    image = ImageSerializer(read_only=True, required=False)
    patient = PatientsSerializer(read_only=True)
    leads = serializers.JSONField(read_only=True)

    class Meta:
        model = Electrocardiogram
        exclude = ["updated_by", "is_deleted"]


class EcgFlatLeadSerializer(serializers.Serializer):
    type = serializers.CharField(source="type.id", read_only=True)
    type_name = serializers.CharField(source="type.name", read_only=True)
    source_file_index = serializers.IntegerField(read_only=True)
    data = serializers.JSONField(source="data_set.data")

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def create(self, validated_data):
        return super().create(validated_data)


class ElectrocardiogramsDetailSerializer(serializers.ModelSerializer):
    image = ImageSerializer(read_only=True, required=False)
    patient = PatientsSerializer(read_only=True)
    reports = ReportsForELWithHeartsSerializer(many=True, required=False, read_only=True)
    leads = serializers.JSONField(read_only=True)

    class Meta:
        model = Electrocardiogram
        exclude = ["updated_by", "is_deleted"]


class ElectrocardiogramsListSerializer(serializers.ModelSerializer):
    patient = PatientsSerializer(read_only=True)
    interpretation_count = serializers.IntegerField()
    image = ImageSerializer(read_only=True)
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Electrocardiogram
        exclude = ["updated_by", "is_deleted"]


class ElectrocardiogramCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Electrocardiogram
        exclude = ["updated_by", "is_deleted"]


class EcgLeadSerializer(serializers.Serializer):
    samples = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    avm = serializers.IntegerField(read_only=True)
    dimension = serializers.CharField(read_only=True)
    type = serializers.IntegerField(read_only=True)
    type_name = serializers.CharField(read_only=True)
    start = serializers.IntegerField(read_only=True)
    end = serializers.IntegerField(read_only=True)
    sample_frequency = serializers.IntegerField(read_only=True)
    source_file_index = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        result = super(EcgLeadSerializer, self).to_representation(instance)
        # check the request is list view or detail view
        is_list_view = isinstance(self.instance, list)
        extra_ret = {"key": "list value"} if is_list_view else {"key": "single value"}
        result.update(extra_ret)
        return result

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ElectrocardiogramCreateUpdateGraphQL(serializers.ModelSerializer):
    gender = serializers.CharField(required=False)

    class Meta:
        model = Electrocardiogram
        exclude = ["updated_by", "is_deleted"]


class ElectrocardiogramForPatientsSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    p = serializers.FloatField(required=False)
    pq = serializers.FloatField(required=False)
    age = serializers.IntegerField(required=False)
    qrs = serializers.FloatField(required=False)
    qt = serializers.FloatField(required=False)
    aqrs = serializers.IntegerField(required=False)
    delta_rr_rr = serializers.FloatField(required=False)
    gender = serializers.CharField(required=False, source="get_gender_display")
    heart_rate = serializers.IntegerField(required=False)
    rr_best_qrs = serializers.FloatField(required=False)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True, required=False)
    image = FileSerializer(read_only=True, required=False)

    class Meta:
        model = Electrocardiogram
        exclude = ["updated_by", "is_deleted"]


class PatientsElectroSerializer(serializers.ModelSerializer):
    electrocardiograms = ElectrocardiogramForPatientsSerializer(many=True, required=False, read_only=True)
    gender = serializers.CharField(required=False)

    class Meta:
        model = Patient
        exclude = ["updated_by", "is_deleted"]


class ElectrocardiogramListTasksSerializer(serializers.Serializer):
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects)
    questionnaire = QuestionnaireListSerializer(read_only=True)
    interpretation_diagnoses = Heart_diagnosesNotRequiredSerializer(read_only=True, required=False, many=True)
    interpretation_date = serializers.DateTimeField(read_only=True)
    user = UserSerializer(read_only=True)
    level_of_agreement = serializers.IntegerField(read_only=True)
    permissions = CaslJsRawRuleSerializer(many=True, read_only=True)


"""
reports
"""


class ReportsListSerializer(serializers.ModelSerializer):
    eos = EosNotRequiredSerializer(required=False)
    electrocardiogram = ElectrocardiogramForPatientsSerializer()
    user = UserSerializer()
    heart_diagnoses = Heart_diagnosesNotRequiredSerializer(required=False, many=True, read_only=True)

    class Meta:
        model = Report
        exclude = ["updated_by", "is_deleted"]


class ReportsCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        exclude = ["updated_by", "is_deleted"]


"""
Electrocardiogram_set
"""


class ElectrocardiogramSetDetailForTaskSerializer(serializers.ModelSerializer):
    random_order = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = ElectrocardiogramSet
        fields = ["electrocardiograms", "random_order"]


class ElectrocardiogramSetDetailSerializer(serializers.ModelSerializer):
    electrocardiograms = ElectrocardiogramCreateUpdateSerializer(required=False, many=True, read_only=True)

    class Meta:
        model = ElectrocardiogramSet
        exclude = ["updated_by", "is_deleted"]


def sort_ecg_set(ids, sort_id=None):
    if sort_id == "random":
        sort_order = 1
        sort_name = "?"
    else:
        if sort_id:
            sort_name = ElectrocardiogramSetOrderingField.objects.get(id=sort_id).name
            sort_order = ElectrocardiogramSetOrderingField.objects.get(id=sort_id).order
        else:
            sort_name, sort_order = "id", 1

    if sort_order == 2:
        order = f"-{sort_name}"
    else:
        order = f"{sort_name}"

    ecgs = (
        Electrocardiogram.objects.select_related("patient", "created_by", "image__collection__storage")
        .filter(id__in=ids)
        .order_by(order)
    )

    result = []

    for ecg in ecgs:
        result.append(ecg.id)

    return result


class ElectrocardiogramSetCreateUpdateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):

        ecg_set_ecgs = validated_data.pop("electrocardiograms")
        ecg_ids = [ecg.id for ecg in ecg_set_ecgs]

        if validated_data["ordering_type"] == "1":  # GLOBAL
            ordering_field_id = None
            if "ordering_field" in validated_data:
                ordering_field_id = validated_data["ordering_field"].id
            result = sort_ecg_set(ecg_ids, ordering_field_id)
            validated_data["electrocardiogram_ids"] = result
        else:  # USER
            validated_data["electrocardiogram_ids"] = ecg_ids

        ecg_set = ElectrocardiogramSet.objects.create(**validated_data)
        ecg_set.electrocardiograms.set(ecg_set_ecgs)
        return ecg_set

    def update(self, instance, validated_data):

        is_title_changed = instance.title != validated_data.get("title", instance.title)
        if is_title_changed:
            instance.title = validated_data.get("title", instance.title)

        is_ordering_field_changed = instance.ordering_field != validated_data.get(
            "ordering_field", instance.ordering_field
        )
        if is_ordering_field_changed:
            instance.ordering_field = validated_data.get("ordering_field", instance.ordering_field)

        is_ordering_type_changed = instance.ordering_type != validated_data.get("ordering_type", instance.ordering_type)
        if is_ordering_type_changed:
            instance.ordering_type = validated_data.get("ordering_type", instance.ordering_type)

        is_ecg_set_changed = False
        instance_ecg_set = instance.electrocardiogram_ids
        ecg_set_ecgs = instance_ecg_set
        if "electrocardiograms" not in validated_data:
            is_ecg_set_changed = False
        else:
            ecg_set_ecgs = validated_data.pop("electrocardiograms")
            ecg_ids = [ecg.id for ecg in ecg_set_ecgs]

            if len(instance_ecg_set) != len(ecg_ids):
                is_ecg_set_changed = True
            else:
                for ecg in ecg_ids:
                    if ecg not in instance_ecg_set:
                        is_ecg_set_changed = True
                        break

        add_to_tail = validated_data.get("add_to_tail", instance.add_to_tail)

        if (is_ecg_set_changed or is_ordering_field_changed or is_ordering_type_changed) and add_to_tail is False:
            if validated_data["ordering_type"] == "1":  # GLOBAL
                ordering_field_id = None
                if is_ordering_field_changed:
                    ordering_field_id = validated_data["ordering_field"].id
                result = sort_ecg_set(ecg_ids, ordering_field_id)
                electrocardiogram_ids = result
            if validated_data["ordering_type"] == "2":  # USER
                electrocardiogram_ids = ecg_ids
            instance.electrocardiogram_ids = electrocardiogram_ids

        else:  # random-tail
            if is_ecg_set_changed and add_to_tail:
                exist_ecg = []
                for k in instance_ecg_set:
                    exist_ecg.append(k)
                create_ecg = [x for x in ecg_ids if x not in exist_ecg]
                delete_ecg = [x for x in instance_ecg_set if x not in ecg_ids]

                if len(delete_ecg) > 0:
                    instance_ecg_set = [x for x in instance_ecg_set if x not in delete_ecg]

                if len(create_ecg) == 0:
                    pass
                elif len(create_ecg) == 1:
                    instance_ecg_set.append(create_ecg[0])
                else:
                    result = sort_ecg_set(create_ecg, None)
                    for id in result:
                        instance_ecg_set.append(id)
                electrocardiogram_ids = instance_ecg_set
                instance.electrocardiogram_ids = electrocardiogram_ids

        instance.save()
        instance.electrocardiograms.set(ecg_set_ecgs)

        return instance

    class Meta:
        model = ElectrocardiogramSet
        exclude = ["updated_by", "is_deleted"]


"""
ElectrocardiogramSetOrderingField
"""


class ElectrocardiogramSetOrderingFieldDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectrocardiogramSetOrderingField
        exclude = ["updated_by", "is_deleted"]


class ElectrocardiogramSetOrderingFieldCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectrocardiogramSetOrderingField
        exclude = ["updated_by", "is_deleted"]


"""
Electrocardiogram_set_user
"""


class ElectrocardiogramIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Electrocardiogram
        fields = ["id"]


class ElectrocardiogramSetUserOrderDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    electrocardiogram_set = ElectrocardiogramSetCreateUpdateSerializer(required=False, read_only=True)
    electrocardiogram = ElectrocardiogramIdSerializer(required=False, read_only=True)

    class Meta:
        model = ElectrocardiogramSetUserOrder
        exclude = ["updated_by", "is_deleted"]


class ElectrocardiogramSetUserOrderCreateUpdateSerializer(serializers.ModelSerializer):
    force_update_electrocardiogram_set = serializers.BooleanField(required=False, default=False)

    def is_create(self):
        return self.instance is None

    def is_update(self):
        return self.instance is not None

    def validate(self, data):
        # Проверка есть ли electrocardiogram_set на user-е
        user_sets = []
        if self.is_create():
            user_sets = ElectrocardiogramSetUserOrder.objects.filter(
                user=data["user"], electrocardiogram_set=data["electrocardiogram_set"]
            )
        else:
            if (
                self.instance.user != data["user"]
                or self.instance.electrocardiogram_set != data["electrocardiogram_set"]
            ):
                user_sets = ElectrocardiogramSetUserOrder.objects.filter(
                    user=data["user"], electrocardiogram_set=data["electrocardiogram_set"]
                )

        if len(user_sets) != 0:
            raise serializers.ValidationError("user already has this electrocardiogram_set")

        return data

    def create(self, validated_data):
        # Сортировка, если стоит USER в electrocardiogram_set.ordering_type
        el_set = validated_data["electrocardiogram_set"]
        ecg_set_order = el_set.ordering_type
        order_id = None
        if el_set.ordering_field:
            order_id = el_set.ordering_field.id

        # ElectrocardiogramSetUserOrder.order = 3, если в set стоит GLOBAL, но хочется USER сортировку (можно поменять)
        if ecg_set_order == "2" or validated_data["order"] == "3":
            if validated_data["order"] == "3":
                order_id = "random"
            result = sort_ecg_set(el_set.electrocardiogram_ids, order_id)
            validated_data["electrocardiogram_ids"] = result

            if "electrocardiogram" not in validated_data:
                validated_data["electrocardiogram"] = Electrocardiogram.objects.get(id=result[0])
        else:
            # дефолтное значение, когда отсортированный сет смотрится из другого места
            validated_data["electrocardiogram_ids"] = []
            if "electrocardiogram" not in validated_data:
                validated_data["electrocardiogram"] = Electrocardiogram.objects.get(id=el_set.electrocardiogram_ids[0])

        validated_data.pop("force_update_electrocardiogram_set")
        return ElectrocardiogramSetUserOrder.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("force_update_electrocardiogram_set", False):
            order_changed = True
        else:
            order_changed = instance.order != validated_data.get("order", instance.order)
            order_changed |= instance.electrocardiogram_set != validated_data.get(
                "electrocardiogram_set", instance.electrocardiogram_set
            )

        instance.user = validated_data.get("user", instance.user)
        instance.order = validated_data.get("order", instance.order)
        instance.electrocardiogram_set = validated_data.get("electrocardiogram_set", instance.electrocardiogram_set)
        instance.electrocardiogram = validated_data.get("electrocardiogram", instance.electrocardiogram)
        instance.add_to_tail = validated_data.get("add_to_tail", instance.add_to_tail)

        el_set = instance.electrocardiogram_set
        ecg_set_order = el_set.ordering_type

        if order_changed and (ecg_set_order == "2" or instance.order == "3"):
            # ElectrocardiogramSetUserOrder.order = 3, если в set стоит GLOBAL, но хочется USER сортировку
            order_id = None
            if el_set.ordering_field:
                order_id = el_set.ordering_field.id
            if instance.order == "3":
                order_id = "random"

            if instance.add_to_tail is False or validated_data.get(
                "force_update_electrocardiogram_set", False
            ):  # Пересорт все
                result = sort_ecg_set(el_set.electrocardiogram_ids, order_id)
                instance.electrocardiogram_ids = result
                instance.electrocardiogram = Electrocardiogram.objects.get(id=result[0])
            else:  # add_to_tail = True, делаем random-tail
                ecg_new = []
                for ecg in instance.electrocardiogram_set.electrocardiogram_ids:
                    if ecg not in instance.electrocardiogram_ids:
                        ecg_new.append(ecg)
                if len(ecg_new) == 0:  # TODO
                    result = sort_ecg_set(el_set.electrocardiogram_ids, order_id)
                    instance.electrocardiogram_ids = result
                elif len(ecg_new) == 1:
                    instance.electrocardiogram_ids.append(ecg_new[0])
                else:
                    result = sort_ecg_set(ecg_new, order_id)
                    for id in result:
                        instance.electrocardiogram_ids.append(id)
        else:
            # первое значение из отсортированного массива сета
            instance.electrocardiogram = Electrocardiogram.objects.get(id=el_set.electrocardiogram_ids[0])
        instance.save()
        return instance

    class Meta:
        model = ElectrocardiogramSetUserOrder
        exclude = ["is_deleted"]


class ElectrocardiogramSetUserIdSerializer(serializers.Serializer):
    electrocardiogram = ElectrocardiogramForPatientsSerializer()
    """ electrocardiogram_set = ElectrocardiogramSetCreateUpdateSerializer(required=False, read_only=True)
    electrocardiogram_ids = [serializers.IntegerField(required=False, read_only=True)] """
    ecg_index = serializers.IntegerField()
    is_first = serializers.BooleanField()
    is_last = serializers.BooleanField()

    def __init__(self, electrocardiogram=None, ecg_index=None, is_first=None, is_last=None):
        super().__init__(
            instance={
                "electrocardiogram": electrocardiogram,
                "ecg_index": ecg_index,
                "is_first": is_first,
                "is_last": is_last,
            },
            data=empty,
        )


def delete_set_user(user_id, set_id):
    user_set_del = ElectrocardiogramSetUserOrder.objects.get(user=user_id, electrocardiogram_set=set_id)
    user_set_del.delete()


class ElectrocardiogramSetUserGroupCreateUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    user_group = serializers.ListField(child=serializers.IntegerField(), required=False, default=[])
    users = serializers.ListField(child=serializers.IntegerField(), required=False, default=[])
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, default=None, allow_null=True
    )
    order = serializers.IntegerField(default=1)
    choice = serializers.CharField()  # create, update or delete
    force_update_existing = serializers.BooleanField(required=False, default=False)

    def create(self, validated_data):
        id_users = []
        for i in validated_data["user_group"]:
            users_in_group = User.objects.filter(groups=i)
            for k in users_in_group:
                id_users.append(k.id)
        for i in validated_data["users"]:
            id_users.append(i)
        if validated_data["user"] is not None:
            id_users.append(validated_data["user"].id)
        id_users = set(id_users)  # убиpаю дубли

        create_data_mixin = {
            "created_by": validated_data["created_by"],
            "created_at": validated_data["created_at"],
        }

        update_data_mixin = {
            "updated_by": validated_data.get("updated_by", validated_data["created_by"]),
            "updated_at": validated_data.get("updated_at", validated_data["created_at"]),
        }

        if validated_data["choice"] == "delete" or validated_data["choice"] == "create":
            for i in list(id_users):
                if validated_data["choice"] == "delete":
                    delete_set_user(i, validated_data["electrocardiogram_set"].id)

                elif validated_data["choice"] == "create":
                    data = {
                        "user": i,
                        "order": validated_data["order"],
                        "electrocardiogram_set": validated_data["electrocardiogram_set"].id,
                    }
                    Helper.create(ElectrocardiogramSetUserOrderCreateUpdateSerializer, data, create_data_mixin)

        if validated_data["choice"] == "update":
            exist_user = ElectrocardiogramSetUserOrder.objects.filter(
                electrocardiogram_set=validated_data["electrocardiogram_set"].id
            )
            exist_id = []
            for k in exist_user:
                exist_id.append(k.user.id)
            create_user = [x for x in id_users if x not in exist_id]
            delete_user = [x for x in exist_id if x not in id_users]
            if len(delete_user) != 0:
                for j in delete_user:
                    delete_set_user(j, validated_data["electrocardiogram_set"].id)
            if len(create_user) != 0:
                for p in create_user:
                    data = {
                        "user": p,
                        "order": validated_data["order"],
                        "electrocardiogram_set": validated_data["electrocardiogram_set"].id,
                    }
                    Helper.create(ElectrocardiogramSetUserOrderCreateUpdateSerializer, data, create_data_mixin)
            if validated_data["force_update_existing"]:
                update_user_ids = [x for x in exist_id if x in id_users]
                if len(update_user_ids) > 0:
                    existing_orders = ElectrocardiogramSetUserOrder.objects.filter(
                        electrocardiogram_set=validated_data["electrocardiogram_set"], user__id__in=update_user_ids
                    )
                    for order in existing_orders:
                        data = {
                            "user": order.user.id,
                            "order": validated_data["order"],
                            "electrocardiogram_set": validated_data["electrocardiogram_set"].id,
                            "force_update_electrocardiogram_set": True,
                        }
                        Helper.update(
                            ElectrocardiogramSetUserOrderCreateUpdateSerializer, order, data, update_data_mixin
                        )
        return validated_data

    class Meta:
        model = ElectrocardiogramSetUserOrder
        exclude = ["is_deleted"]


class ElectrocardiogramSetUserGroupUpdateOrderSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False)
    ordering_field = serializers.CharField(required=False)

    def update(self, instance, validated_data):
        order_changed = instance.ordering_type != validated_data.get("ordering_type", instance.ordering_type)

        instance.ordering_type = validated_data.get("ordering_type", instance.ordering_type)

        if order_changed:
            ElectrocardiogramSet.objects.update(**validated_data)

            update_data_mixin = {
                "updated_by": User.objects.get(id=instance.updated_by.id),
                "updated_at": timezone.now(),
            }

            set_user = ElectrocardiogramSetUserOrder.objects.filter(electrocardiogram_set=instance.id)
            if instance.ordering_type == "2":
                for i in set_user:
                    data = {
                        "user": i.user.id,
                        "order": 3,
                        "electrocardiogram_set": i.electrocardiogram_set.id,
                    }
                    Helper.update(ElectrocardiogramSetUserOrderCreateUpdateSerializer, i, data, update_data_mixin)
            else:
                for i in set_user:
                    data = {
                        "user": i.user.id,
                        "order": 1,
                        "electrocardiogram_set": i.electrocardiogram_set.id,
                    }
                    Helper.update(ElectrocardiogramSetUserOrderCreateUpdateSerializer, i, data, update_data_mixin)

        return instance

    class Meta:
        model = ElectrocardiogramSet
        exclude = ["is_deleted"]


class FoundDiagnosisSerializer(serializers.Serializer):
    diagnosis = Heart_diagnosesNotRequiredSerializer(read_only=True)
    confidence = serializers.FloatField(read_only=True)
    is_true = serializers.BooleanField(read_only=True)


class EcgDiagnosesPredictionModelBaseDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcgDiagnosesPredictionExternalModel
        fields = ("id", "name", "version", "description")


class ExceptionSerializer(serializers.Serializer):
    def to_representation(self, instance):

        if hasattr(instance, "type"):
            type = str(instance.type)
        else:
            type = instance.__class__.__name__

        return {
            "type": type,
            "message": str(instance),
        }


class DiagnosisModelInferenceResultSerializer(serializers.Serializer):
    model = EcgDiagnosesPredictionModelBaseDetailsSerializer(read_only=True)
    diagnoses = FoundDiagnosisSerializer(many=True, read_only=True)
    error = ExceptionSerializer(required=False, read_only=True)


class DiagnosisModelInferenceResultSetSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = DiagnosisModelInferenceResultSerializer(many=True, read_only=True)


class EcgUploadSerializer(serializers.Serializer):
    collection = serializers.IntegerField(required=False)
    types = serializers.PrimaryKeyRelatedField(queryset=EcgType.objects, many=True, required=False)
    file_set_type = serializers.CharField(required=False)
    files = serializers.FileField()


class FileUploadExceptionSerializer(serializers.Serializer):
    file = serializers.CharField(read_only=True)
    error = ExceptionSerializer(read_only=True)


class EcgUploadResultSerializer(serializers.Serializer):
    existing_electrocardiograms = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    new_electrocardiograms = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    errors = FileUploadExceptionSerializer(many=True)
