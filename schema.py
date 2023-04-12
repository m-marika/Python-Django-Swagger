from unicodedata import numeric
import graphene
from django.utils import timezone
from graphene_django.types import DjangoObjectType, ObjectType
from django.contrib.auth.models import User
from .models import Eos, Diagnosis, HeartDiagnosis, Report, Electrocardiogram, Patient
from graphene_django.rest_framework.mutation import SerializerMutation
from .serializers import (
    DiagnosesSerializer,
    EosSerializer,
    Heart_diagnosesSerializer,
    PatientsElectroSerializer,
    ElectrocardiogramCreateUpdateGraphQL,
    ReportsCreateUpdateSerializer,
)
import graphene_django_optimizer as gql_optimizer


class UserType(DjangoObjectType):
    class Meta:
        model = User


class EosType(DjangoObjectType):
    class Meta:
        model = Eos


class DiagnosisType(DjangoObjectType):
    class Meta:
        model = Diagnosis


class HeartDiagnosisType(DjangoObjectType):
    class Meta:
        model = HeartDiagnosis


class ReportType(DjangoObjectType):
    class Meta:
        model = Report


class ElectrocardiogramType(DjangoObjectType):
    class Meta:
        model = Electrocardiogram


class PatientType(DjangoObjectType):
    class Meta:
        model = Patient


