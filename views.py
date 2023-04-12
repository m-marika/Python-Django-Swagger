import re
from os import path

from django.contrib.auth.models import User, Group
from django.db.models import Prefetch, Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, filters, status
from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_csv import renderers as r

from api.common import permissions as perm
from api.common.filters import EntityListFilterByIdSet
from api.common.logging import get_logger
from api.common.mixins import CreateModelWithByMixin, UpdateModelWithByMixin
from api.common.models import CaslJsRawRule
from api.common.pagination import paginate_list
from api.common.permissions import IsAuthorOrSuperUserOrReadOnly
from api.common.serializers import (
    CurrentUserSerializer,
    UserGroupSerializer,
    UserGroupDetailSerializer,
    CaslJsRawRuleSerializer,
)
from api.processing.models import FunctionRunStatus
from api.storage.helpers import DEFAULT_COLLECTION_NAME, get_or_store_file_stream
from api.storage.models import Collection
from api.tasks.models import (
    CHANGE_TASK_PERMISSION,
    TASK_ACTION_SUBJECT,
)
from api.tasks.task_types.questionnaire_task.models import QuestionnaireTaskEcgResult, QuestionnaireResult
from api.tasks.task_types.questionnaire_task.views import ResultInterpretation, Diagnoses
from .helpers import ECGSetHelper, ECGTaskHelper, ECGInterpretationHelper
from .ml.runners import run_ecg_ml_models
from .models import (
    Diagnosis,
    Patient,
    Eos,
    Electrocardiogram,
    Report,
    HeartDiagnosis,
    ElectrocardiogramSet,
    ElectrocardiogramSetUserOrder,
    ElectrocardiogramSetOrderingField,
    EcgData,
    EcgInterpretationRule,
    EcgInterpretationRuleItem,
    EcgResultInterpretation,
    EcgInterpretation,
    EcgDiagnosesPredictionExternalModel,
    DiagnosisModelInferenceResult,
    EcgSource,
    EcgSourceFile,
    SourceFileStatus,
    SourceFileType,
)
from .processing.dicom_source import DicomSourceProcessingFunction
from .processing.edf_source import ProcessEdfSourceFileFunction, ProcessEdfSourceFileFunctionRunOptions
from .processing.helpers import get_or_create_ecg_data, compile_ecg_data_content
from .serializers import (
    DiagnosesSerializer,
    ElectrocardiogramsDetailSerializer,
    ElectrocardiogramsListSerializer,
    EosSerializer,
    Heart_diagnosesSerializer,
    ReportsListSerializer,
    ElectrocardiogramsReportsListSerializer,
    PatientsElectroSerializer,
    ElectrocardiogramCreateUpdateSerializer,
    ReportsCreateUpdateSerializer,
    ElectrocardiogramSetDetailSerializer,
    ElectrocardiogramSetCreateUpdateSerializer,
    ElectrocardiogramSetUserOrderDetailSerializer,
    ElectrocardiogramSetUserOrderCreateUpdateSerializer,
    ElectrocardiogramSetUserIdSerializer,
    ElectrocardiogramSetOrderingFieldDetailSerializer,
    ElectrocardiogramSetOrderingFieldCreateUpdateSerializer,
    ElectrocardiogramSetUserGroupCreateUpdateSerializer,
    ElectrocardiogramSetUserGroupUpdateOrderSerializer,
    QuestionnaireInterpretationRuleSerializer,
    QuestionnaireInterpretationRuleItemSerializer,
    QuestionnaireResultInterpretationSerializer,
    QuestionnaireResultInterpretationCalcSerializer,
    EcgInterpretationSerializer,
    EcgLeadSerializer,
    ElectrocardiogramListTasksSerializer,
    DiagnosisModelInferenceResultSetSerializer,
    EcgUploadSerializer,
    EcgUploadResultSerializer,
)


class UserList(generics.ListAPIView):
    queryset = User.objects.prefetch_related("groups").all()
    serializer_class = CurrentUserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = CurrentUserSerializer


class CurrentUserDetail(APIView):
    @staticmethod
    def get(request):
        return Response(CurrentUserSerializer(request.user).data)


