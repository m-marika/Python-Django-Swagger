from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models

from api.common.models import (
    Entity,
    ManagerBuilder,
    NotDeletedEntityManager,
    ReadOnlyEntity,
    ReadOnlyDataEntity,
)
from api.processing.models import Data
from api.questionnaire.models import Questionnaire, AnswerOption, ConditionKind, QuestionnaireResult
from api.storage.models import File

User = get_user_model()


class Diagnosis(Entity):
    title = models.CharField(max_length=255)
    scp_ecg = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "diagnoses"
        default_related_name = "diagnoses_related"
        verbose_name_plural = "diagnoses"


class Eos(Entity):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "eos"
        default_related_name = "eos_related"
        verbose_name_plural = "eos"


class Classifier(Entity):
    name = models.CharField(max_length=255)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "classifier"
        default_related_name = "classifier_related"
        verbose_name_plural = "classifier"


class HeartDiagnosis(Entity):
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    classifier = models.ForeignKey(Classifier, on_delete=models.CASCADE, null=True, related_name="diagnoses")

    def __str__(self):
        return self.title

    class Meta:
        db_table = "heart_diagnoses"
        default_related_name = "heart_diagnoses_related"
        verbose_name_plural = "heart diagnoses"


class EcgInterpretationRule(Entity):
    name = models.CharField(max_length=255)
    classifier = models.ForeignKey(Classifier, on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE, null=True, blank=True, related_name="+")

    def __str__(self):
        return f"{self.name} - {self.classifier} - {self.questionnaire}"

    class Meta:
        db_table = "ecg_interpretation_rule"
        default_related_name = "rule_related"


class EcgInterpretationRuleItem(Entity):
    condition_kind = models.IntegerField(choices=ConditionKind.choices)
    group = models.CharField(max_length=1024, null=True, blank=True)
    rule = models.ForeignKey(EcgInterpretationRule, on_delete=models.CASCADE, related_name="items")
    answer_option = models.ManyToManyField(AnswerOption, related_name="answer_options")
    diagnoses = models.ForeignKey(HeartDiagnosis, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "ecg_interpretation_rule_item"
        default_related_name = "ecg_interpretation_rule_item_related"


class EcgResultInterpretation(Entity):
    rule = models.ForeignKey(EcgInterpretationRule, on_delete=models.CASCADE, related_name="+")
    diagnoses = models.ManyToManyField(HeartDiagnosis, related_name="+")
    result = models.ForeignKey(QuestionnaireResult, on_delete=models.CASCADE)

    class Meta:
        db_table = "ecg_result_interpretation"


class Report(Entity):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    electrocardiogram = models.ForeignKey("Electrocardiogram", on_delete=models.CASCADE, related_name="reports")
    heart_diagnoses = models.ManyToManyField(HeartDiagnosis, related_name="hearts")
    comment = models.TextField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)
    pq = models.FloatField(null=True, blank=True)
    eos = models.ForeignKey("Eos", on_delete=models.CASCADE)
    aqrs_invalid = models.BooleanField(null=True, blank=True)
    has_artifacts = models.BooleanField(null=True, blank=True)
    heart_rate = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user}.{self.id}: {self.result}"

    class Meta:
        db_table = "reports"
        default_related_name = "reports"


class EcgType(Entity):
    name = models.CharField(max_length=512)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "ecg_types"
        default_permissions = ()


class Electrocardiogram(Entity):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, null=True, blank=True)
    p = models.FloatField(null=True, blank=True)
    pq = models.FloatField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    qrs = models.FloatField(null=True, blank=True)
    qt = models.FloatField(null=True, blank=True)
    aqrs = models.IntegerField(null=True, blank=True)
    delta_rr_rr = models.FloatField(null=True, blank=True)
    sex = (("1", "мужчина"), ("2", "женщина"))
    gender = models.CharField(max_length=100, choices=sex, null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    rr_best_qrs = models.FloatField(null=True, blank=True)
    image = models.ForeignKey(File, on_delete=models.PROTECT, default=None, null=True, blank=True)
    types = models.ManyToManyField(EcgType, related_name="+")

    objects_fully_prefetched = (
        ManagerBuilder(NotDeletedEntityManager).select_related("patient", "image__collection__storage").build()
    )

    def __str__(self):
        return f"{self.id}: {self.patient}"

    class Meta:
        db_table = "electrocardiograms"
        default_related_name = "electrocardiograms"


class EcgInterpretation(Entity):
    ecg = models.ForeignKey(Electrocardiogram, on_delete=models.CASCADE)
    source = models.CharField(max_length=1024, blank=True, null=True, editable=False)
    diagnoses = models.ManyToManyField(HeartDiagnosis, related_name="interpretations")
    result_interpretation = models.ForeignKey(EcgResultInterpretation, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        db_table = "ecg_interpretation"


class Patient(Entity):
    sex = (("1", "мужчина"), ("2", "женщина"))
    gender = models.CharField(max_length=100, choices=sex)
    birthday = models.DateField()

    def __str__(self):
        return f"{self.gender}: {self.birthday}"

    class Meta:
        db_table = "patients"
        default_related_name = "patients"


class ElectrocardiogramSetOrderingField(Entity):
    name = models.CharField(max_length=255)
    order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.id}: {self.name}"

    class Meta:
        db_table = "electrocardiogram_set_ordering_field"
        default_related_name = "electrocardiogram_set_ordering_field"


class ElectrocardiogramSet(Entity):
    title = models.CharField(max_length=255)
    ordering_field = models.ForeignKey(
        "ElectrocardiogramSetOrderingField", on_delete=models.CASCADE, null=True, blank=True
    )
    order_type = (("1", "GLOBAL"), ("2", "USER"))
    ordering_type = models.CharField(max_length=10, choices=order_type)
    electrocardiograms = models.ManyToManyField(Electrocardiogram)
    electrocardiogram_ids = ArrayField(models.IntegerField(), size=100, null=True, blank=True, editable=False)
    add_to_tail = models.BooleanField(null=True, blank=True, default=True)

    def __str__(self):
        return f"{self.id}: {self.title}"

    class Meta:
        db_table = "electrocardiogram_set"
        default_related_name = "electrocardiogram_set"


class ElectrocardiogramSetUserOrder(Entity):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="+")
    order_type = (("1", "нет"), ("3", "случайный"))
    order = models.CharField(max_length=10, choices=order_type)
    electrocardiogram_set = models.ForeignKey("ElectrocardiogramSet", on_delete=models.CASCADE)
    electrocardiogram = models.ForeignKey("Electrocardiogram", on_delete=models.CASCADE, blank=True)
    electrocardiogram_ids = ArrayField(models.IntegerField(), size=100, null=True, blank=True, editable=False)
    add_to_tail = models.BooleanField(null=True, blank=True, default=True)

    def __str__(self):
        return f"{self.user}: {self.electrocardiogram_set}"

    class Meta:
        db_table = "electrocardiogram_set_user_order"
        default_related_name = "electrocardiogram_set_user_order"