class Query(ObjectType):

    # User

    user = graphene.Field(UserType, id=graphene.Int())
    user_all = graphene.List(UserType)

    def resolve_user(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return User.objects.get(pk=id)
        return None

    def resolve_user_all(self, info, **kwargs):
        return User.objects.prefetch_related("groups").all()

    """ def resolve_current_user_detail(self, info, **kwargs): # TODO
        return User.objects.prefetch_related("groups").all() """

    # EOS
    eos = graphene.Field(EosType, id=graphene.Int())
    eos_all = graphene.List(EosType)
    eos_count = graphene.Int()

    def resolve_eos(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return Eos.objects.get(pk=id)
        return None

    def resolve_eos_all(self, info, **kwargs):
        return Eos.objects.all()

    def resolve_eos_count(self, info, **kwargs):
        return Eos.objects.count()

    # Diagnosis

    diagnosis = graphene.Field(DiagnosisType, id=graphene.Int())
    diagnosis_all = graphene.List(DiagnosisType)
    diagnosis_count = graphene.Int()

    def resolve_diagnosis(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return Diagnosis.objects.get(pk=id)
        return None

    def resolve_diagnosis_all(self, info, **kwargs):
        return Diagnosis.objects.all()

    def resolve_diagnosis_count(self, info, **kwargs):
        return Diagnosis.objects.count()

    # HeartDiagnosis

    heart_diagnosis = graphene.Field(HeartDiagnosisType, id=graphene.Int())
    heart_diagnosis_all = graphene.List(HeartDiagnosisType)
    heart_diagnosis_count = graphene.Int()

    def resolve_heart_diagnosis(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return HeartDiagnosis.objects.get(pk=id)
        return None

    def resolve_heart_diagnosis_all(self, info, **kwargs):
        return HeartDiagnosis.objects.all()

    def resolve_heart_diagnosis_count(self, info, **kwargs):
        return HeartDiagnosis.objects.count()

    # Report

    report = graphene.Field(ReportType, id=graphene.Int())
    reports = graphene.List(ReportType)
    reports_opt = graphene.List(ReportType)
    reports_count = graphene.Int()

    def resolve_report(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return gql_optimizer.query(Report.objects.get(pk=id), info)
        return None

    def resolve_reports(self, info, **kwargs):
        return gql_optimizer.query(Report.objects.all(), info)

    def resolve_reports_count(self, info, **kwargs):
        return Report.objects.count()

    # Electrocardiogram

    electrocardiogram = graphene.Field(ElectrocardiogramType, id=graphene.Int())
    electrocardiograms = graphene.List(ElectrocardiogramType)
    electrocardiograms_count = graphene.Int()
    electrocardiogram_reports = graphene.String()

    def resolve_electrocardiogram(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return gql_optimizer.query(Electrocardiogram.objects.get(pk=id), info)
        return None

    def resolve_electrocardiograms(self, info, **kwargs):
        return gql_optimizer.query(Electrocardiogram.objects.all(), info)

    def resolve_electrocardiograms_count(self, info, **kwargs):
        return Electrocardiogram.objects.count()

    def resolve_electrocardiogram_reports(self, info, **kwargs):

        return "electrocardiograms/reports/"

    # Patient

    patient = graphene.Field(PatientType, id=graphene.Int())
    patients = graphene.List(PatientType)
    patients_count = graphene.Int()

    def resolve_patient(self, info, **kwargs):
        id = kwargs.get("id")
        if id is not None:
            return gql_optimizer.query(Patient.objects.get(pk=id), info)
        return None

    def resolve_patients(self, info, **kwargs):
        return gql_optimizer.query(Patient.objects.all(), info)

    def resolve_patients_count(self, info, **kwargs):
        return Patient.objects.count()


# mutations for eos
class CreateOrUpdateEos(SerializerMutation):
    class Meta:
        serializer_class = EosSerializer
        model_operations = ["create", "update"]
        lookup_field = "id"

    @classmethod
    def get_serializer_kwargs(cls, self, request, **input):
        if "id" in input:
            instance = Eos.objects.filter(id=input["id"], created_by=request.context.user).first()

            if instance:
                instance.updated_at = timezone.now()
                instance.updated_by = request.context.user
                return {"instance": instance, "data": input, "partial": True}

        return {"data": input, "partial": True}


class DeleteEos(graphene.Mutation):
    class Arguments:
        ids = graphene.List(graphene.ID)

    class Meta:
        output = graphene.String

    def mutate(self, info, **kwargs):

        deleted_eos = []
        not_deleted_eos = []

        for eos in Eos.objects.filter(id__in=kwargs["id"]):
            if eos is not None:
                deleted_eos.append(eos.id)
                eos.delete()

        id = [int(x) for x in kwargs["id"]]
        not_deleted_eos = [x for x in id if x not in deleted_eos]

        return f"deleted_eos = {deleted_eos} not_deleted_eos = {not_deleted_eos}"


# Create mutations for diagnosis
class CreateOrUpdateDiagnosis(SerializerMutation):
    class Meta:
        serializer_class = DiagnosesSerializer
        model_operations = ["create", "update"]
        lookup_field = "id"

    @classmethod
    def get_serializer_kwargs(cls, self, request, **input):
        if "id" in input:
            instance = Diagnosis.objects.filter(id=input["id"], created_by=request.context.user).first()

            if instance:
                instance.updated_at = timezone.now()
                instance.updated_by = request.context.user
                return {"instance": instance, "data": input, "partial": True}

        return {"data": input, "partial": True}


class DeleteDiagnosis(graphene.Mutation):
    class Arguments:
        id = graphene.List(graphene.ID)

    class Meta:
        output = graphene.String

    def mutate(self, info, **kwargs):

        deleted_diagnosis = []
        not_deleted_diagnosis = []

        for diagnosis in Diagnosis.objects.filter(id__in=kwargs["id"]):
            if diagnosis is not None:
                deleted_diagnosis.append(diagnosis.id)
                diagnosis.delete()

        id = [int(x) for x in kwargs["id"]]
        not_deleted_diagnosis = [x for x in id if x not in deleted_diagnosis]

        return f"deleted_diagnosis = {deleted_diagnosis} not_deleted_diagnosis = {not_deleted_diagnosis}"


# Create mutations for HeartDiagnosis
class CreateOrUpdateHeartDiagnosis(SerializerMutation):
    class Meta:
        serializer_class = Heart_diagnosesSerializer
        model_operations = ["create", "update"]
        lookup_field = "id"

    @classmethod
    def get_serializer_kwargs(cls, self, request, **input):
        if "id" in input:
            instance = HeartDiagnosis.objects.filter(id=input["id"], created_by=request.context.user).first()

            if instance:
                instance.updated_at = timezone.now()
                instance.updated_by = request.context.user
                return {"instance": instance, "data": input, "partial": True}

        return {"data": input, "partial": True}


class DeleteHeartDiagnosis(graphene.Mutation):
    class Arguments:
        id = graphene.List(graphene.ID)

    class Meta:
        output = graphene.String

    def mutate(self, info, **kwargs):

        deleted_heartDiagnosis = []
        not_deleted_heartDiagnosis = []

        for heartDiagnosis in HeartDiagnosis.objects.filter(id__in=kwargs["id"]):
            if heartDiagnosis is not None:
                deleted_heartDiagnosis.append(heartDiagnosis.id)
                heartDiagnosis.delete()

        id = [int(x) for x in kwargs["id"]]
        not_deleted_heartDiagnosis = [x for x in id if x not in deleted_heartDiagnosis]

        return f"deleted_heartDiagnosis = {deleted_heartDiagnosis} not_deleted_heartDiagnosis = {not_deleted_heartDiagnosis}"


# Create mutations for Report
def create_heart_diagnoses(input):
    result = []
    for i in input["heart_diagnoses"]:
        if i.isnumeric():
            result.append(i)

    input["heart_diagnoses"] = result
    return result


class CreateOrUpdateReport(SerializerMutation):
    class Meta:
        serializer_class = ReportsCreateUpdateSerializer
        model_operations = ["create", "update"]
        lookup_field = "id"

    @classmethod
    def get_serializer_kwargs(cls, self, request, **input):
        print("input = ", input)
        if "id" in input:
            instance = (
                Report.objects.select_related("electrocardiogram", "created_by", "eos", "user")
                .prefetch_related(
                    "heart_diagnoses",
                    "heart_diagnoses__created_by",
                    "eos__created_by",
                    "electrocardiogram__patient",
                    "electrocardiogram__image__collection",
                )
                .filter(id=input["id"], created_by=request.context.user)
                .first()
            )

            print("instance = ", instance)

            if instance:
                instance.updated_at = timezone.now()
                instance.updated_by = request.context.user
                input["heart_diagnoses"] = create_heart_diagnoses(input)
                return {"instance": instance, "data": input, "partial": True}

        # Не подтягивает связь ManyToManyField из модели, поэтому делаем из строки массив чисел
        # (должен быть способ лучше) #TODO
        input["heart_diagnoses"] = create_heart_diagnoses(input)

        return {"data": input, "partial": True}


class DeleteReport(graphene.Mutation):
    class Arguments:
        id = graphene.List(graphene.ID)

    class Meta:
        output = graphene.String

    def mutate(self, info, **kwargs):

        deleted_report = []
        not_deleted_report = []

        for report in gql_optimizer.query(Report.objects.filter(id__in=kwargs["id"]), info):
            if report is not None:
                deleted_report.append(report.id)
                report.delete()

        id = [int(x) for x in kwargs["id"]]
        not_deleted_report = [x for x in id if x not in deleted_report]

        return f"deleted_report = {deleted_report} not_deleted_report = {not_deleted_report}"


# Create mutations for Electrocardiogram
class CreateOrUpdateElectrocardiogram(SerializerMutation):
    class Meta:
        serializer_class = ElectrocardiogramCreateUpdateGraphQL
        model_operations = ["create", "update"]
        lookup_field = "id"

    @classmethod
    def get_serializer_kwargs(cls, self, request, **input):
        if "id" in input:
            instance = (
                Electrocardiogram.objects.select_related("patient", "created_by", "image__collection__storage")
                .prefetch_related(
                    "reports__eos",
                    "reports__created_by",
                    "reports__user",
                    "reports__heart_diagnoses",
                )
                .filter(id=input["id"], created_by=request.context.user)
                .first()
            )

            if instance:
                instance.updated_at = timezone.now()
                instance.updated_by = request.context.user
                return {"instance": instance, "data": input, "partial": True}

        return {"data": input, "partial": True}


class DeleteElectrocardiogram(graphene.Mutation):
    class Arguments:
        id = graphene.List(graphene.ID)

    class Meta:
        output = graphene.String

    def mutate(self, info, **kwargs):

        deleted_electrocardiogram = []
        not_deleted_electrocardiogram = []

        for electrocardiogram in gql_optimizer.query(Electrocardiogram.objects.filter(id__in=kwargs["id"]), info):
            if electrocardiogram is not None:
                deleted_electrocardiogram.append(electrocardiogram.id)
                electrocardiogram.delete()

        id = [int(x) for x in kwargs["id"]]
        not_deleted_electrocardiogram = [x for x in id if x not in deleted_electrocardiogram]

        return f"deleted_electrocardiogram = {deleted_electrocardiogram} not_deleted_electrocardiogram = {not_deleted_electrocardiogram}"


# mutations for Patient
class CreateOrUpdatePatient(SerializerMutation):
    class Meta:
        serializer_class = PatientsElectroSerializer
        model_operations = ["create", "update"]
        lookup_field = "id"

    @classmethod
    def get_serializer_kwargs(cls, self, request, **input):
        if "id" in input:
            instance = (
                Patient.objects.select_related("created_by")
                .prefetch_related(
                    "electrocardiograms",
                    "electrocardiograms__image__collection",
                )
                .filter(id=input["id"], created_by=request.context.user)
                .first()
            )

            if instance:
                instance.updated_at = timezone.now()
                instance.updated_by = request.context.user
                return {"instance": instance, "data": input, "partial": True}

        return {"data": input, "partial": True}


class DeletePatient(graphene.Mutation):
    class Arguments:
        id = graphene.List(graphene.ID)

    class Meta:
        output = graphene.String

    def mutate(self, info, **kwargs):

        deleted_patient = []
        not_deleted_patient = []

        for patient in gql_optimizer.query(Patient.objects.filter(id__in=kwargs["id"]), info):
            if patient is not None:
                deleted_patient.append(patient.id)
                patient.delete()

        id = [int(x) for x in kwargs["id"]]
        not_deleted_patient = [x for x in id if x not in deleted_patient]

        return f"deleted_patient = {deleted_patient} not_deleted_patient = {not_deleted_patient}"


class Mutation(graphene.ObjectType):
    createOrUpdateEos = CreateOrUpdateEos.Field()
    deleteEos = DeleteEos.Field()

    createOrUpdateDiagnosis = CreateOrUpdateDiagnosis.Field()
    deleteDiagnosis = DeleteDiagnosis.Field()

    createOrUpdateHeartDiagnosis = CreateOrUpdateHeartDiagnosis.Field()
    deleteHeartDiagnosis = DeleteHeartDiagnosis.Field()

    createOrUpdateReport = CreateOrUpdateReport.Field()
    deleteReport = DeleteReport.Field()

    createOrUpdateElectrocardiogram = CreateOrUpdateElectrocardiogram.Field()
    deleteElectrocardiogram = DeleteElectrocardiogram.Field()

    createOrUpdatePatient = CreateOrUpdatePatient.Field()
    deletePatient = DeletePatient.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
