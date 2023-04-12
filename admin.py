from django.contrib import admin
from django.db import models
from django.db.models import Count, Aggregate, F, Value

from api.questionnaire.models import AnswerOption

# from ..questionnaire.admin import AnswerOptionsInline

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
    EcgLeadType,
    Classifier,
    EcgInterpretationRule,
    EcgInterpretationRuleItem,
    EcgType,
    EcgDiagnosesPredictionExternalModel,
)
from ..common.admin import CommonAdmin


@admin.register(Diagnosis)
class DiagnosisAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["title", "scp_ecg", "created_at"])


@admin.register(Classifier)
class ClassifierAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["name", "details", "created_at"])


@admin.register(EcgInterpretationRule)
class QuestionnaireInterpretationRuleAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.search_fields = ["rule"]

        self.add_list_display(["name", "classifier", "questionnaire", "created_at"])


class AnswerOptionsInline(admin.TabularInline):
    model = AnswerOption
    extra = 1
    raw_id_fields = ("answer",)
    autocomplete_fields = ("option",)


@admin.register(EcgInterpretationRuleItem)
class QuestionnaireInterpretationRuleItemAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["rule", "condition_kind", "group", "diagnoses", "created_at"])
        self.fields = ["rule", "condition_kind", "group", "diagnoses", "answer_option"]
        self.filter_horizontal = ("answer_option",)
        self.autocomplete_fields = ["answer_option"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset


@admin.register(Eos)
class EosAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["title", "created_at", "created_by"])


@admin.register(HeartDiagnosis)
class HeartDiagnosisAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["title", "code", "created_at", "created_by"])
        self.search_fields = ["diagnoses"]


@admin.register(Report)
class ReportAdmin(CommonAdmin):
    raw_id_fields = (
        "created_by",
        "user",
        "electrocardiogram",
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["user", "electrocardiogram", "heart_count", "created_at", "user"])
        self.filter_horizontal = ("heart_diagnoses",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("user", "electrocardiogram__patient", "user")

        queryset = queryset.annotate(
            heart_count=Count("heart_diagnoses", distinct=True),
        )

        return queryset

    def heart_count(self, obj):
        return obj.heart_count

    heart_count.short_description = "heart_diagnoses"


class ReportInline(admin.TabularInline):
    model = Report
    can_delete = False
    exclude = ("created_by", "updated_by", "is_deleted")

    def get_queryset(self, request):
        queryset = (
            super(ReportInline, self)
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("eos", "heart_diagnoses")
        )

        if request.user.is_superuser:
            return queryset

        return queryset.filter(user=request.user)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        return False


@admin.register(Electrocardiogram)
class ElectrocardiogramAdmin(CommonAdmin):
    raw_id_fields = (
        "created_by",
        "patient",
        "image",
    )
    inlines = (ReportInline,)

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["patient", "type_list", "report_count", "created_at", "created_by"])
        self.autocomplete_fields = ("types",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("patient", "created_by", "image__collection__storage")
        queryset = queryset.annotate(
            report_count=Count("reports", distinct=True),
            type_list=Aggregate(
                F("types__name"),
                Value(", "),
                function="STRING_AGG",
                output_field=models.CharField(),
            ),
        )
        return queryset

    def report_count(self, obj):
        return obj.report_count

    report_count.short_description = "reports"

    def type_list(self, obj):
        return obj.type_list

    type_list.short_description = "types"

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "reports":
            kwargs["queryset"] = Report.objects.filter(owner=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Patient)
class PatientAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["birthday", "gender", "ecg_count", "created_at", "created_by"])

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            ecg_count=Count("electrocardiograms", distinct=True),
        )
        return queryset

    def ecg_count(self, obj):
        return obj.ecg_count

    ecg_count.short_description = "electrocardiograms"


@admin.register(ElectrocardiogramSet)
class ElectrocardiogramSetAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["ordering_type", "electrocardiogram_ids", "ecg_set_count", "created_at", "created_by"])
        self.filter_horizontal = ("electrocardiograms",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            ecg_set_count=Count("electrocardiograms", distinct=True),
        )
        return queryset

    def ecg_set_count(self, obj):
        return obj.ecg_set_count

    ecg_set_count.short_description = "electrocardiograms"


@admin.register(ElectrocardiogramSetUserOrder)
class ElectrocardiogramSetUserAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(
            ["user", "electrocardiogram_set", "electrocardiogram", "order", "created_at", "created_by"]
        )


@admin.register(ElectrocardiogramSetOrderingField)
class ElectrocardiogramSetOrderingFieldAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["name", "order", "created_at", "created_by"])


@admin.register(EcgLeadType)
class EcgLeadTypeAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["name"])


@admin.register(EcgType)
class EcgTypeAdmin(CommonAdmin):
    search_fields = ("name",)

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        self.add_list_display(["name"])


@admin.register(EcgDiagnosesPredictionExternalModel)
class EcgDiagnosesPredictionExternalModelAdmin(CommonAdmin):
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.autocomplete_fields = ("ecg_types",)
        self.add_list_display(["name", "version", "description", "type_list"])

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            type_list=Aggregate(
                F("ecg_types__name"),
                Value(", "),
                function="STRING_AGG",
                output_field=models.CharField(),
            ),
        )
        return queryset

    def type_list(self, obj):
        return obj.type_list

    type_list.short_description = "types"
