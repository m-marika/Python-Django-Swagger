from django.urls import path
from graphene_django.views import GraphQLView

from . import views

# from django.views.decorators.csrf import csrf_exempt  # для отключения IDE GraphiQL

urlpatterns = [
    path("users/", views.UserList.as_view()),
    path("groups/", views.GroupList.as_view()),
    path("groups/<int:pk>/", views.GroupDetail.as_view()),
    path("users/<int:pk>/", views.UserDetail.as_view()),
    path("users/current/", views.CurrentUserDetail.as_view()),
    path("users/current/permissions/", views.CurrentUserPermissions.as_view()),
    path("diagnoses/", views.DiagnosesViewSet.as_view()),
    path("diagnoses/<int:pk>/", views.DiagnosesDetView.as_view()),
    path("diagnoses/count/", views.DiagnosesCountView.as_view()),
    path("patients/", views.PatientsListView.as_view()),
    path("patients/<int:pk>/", views.PatientDetailView.as_view()),
    path("patients/count/", views.PatientCountView.as_view()),
    path("electrocardiograms/", views.ElectrocardiogramsListView.as_view()),
    path("electrocardiograms/<int:pk>/", views.ElectrocardiogramsDetailView.as_view()),
    path("electrocardiograms/<int:pk>/leads/", views.ElectrocardiogramLeadListView.as_view()),
    path("electrocardiograms/<int:pk>/tasks/", views.ElectrocardiogramListTasksView.as_view()),
    path("electrocardiograms/count/", views.ElectrocardiogramsCountView.as_view()),
    path("electrocardiograms/reports/", views.ElectrocardiogramsAllReportsListView.as_view()),
    path("eos/", views.EosListView.as_view()),
    path("eos/<int:pk>/", views.EosDetailView.as_view()),
    path("eos/count/", views.EosCountView.as_view()),
    path("heart-diagnoses/", views.Heart_diagnosesListView.as_view()),
    path("heart-diagnoses/<int:pk>/", views.Heart_diagnosesDetailView.as_view()),
    path("heart-diagnoses/count/", views.Heart_diagnosesCountView.as_view()),
    path("reports/", views.ReportsListView.as_view()),
    path("reports/<int:pk>/", views.ReportsDetailView.as_view()),
    path("reports/count/", views.ReportsCountView.as_view()),
    path("electrocardiogram-set/", views.ElectrocardiogramSetView.as_view()),
    path("electrocardiogram-set/<int:pk>/", views.ElectrocardiogramSetDetailView.as_view()),
    path("elset/count/<int:pk>/", views.ElectrocardiogramSetCountView.as_view()),
    path("electrocardiogram-set-order/", views.ElectrocardiogramSetOrderingFieldView.as_view()),
    path("electrocardiogram-set-order/<int:pk>/", views.ElectrocardiogramSetOrderingFieldDetailView.as_view()),
    path("electrocardiogram-set-user/", views.ElectrocardiogramSetUserView.as_view()),
    path("electrocardiogram-set-user/<int:pk>/", views.ElectrocardiogramSetUserOrderDetailView.as_view()),
    path(
        "electrocardiogram-sets/<int:pk>/electrocardiograms/<int:el_id>/<str:list>/",
        views.ElectrocardiogramSetNextPreviousView.as_view(),
    ),
    path("electrocardiogram-set-user/group/", views.ElectrocardiogramSetUserGroupView.as_view()),
    path("electrocardiogram-set/<int:pk>/re-order", views.ElectrocardiogramSetUserGroupUpdateOrderView.as_view()),
    path(
        "graphql/", GraphQLView.as_view(graphiql=True)
    ),  # path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=False)))
    path("ecg-interpretation/", views.EcgInterpretationListView.as_view()),
    path("ecg-interpretation-rule/", views.QuestionnaireInterpretationRuleListView.as_view()),
    path("ecg-interpretation-rule/<int:pk>/", views.QuestionnaireInterpretationRuleDetailView.as_view()),
    path("ecg-interpretation-rule/count/", views.QuestionnaireInterpretationRuleCountView.as_view()),
    path("ecg-interpretation-rule-item/", views.QuestionnaireInterpretationRuleItemListView.as_view()),
    path(
        "ecg-interpretation-rule-item/<int:pk>/",
        views.QuestionnaireInterpretationRuleItemDetailView.as_view(),
    ),
    path("ecg-interpretation-rule-item/count/", views.QuestionnaireInterpretationRuleItemCountView.as_view()),
    path("ecg-result-interpretation/", views.QuestionnaireResultInterpretationListView.as_view()),
    path(
        "ecg-result-interpretation/<int:pk>/",
        views.QuestionnaireResultInterpretationDetailView.as_view(),
    ),
    path("ecg-result-interpretation/count/", views.QuestionnaireResultInterpretationCountView.as_view()),
    path(
        "ecg-result-interpretation-calc/result/<int:result_id>/rule/<int:rule_id>/",
        views.QuestionnaireResultInterpretationCalcListView.as_view(),
    ),
    path(
        "ecg-result-interpretation-calc/<int:pk>/refresh/",
        views.QuestionnaireResultInterpretationCalcDetailView.as_view(),
    ),
    path("electrocardiograms/<int:pk>/model-inference-results/", views.EcgModelInferenceView.as_view()),
    path("electrocardiograms/<int:pk>/models/count/", views.EcgModelCountView.as_view()),
    path("electrocardiograms/upload/", views.UploadEcgSourceView.as_view()),
]