class SourceFileStatus(models.IntegerChoices):
    UPLOADED = 0, "Загружен"
    PROCESSED = 1, "Обработан"
    ERROR = 100, "Ошибка"


class SourceFileType(models.IntegerChoices):
    UNKNOWN = 0, "не известен"
    EDF = 1, "edf"
    EDF_PLUS = 2, "edf+"
    BDF = 3, "bdf"
    BDF_PLUS = 4, "bdf+"
    SCP = 5, "scp"
    JSON = 6, "json"
    CSV = 7, "csv"
    DICOM = 8, "dicom"


class EcgSource(ReadOnlyEntity):
    ecg = models.ForeignKey(Electrocardiogram, on_delete=models.CASCADE, null=True, blank=True, editable=False)
    status = models.IntegerField(choices=SourceFileStatus.choices)

    class Meta:
        db_table = "sources"
        default_permissions = ()


class EcgSourceFile(ReadOnlyEntity):
    source = models.ForeignKey(EcgSource, on_delete=models.CASCADE, editable=False, related_name="files", null=True)
    file = models.ForeignKey(File, on_delete=models.PROTECT, null=True, blank=True, editable=False)
    path = models.CharField(max_length=1024, null=True, blank=True, editable=False)
    type = models.IntegerField(choices=SourceFileType.choices, editable=False)

    class Meta:
        db_table = "source_files"
        default_permissions = ()


class EcgLeadType(Entity):
    id = models.IntegerField(primary_key=True, editable=False)
    name = models.CharField(max_length=32)
    scp_code = models.IntegerField()
    description = models.CharField(max_length=1024)
    iso_reference = models.CharField(max_length=1024, null=True, blank=True)

    class Meta:
        db_table = "lead_types"
        default_permissions = ()


class EcgData(ReadOnlyDataEntity):
    ecg = models.ForeignKey(Electrocardiogram, on_delete=models.CASCADE)
    data = models.OneToOneField(Data, on_delete=models.PROTECT)

    class Meta:
        db_table = "ecg_data"
        default_permissions = ()


class ServiceRunners(models.TextChoices):
    DIAGNOSIS_PREDICTION_MODEL_RUNNER = "diagnosis-prediction-runner-v1", "Запрос модели предсказания диагнозов ЭКГ"
    STUB_DIAGNOSIS_PREDICTION_MODEL_RUNNER = (
        "stub-diagnosis-prediction-runner-v1",
        "Заглушка запроса модели предсказания диагнозов ЭКГ",
    )


class EcgDiagnosesPredictionExternalModel(Entity):
    name = models.CharField(max_length=1024)
    version = models.IntegerField()
    description = models.CharField(max_length=2048)
    runner = models.CharField(max_length=256, choices=ServiceRunners.choices)
    url = models.URLField(max_length=2048)
    diagnoses = models.ManyToManyField(HeartDiagnosis, related_name="+", through="EcgDiagnosesToModelLink")
    ecg_types = models.ManyToManyField(EcgType, related_name="+", blank=True)

    class Meta:
        db_table = "ecg_diagnoses_prediction_external_models"
        default_permissions = ()


class EcgDiagnosesToModelLink(models.Model):
    ecg_model = models.ForeignKey(
        EcgDiagnosesPredictionExternalModel, on_delete=models.CASCADE, related_name="+", editable=False
    )
    diagnosis = models.ForeignKey(HeartDiagnosis, on_delete=models.CASCADE, related_name="+", editable=False)
    minimal_confidence = models.FloatField()

    class Meta:
        db_table = "ecg_diagnosis_to_model_links"
        default_permissions = ()


class DiagnosisModelInferenceResult:
    class DiagnosisResult:
        def __init__(self, *, diagnosis, confidence, is_true):
            self.diagnosis = diagnosis
            self.confidence = confidence
            self.is_true = is_true

    def __init__(self, *, model, diagnoses=None, error=None):
        if diagnoses is None:
            diagnoses = []

        self.model = model
        self.diagnoses = diagnoses
        self.error = error


class DiagnosesModelInferenceError(Exception):
    pass