class CurrentUserPermissions(APIView):
    def get_serializer(self):
        return CaslJsRawRuleSerializer()

    def get(self, request):
        result = []

        permissions = request.user.get_all_permissions()
        for permission in permissions:
            arr = permission.split(".")[-1].split("_")
            result.append(CaslJsRawRule(action=arr[0], subject=arr[1]))

        return Response(CaslJsRawRuleSerializer(result, many=True).data)


class GroupList(generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = UserGroupSerializer


class GroupDetail(generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = UserGroupDetailSerializer


"""
Diagnoses
"""


class DiagnosesDetView(UpdateModelWithByMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DiagnosesSerializer
    queryset = Diagnosis.objects.all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DiagnosesViewSet(CreateModelWithByMixin, generics.ListCreateAPIView):
    queryset = Diagnosis.objects.all()
    serializer_class = DiagnosesSerializer


class DiagnosesCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        diagnoses_count = Diagnosis.objects.count()
        content = diagnoses_count
        return Response(content)


"""
Patients
"""


class PatientsListView(CreateModelWithByMixin, generics.ListCreateAPIView):
    serializer_class = PatientsElectroSerializer
    queryset = (
        Patient.objects.select_related("created_by")
        .prefetch_related(
            "electrocardiograms",
            "electrocardiograms__image__collection",
        )
        .all()
    )


class PatientDetailView(UpdateModelWithByMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PatientsElectroSerializer
    queryset = (
        Patient.objects.select_related("created_by")
        .prefetch_related(
            "electrocardiograms",
            "electrocardiograms__image__collection",
        )
        .all()
    )


class PatientCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        patients_count = Patient.objects.count()
        content = patients_count
        return Response(content)


"""
electrocardiograms
"""


def _get_electrocardiogram_queryset(context):
    queryset = Electrocardiogram.objects_fully_prefetched

    if context.request.user.is_superuser:
        return queryset.prefetch_related(
            "reports__eos",
            "reports__created_by",
            "reports__user__groups",
            "reports__heart_diagnoses",
        )

    user_groups = context.request.user.groups.all()
    return queryset.prefetch_related(
        Prefetch(
            "reports",
            queryset=Report.objects.select_related("user")
            .prefetch_related("user__groups", "eos", "created_by", "heart_diagnoses")
            .filter(user__groups__in=[g.id for g in user_groups]),
        ),
    )


class ElectrocardiogramsListView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EntityListFilterByIdSet
    search_fields = ["id"]
    ordering_fields = ["id", "patient", "created_at", "updated_at", "age", "gender", "interpretation_count"]
    ordering = ["id"]

    per_100 = Count(
        "questionnairetaskecgresult",
        filter=Q(
            questionnairetaskecgresult__result__progress=100,
            questionnairetaskecgresult__result__is_deleted=False,
            questionnairetaskecgresult__task__is_deleted=False,
        ),
    )

    queryset = Electrocardiogram.objects.select_related("patient").annotate(interpretation_count=per_100).all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramsListSerializer
        return ElectrocardiogramCreateUpdateSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            page = ECGTaskHelper.enrich_ecg_with_task_count_field(page)
            serializer = ElectrocardiogramsListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        queryset = ECGTaskHelper.enrich_ecg_with_task_count_field(queryset)
        serializer = ElectrocardiogramsListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = ElectrocardiogramCreateUpdateSerializer(data=request.data)
        serializer.initial_data["created_by"] = request.user.id
        serializer.initial_data["created_at"] = timezone.now()
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ElectrocardiogramsDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramsDetailSerializer
        return ElectrocardiogramCreateUpdateSerializer

    def get_queryset(self):
        return _get_electrocardiogram_queryset(self)

    def get(self, request, *args, **kwargs):
        ecg = self.get_object()

        try:
            ecg_data = get_or_create_ecg_data(ecg, request.query_params.getlist("filter"), request.user)

            content = compile_ecg_data_content(ecg_data)
            for lead in content["leads"]:
                lead["samples"] = paginate_list(lead["samples"], request)

            setattr(ecg, "leads", content["leads"])
        except EcgData.DoesNotExist:
            pass

        return Response(ElectrocardiogramsDetailSerializer(ecg).data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.updated_at = timezone.now()
        instance.updated_by = self.request.user
        serializer = ElectrocardiogramCreateUpdateSerializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response({"message": "failed", "details": serializer.errors})


class ElectrocardiogramLeadListView(generics.RetrieveAPIView):
    def get_serializer(self):
        return EcgLeadSerializer()

    def get_queryset(self):
        return _get_electrocardiogram_queryset(self)

    def get(self, request, *args, **kwargs):
        ecg = self.get_object()

        try:
            ecg_data = get_or_create_ecg_data(ecg, request.query_params.getlist("filter"), request.user)
        except EcgData.DoesNotExist:
            raise NotFound

        content = compile_ecg_data_content(ecg_data)
        for lead in content["leads"]:
            lead["samples"] = paginate_list(lead["samples"], request)

        return Response(content["leads"])


class ElectrocardiogramListTasksView(generics.ListAPIView):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        "questionnairetaskecgresult__task__id",
        "questionnaire__title",
        "ecgresultinterpretation__diagnoses__title",
        "ecgresultinterpretation__diagnoses__code",
    ]
    ordering_fields = ["questionnairetaskecgresult__task", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return ElectrocardiogramListTasksSerializer

    def get_queryset(self):
        results = QuestionnaireResult.objects.filter(
            progress=100,
            id__in=(
                QuestionnaireTaskEcgResult.objects.filter(
                    ecg__in=Electrocardiogram.objects.filter(id=self.kwargs["pk"]).prefetch_related("user"),
                ).select_related("task", "ecg", "result")
            ),
        ).select_related("user", "questionnaire")
        return results

    def list(self, request, *args, **kwargs):

        order = request.query_params.get("ordering")
        order_new = []
        if order:
            order_items = [oi.strip() for oi in order.split(",")]
            if "task" in order_items:
                order_new.append("questionnairetaskecgresult__task")
            elif "-task" in order_items:
                order_new.append("-questionnairetaskecgresult__task")
            if "interpretation_date" in order_items:
                order_new.append("created_at")
            elif "-interpretation_date" in order_items:
                order_new.append("-created_at")

            if len(order_new) > 0:
                order_new = ",".join(order_new)
                request.query_params._mutable = True
                request.query_params.__setitem__("ordering", order_new)

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            queryset = page

        for result in queryset:

            task = QuestionnaireTaskEcgResult.objects.select_related("task").get(
                ecg=self.kwargs["pk"], result=result.id
            )

            try:
                flag_rule = EcgInterpretationRule.objects.get(questionnaire_id=result.questionnaire)

                interpretation_diagnoses = ResultInterpretation

                interpretation_diagnoses = ECGInterpretationHelper.interpretation_result(self, flag_rule.id, result.id)

            except EcgInterpretationRule.DoesNotExist:
                interpretation_diagnoses = ResultInterpretation(
                    rule=None,
                    diagnoses=[
                        Diagnoses(
                            title="Can't calculate diagnoses! You need to create rule on this questionnaire!", code=None
                        )
                    ],
                    result_id=result.id,
                )

            result.interpretation_date = result.created_at
            result.task = task.task
            result.questionnaire = result.questionnaire
            result.interpretation_diagnoses = interpretation_diagnoses.diagnoses
            result.level_of_agreement = 33
            result.permissions = []

            if request.user.is_superuser or (
                task.task.created_by == request.user and request.user.has_perm(CHANGE_TASK_PERMISSION)
            ):
                result.permissions.append(CaslJsRawRule(action=perm.CHANGE_ACTION, subject=TASK_ACTION_SUBJECT))

        serializer = ElectrocardiogramListTasksSerializer(queryset, many=True)

        if page is not None:
            return self.get_paginated_response(serializer.data)
        else:
            return Response(serializer.data)


class ElectrocardiogramsCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        electrocardiograms_count = Electrocardiogram.objects.count()
        content = electrocardiograms_count
        return Response(content)


def regular_header(header, reg_exp):
    result_headers = []
    for i in header:
        result = re.match(reg_exp, i)
        if result is not None:
            i = i.replace(reg_exp, "")
            result_headers.append(i)
    return result_headers


def data_for_many(dict, headers, row, n):
    hearts_result = [dict.get(key, None) for key in headers]
    hearts_result = ",".join([x for x in hearts_result if x is not None])
    row[n] = hearts_result
    return row


class SpecialCharSeparator(r.CSVRenderer):
    def render(self, data, media_type=None, renderer_context=None, writer_opts=None):

        if writer_opts is None:
            writer_opts = {}

        new_writer_opts = {"delimiter": ";"}
        new_writer_opts.update(writer_opts)

        return super(SpecialCharSeparator, self).render(
            data, media_type, renderer_context, writer_opts=new_writer_opts
        )  # set your delimiter her

    def tablize(self, data, header=None, labels=None):
        if not header and hasattr(data, "header"):
            header = data.header

        if data:
            data = self.flatten_data(data)

            if not header:
                data = tuple(data)
                header_fields = set()
                for item in data:
                    header_fields.update(list(item.keys()))
                header_full = sorted(header_fields)
                header = sorted(header_fields)
                header = [
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
                ]

            if labels:  # write headers
                yield [labels.get(x, x) for x in header]
            else:
                yield header
            for n, dict_ in enumerate(data):
                hearts = regular_header(header_full, r"heart_diagnoses.\d.scp")
                groups = regular_header(header_full, r"user_group.\d.name")

                row = [dict_.get(key, None) for key in header]

                row = data_for_many(dict_, hearts, row, 4)
                row = data_for_many(dict_, groups, row, 3)
                yield row

        elif header:
            if labels:
                yield [labels.get(x, x) for x in header]
            else:
                yield header
        else:
            pass


class ElectrocardiogramsAllReportsListView(generics.ListAPIView):
    serializer_class = ElectrocardiogramsReportsListSerializer
    queryset = (
        Report.objects.select_related("electrocardiogram", "user", "eos", "created_by")
        .prefetch_related(
            "heart_diagnoses",
            "user__groups",
        )
        .all()
    )

    pagination_class = None
    renderer_classes = [SpecialCharSeparator] + [r.CSVRenderer]


"""
eos
"""


class EosListView(generics.ListCreateAPIView):
    serializer_class = EosSerializer
    queryset = Eos.objects.all()


class EosDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EosSerializer
    queryset = Eos.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.updated_at = timezone.now()
        instance.updated_by = self.request.user
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response({"message": "failed", "details": serializer.errors})


class EosCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        eos_count = Eos.objects.count()
        content = eos_count
        return Response(content)


"""
Heart_diagnoses
"""


class Heart_diagnosesListView(CreateModelWithByMixin, generics.ListCreateAPIView):
    serializer_class = Heart_diagnosesSerializer
    queryset = HeartDiagnosis.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "code"]


class Heart_diagnosesDetailView(UpdateModelWithByMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = Heart_diagnosesSerializer
    queryset = HeartDiagnosis.objects.all()


class Heart_diagnosesCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        heart_diagnoses_count = HeartDiagnosis.objects.count()
        content = heart_diagnoses_count
        return Response(content)


"""
Interpretation
"""


class QuestionnaireInterpretationRuleListView(CreateModelWithByMixin, generics.ListCreateAPIView):
    serializer_class = QuestionnaireInterpretationRuleSerializer
    queryset = EcgInterpretationRule.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = QuestionnaireInterpretationRuleSerializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.validated_data["created_at"] = timezone.now()
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuestionnaireInterpretationRuleDetailView(UpdateModelWithByMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionnaireInterpretationRuleSerializer
    queryset = EcgInterpretationRule.objects.all()


class QuestionnaireInterpretationRuleCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        quest_inter_rule_count = EcgInterpretationRule.objects.count()
        content = quest_inter_rule_count
        return Response(content)


class QuestionnaireInterpretationRuleItemListView(CreateModelWithByMixin, generics.ListCreateAPIView):
    serializer_class = QuestionnaireInterpretationRuleItemSerializer
    queryset = EcgInterpretationRuleItem.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "classifier", "questionnaire"]

    def create(self, request, *args, **kwargs):
        serializer = QuestionnaireInterpretationRuleItemSerializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.validated_data["created_at"] = timezone.now()
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuestionnaireInterpretationRuleItemDetailView(UpdateModelWithByMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionnaireInterpretationRuleItemSerializer
    queryset = EcgInterpretationRuleItem.objects.all()


class QuestionnaireInterpretationRuleItemCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        quest_inter_rule_count = EcgInterpretationRuleItem.objects.count()
        content = quest_inter_rule_count
        return Response(content)


class QuestionnaireResultInterpretationListView(CreateModelWithByMixin, generics.ListCreateAPIView):
    serializer_class = QuestionnaireResultInterpretationSerializer
    queryset = EcgResultInterpretation.objects.all()


class QuestionnaireResultInterpretationDetailView(UpdateModelWithByMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionnaireResultInterpretationSerializer
    queryset = EcgResultInterpretation.objects.all()


class QuestionnaireResultInterpretationCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        quest_inter_rule_count = EcgResultInterpretation.objects.count()
        content = quest_inter_rule_count
        return Response(content)


class EcgInterpretationListView(generics.ListAPIView):
    serializer_class = EcgInterpretationSerializer
    queryset = EcgInterpretation.objects.all()


class QuestionnaireResultInterpretationCalcListView(APIView):
    serializer_class = QuestionnaireResultInterpretationCalcSerializer
    queryset = EcgResultInterpretation.objects.all()

    def get(self, request, *args, **kwargs):

        exist_enter = ECGInterpretationHelper.interpretation_result(self, kwargs["rule_id"], kwargs["result_id"])

        serializer = QuestionnaireResultInterpretationCalcSerializer(exist_enter)

        if serializer:
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuestionnaireResultInterpretationCalcDetailView(generics.UpdateAPIView):
    serializer_class = QuestionnaireResultInterpretationCalcSerializer
    queryset = EcgResultInterpretation.objects.all()

    def update(self, request, *args, **kwargs):

        instance = self.get_object()

        exist_enter = ECGInterpretationHelper.update_interpretation(
            self, instance.result, instance.rule, instance, True
        )

        serializer = QuestionnaireResultInterpretationCalcSerializer(exist_enter)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


"""
Reports
"""


class ReportsListView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ReportsListSerializer
        return ReportsCreateUpdateSerializer

    def get_queryset(self):
        queryset = (
            Report.objects.select_related("electrocardiogram", "created_by", "eos", "user")
            .prefetch_related(
                "heart_diagnoses",
                "electrocardiogram__image__collection",
                "heart_diagnoses__created_by",
                "eos__created_by",
                "electrocardiogram__patient",
            )
            .all()
        )

        if self.request.user.is_superuser:
            return queryset

        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ReportsCreateUpdateSerializer(data=request.data)
        serializer.initial_data["created_by"] = request.user.id
        serializer.initial_data["created_at"] = timezone.now()
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportsDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ReportsListSerializer
        return ReportsCreateUpdateSerializer

    queryset = (
        Report.objects.select_related("electrocardiogram", "created_by", "eos", "user")
        .prefetch_related(
            "heart_diagnoses",
            "electrocardiogram__image__collection",
            "heart_diagnoses__created_by",
            "eos__created_by",
            "electrocardiogram__patient",
        )
        .all()
    )
    permission_classes = (IsAuthenticated, IsAuthorOrSuperUserOrReadOnly)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.updated_at = timezone.now()
        instance.updated_by = self.request.user

        serializer = ReportsCreateUpdateSerializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportsCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        reports_count = Report.objects.count()
        content = reports_count
        return Response(content)


"""
Electrocardiogram_set
"""


class ElectrocardiogramSetView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramSetDetailSerializer
        return ElectrocardiogramSetCreateUpdateSerializer

    def get_queryset(self):
        queryset = (
            ElectrocardiogramSet.objects.select_related("ordering_field", "created_by")
            .prefetch_related(
                "electrocardiograms",
            )
            .all()
        )

        if self.request.user.is_superuser:
            return queryset

        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ElectrocardiogramSetCreateUpdateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.validated_data["created_at"] = timezone.now()
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ElectrocardiogramSetDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramSetDetailSerializer
        return ElectrocardiogramSetCreateUpdateSerializer

    queryset = ElectrocardiogramSet.objects.prefetch_related(
        "electrocardiograms",
    ).all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.updated_at = timezone.now()
        instance.updated_by = self.request.user

        serializer = ElectrocardiogramSetCreateUpdateSerializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ElectrocardiogramSetCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, format=None):
        reports_count = ElectrocardiogramSet.objects.count()
        content = reports_count
        return Response(content)


"""
ElectrocardiogramSetOrderingField
"""


class ElectrocardiogramSetOrderingFieldView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramSetOrderingFieldDetailSerializer
        return ElectrocardiogramSetOrderingFieldCreateUpdateSerializer

    def get_queryset(self):
        queryset = ElectrocardiogramSetOrderingField.objects.all()

        if self.request.user.is_superuser:
            return queryset

        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ElectrocardiogramSetOrderingFieldCreateUpdateSerializer(data=request.data)
        serializer.initial_data["created_by"] = request.user.id
        serializer.initial_data["created_at"] = timezone.now()

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ElectrocardiogramSetOrderingFieldDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramSetOrderingFieldDetailSerializer
        return ElectrocardiogramSetOrderingFieldCreateUpdateSerializer

    queryset = ElectrocardiogramSetOrderingField.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.updated_at = timezone.now()
        instance.updated_by = self.request.user

        serializer = ElectrocardiogramSetOrderingFieldCreateUpdateSerializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response(
                {"message": "failed", "details": serializer.errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


"""
Electrocardiogram_set_user
"""


class ElectrocardiogramSetUserView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramSetUserOrderDetailSerializer
        return ElectrocardiogramSetUserOrderCreateUpdateSerializer

    def get_queryset(self):
        queryset = (
            ElectrocardiogramSetUserOrder.objects.select_related("user", "electrocardiogram_set", "electrocardiogram")
            .prefetch_related(
                "electrocardiogram__image__collection__storage",
            )
            .all()
        )

        if self.request.user.is_superuser:
            return queryset

        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ElectrocardiogramSetUserOrderCreateUpdateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.validated_data["created_at"] = timezone.now()
            serializer.save()
            return Response(serializer.data)

        else:
            return Response({"message": "failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ElectrocardiogramSetUserOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        if self.request.method == "GET":
            return ElectrocardiogramSetUserOrderDetailSerializer
        return ElectrocardiogramSetUserOrderCreateUpdateSerializer

    queryset = (
        ElectrocardiogramSetUserOrder.objects.select_related("user", "electrocardiogram_set", "electrocardiogram")
        .prefetch_related(
            "electrocardiogram__image__collection__storage",
        )
        .all()
    )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.updated_by = self.request.user
        instance.updated_at = timezone.now()

        serializer = ElectrocardiogramSetUserOrderCreateUpdateSerializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        else:
            return Response({"message": "failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ElectrocardiogramSetNextPreviousView(generics.ListAPIView):
    serializer_class = ElectrocardiogramSetUserIdSerializer

    def get_queryset(self):

        queryset = (
            ElectrocardiogramSetUserOrder.objects.filter(
                user_id=self.request.user.id,
                electrocardiogram_set=self.kwargs["pk"],
            )
            .select_related("electrocardiogram", "user", "created_by", "electrocardiogram_set")
            .prefetch_related("electrocardiogram_set")
        )
        if self.request.user.is_superuser:
            return queryset

        return queryset.filter(user=self.request.user)

    def get(self, request, pk, list, el_id):

        el_set = ElectrocardiogramSet.objects.get(id=pk)
        user_set = ElectrocardiogramSetUserOrder.objects.get(electrocardiogram_set=pk, user_id=self.request.user.id)

        next_result = ECGSetHelper.get_next_prev_ecg(el_set, user_set, list, el_id)

        return Response(
            ElectrocardiogramSetUserIdSerializer(
                next_result.ecg, next_result.index, next_result.is_first, next_result.is_last
            ).data
        )


class ElectrocardiogramSetUserGroupView(generics.CreateAPIView, APIView):
    """
    choice = [create, update, delete]
    В зависимости от того, что планируется делать с группами пользователей
    надо передать в поле choice нужную команду:
    create(всегда при post) = все переданные группы, пользователи создадутся сете(ElectrocardiogramSetUserOrder)
    update = бэк сам определит какие группы/польз удалены или добавлены и сделает это на бэке
    delete = все пользователи будут удалены из сета
    """

    serializer_class = ElectrocardiogramSetUserGroupCreateUpdateSerializer

    def create(self, request, *args, **kwargs):
        serializer = ElectrocardiogramSetUserGroupCreateUpdateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.validated_data["created_at"] = timezone.now()
            serializer.validated_data["choice"] = "create"
            serializer.save()
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        serializer = ElectrocardiogramSetUserGroupCreateUpdateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.validated_data["created_at"] = timezone.now()
            serializer.save()
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ElectrocardiogramSetUserGroupUpdateOrderView(generics.UpdateAPIView):
    serializer_class = ElectrocardiogramSetUserGroupUpdateOrderSerializer
    queryset = ElectrocardiogramSet.objects.prefetch_related(
        "electrocardiogram_set",
    ).all()

    def update(self, request, *args, **kwargs):

        instance = self.get_object()
        instance.updated_by = self.request.user
        instance.updated_at = timezone.now()

        serializer = ElectrocardiogramSetUserGroupUpdateOrderSerializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


def get_corresponding_diagnoses_models(ecg):
    ecg_type_ids = [ecg_type.id for ecg_type in ecg.types.all()]
    ecg_types_count = len(ecg_type_ids)
    if ecg_types_count > 0:
        diagnoses_models = (
            EcgDiagnosesPredictionExternalModel.objects.prefetch_related("ecg_types")
            .annotate(ecg_type_count=Count("ecg_types"))
            .filter(Q(ecg_type_count__lte=ecg_types_count) | Q(ecg_type_count=0))
        )
    else:
        diagnoses_models = (
            EcgDiagnosesPredictionExternalModel.objects.prefetch_related("ecg_types")
            .annotate(ecg_type_count=Count("ecg_types"))
            .filter(ecg_type_count=0)
        )

    type_corresponding_diagnoses_models = []
    for diagnoses_model in diagnoses_models:
        for diagnosis_ecg_type in diagnoses_model.ecg_types.all():
            if diagnosis_ecg_type.id not in ecg_type_ids:
                break
        else:
            type_corresponding_diagnoses_models.append(diagnoses_model)

    return type_corresponding_diagnoses_models


class EcgModelInferenceView(APIView):
    def get_serializer(self):
        return DiagnosisModelInferenceResultSetSerializer()

    def get(self, request, pk):
        try:
            ecg = Electrocardiogram.objects.get(pk=pk)
        except Electrocardiogram.DoesNotExist:
            raise NotFound

        type_corresponding_diagnoses_models = get_corresponding_diagnoses_models(ecg)

        if len(type_corresponding_diagnoses_models) == 0:
            raise NotFound

        model_inference_results = run_ecg_ml_models(type_corresponding_diagnoses_models, ecg)
        found_diagnosis_codes = set()

        for model_result in model_inference_results:
            if model_result.error is None:
                for result_diagnosis in model_result.diagnoses:
                    found_diagnosis_codes.add(result_diagnosis.code)

        diagnoses = HeartDiagnosis.objects.filter(code__in=found_diagnosis_codes).order_by("id")
        diagnosis_code_map = {d.code: d for d in diagnoses}

        results = []

        for model_result in model_inference_results:
            result_item = DiagnosisModelInferenceResult(model=model_result.model)

            if model_result.error is None:
                for result_diagnosis in model_result.diagnoses:
                    result_item.diagnoses.append(
                        DiagnosisModelInferenceResult.DiagnosisResult(
                            diagnosis=diagnosis_code_map[result_diagnosis.code],
                            confidence=result_diagnosis.confidence,
                            is_true=result_diagnosis.is_true,
                        )
                    )
            else:
                result_item.error = model_result.error

            results.append(result_item)

        results.sort(key=lambda res: res.model.id)

        return Response(DiagnosisModelInferenceResultSetSerializer({"count": len(results), "results": results}).data)


class EcgModelCountView(APIView):
    @swagger_auto_schema(responses={200: openapi.Response("", schema=openapi.Schema(type=openapi.TYPE_INTEGER))})
    def get(self, request, pk):
        try:
            ecg = Electrocardiogram.objects.get(pk=pk)
        except Electrocardiogram.DoesNotExist:
            raise NotFound

        # NOTE: на данный момент нет моделей, поддерживающих ЭКГ загруженных в виде картинок
        if ecg.image is not None:
            return Response(0)

        type_corresponding_diagnoses_models = get_corresponding_diagnoses_models(ecg)

        return Response(len(type_corresponding_diagnoses_models))


class UploadEcgSourceView(APIView):
    serializer_class = EcgUploadSerializer
    parser_classes = [MultiPartParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = get_logger(self)

    def get_serializer(self):
        return self.serializer_class()

    class _FileTemplate:
        def __init__(self, file, file_type):
            self.file = file
            self.file_type = file_type

    @swagger_auto_schema(responses={200: openapi.Response("", schema=EcgUploadResultSerializer)})
    def post(self, request):
        # TODO: check permissions

        user = request.user
        created_at = timezone.now()

        collection_id = request.data.get("collection", None)
        if collection_id is not None:
            collection = Collection.objects.get(id=collection_id)
        else:
            collection = Collection.objects.get(name=DEFAULT_COLLECTION_NAME)

        raw_files = request.data.getlist("files", [])
        if len(raw_files) == 0:
            return Response(status=status.HTTP_204_NO_CONTENT)

        file_templates = []
        errors = []
        for raw_file in raw_files:
            head, file_ext = path.splitext(raw_file.name)
            if file_ext == ".edf":
                file_type = SourceFileType.EDF
            elif file_ext == ".dcm":
                file_type = SourceFileType.DICOM
            else:
                errors.append({"file": raw_file.name, "error": Exception(f"Тип файла {file_ext} не поддерживается")})
                continue

            file, created = get_or_store_file_stream(raw_file.name, raw_file.file, collection, user, created_at)
            file_templates.append(UploadEcgSourceView._FileTemplate(file, file_type))

        ecg_sources = []
        if len(file_templates) > 0:
            ecg_sources = list(
                EcgSource.objects.filter(files__file__in=[ft.file for ft in file_templates])
                .select_related("ecg")
                .prefetch_related("files")
                .distinct("id")
            )

        used_ecg_sources_file_ids = set()
        existing_ecg_ids = []
        for ecg_source in ecg_sources:
            if ecg_source.status == SourceFileStatus.PROCESSED:
                existing_ecg_ids.append(ecg_source.ecg.id)

                for ecg_source_file in ecg_source.files.all():
                    used_ecg_sources_file_ids.add(ecg_source_file.file_id)

        unused_file_templates = [ft for ft in file_templates if ft.file.id not in used_ecg_sources_file_ids]

        new_ecg_ids = []
        for file_template in unused_file_templates:
            ecg_source = EcgSource(status=SourceFileStatus.UPLOADED, created_by=user, created_at=created_at)
            ecg_source.save()

            ecg_sources.append(ecg_source)

            ecg_source_file = EcgSourceFile(
                source=ecg_source,
                file=file_template.file,
                type=file_template.file_type,
                created_by=user,
                created_at=created_at,
            )
            ecg_source_file.save()

            if file_template.file_type == SourceFileType.DICOM:
                run_result = DicomSourceProcessingFunction(user).run(ecg_source=ecg_source)
            elif file_template.file_type == SourceFileType.EDF:
                run_result = ProcessEdfSourceFileFunction(user).run(
                    options=ProcessEdfSourceFileFunctionRunOptions(), ecg_source=ecg_source
                )
            else:
                raise Exception("unknown file type")

            if run_result.status == FunctionRunStatus.SUCCESS:
                new_ecg_ids.append(run_result.run.side_effects["ecg"])

            if run_result.status == FunctionRunStatus.FAIL:
                errors.append({"file": file_template.file.name.name, "error": run_result.error})

        return Response(
            EcgUploadResultSerializer(
                {
                    "existing_electrocardiograms": existing_ecg_ids,
                    "new_electrocardiograms": new_ecg_ids,
                    "errors": errors,
                }
            ).data
        )
