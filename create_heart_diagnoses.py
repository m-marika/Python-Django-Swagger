from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone
from api.common.db import reset_sequences

from api.common.models import User
from ...models import HeartDiagnosis, Classifier

created_by = User(id=1)
created_at = timezone.now()


class _Template:
    entity = None


class _PathologyTemplate(_Template):
    def __init__(
        self,
        title,
        code,
        classifier,
        details=None,
    ):
        self.title = title
        self.code = code
        self.details = details
        self.classifier = classifier


class Command(BaseCommand):
    # noinspection PyMethodMayBeStatic
    def __create_entity(self, model, id, **kwargs):
        return model.objects.create(created_by=created_by, created_at=created_at, **kwargs)

    # noinspection PyMethodMayBeStatic
    def __create_or_update_entity(self, model, id, **kwargs):
        obj, created = model.objects.update_or_create(
            id=id, defaults={"created_by": created_by, "created_at": created_at, **kwargs}
        )
        return obj, created

    pathology_index = 1

    def __create_pathology(self, pathology_templates):
        result = []
        for pathology_template in pathology_templates:
            if pathology_template.entity is not None:
                result.append((pathology_template.entity, False, pathology_template))
            else:
                pathology, o_created = self.__create_or_update_entity(
                    HeartDiagnosis,
                    self.pathology_index,
                    title=pathology_template.title,
                    code=pathology_template.code,
                    classifier=pathology_template.classifier,
                )
                result.append((pathology, o_created, pathology_template))
                pathology_template.entity = pathology
                self.pathology_index += 1
        return result

    def handle(self, *args, **options):
        with transaction.atomic():
            classifier = Classifier(id=1)

            def after_commit():
                reset_sequences("ecg")

            transaction.on_commit(after_commit)

            self.__create_pathology(
                [
                    _PathologyTemplate(title="Ненормально для возраста", code="ABFA", classifier=classifier),
                    _PathologyTemplate(title="Норма для возраста", code="NFA", classifier=classifier),
                    _PathologyTemplate(title="Нормальная ЭКГ", code="NORM", classifier=classifier),
                    _PathologyTemplate(title="Миграция водителя ритма", code="WANDP", classifier=classifier),
                    _PathologyTemplate(title="Выраженная синусовая аритмия", code="MSAR", classifier=classifier),
                    _PathologyTemplate(title="Синоатриальная блокада", code="SABLK", classifier=classifier),
                    _PathologyTemplate(title="Пауза или остановка синусового узла", code="SAR", classifier=classifier),
                    _PathologyTemplate(title="Синусовая аритмия", code="SARRH", classifier=classifier),
                    _PathologyTemplate(title="Синусовая брадикардия", code="SBRAD", classifier=classifier),
                    _PathologyTemplate(title="Синусовый ритм", code="SR", classifier=classifier),
                    _PathologyTemplate(title="Синусовая тахикардия", code="STACH", classifier=classifier),
                    _PathologyTemplate(title="Ускоренный желудочковый ритм", code="ACVR", classifier=classifier),
                    _PathologyTemplate(title="Желудочковый ритм", code="VRHYT", classifier=classifier),
                    _PathologyTemplate(
                        title="Остановка синусового узла с замещением на желудочковый ритм",
                        code="SARV",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(title="Желудочковая тахикардия", code="VTACH", classifier=classifier),
                    _PathologyTemplate(title="Фибрилляция желудочков", code="VFIB", classifier=classifier),
                    _PathologyTemplate(title="Трепетание желудочков", code="VFLT", classifier=classifier),
                    _PathologyTemplate(title="Ускоренный узловой ритм", code="ACJR", classifier=classifier),
                    _PathologyTemplate(title="Фибрилляция предсердий", code="AFIB", classifier=classifier),
                    _PathologyTemplate(title="Трепетание предсердий", code="AFLT", classifier=classifier),
                    _PathologyTemplate(
                        title="Пароксизмальная наджелудочковая тахикардия", code="PSVT", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Атриовентрикулярная узловая реципрокная тахикардия", code="AVNRT", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Атриовентрикулярная реципрокная тахикардия", code="AVRT", classifier=classifier
                    ),
                    _PathologyTemplate(title="Эктопический предсердный ритм", code="EAR", classifier=classifier),
                    _PathologyTemplate(title="Узловая брадикардия", code="JBRAD", classifier=classifier),
                    _PathologyTemplate(title="Узловой ритм", code="JRHYT", classifier=classifier),
                    _PathologyTemplate(title="Узловая тахикардия", code="JTACH", classifier=classifier),
                    _PathologyTemplate(
                        title="Эктопическая предсердная тахикардия, мультифокальная", code="MFAT", classifier=classifier
                    ),
                    _PathologyTemplate(title="Нижний правопредсердный ритм", code="RAR", classifier=classifier),
                    _PathologyTemplate(
                        title="Остановка синусового узла с замещением на предсердный ритм",
                        code="SARA",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Остановка синусового узла с замещением на узловой ритм",
                        code="SARJ",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Остановка синусового узла с замещением на наджелудочковый ритм",
                        code="SARSV",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(title="Наджелудочковая аритмия", code="SVARR", classifier=classifier),
                    _PathologyTemplate(title="Наджелудочковый ритм", code="SVRHY", classifier=classifier),
                    _PathologyTemplate(title="Наджелудочковая тахикардия", code="SVTAC", classifier=classifier),
                    _PathologyTemplate(title="Предсердная тахикардия", code="ATACH", classifier=classifier),
                    _PathologyTemplate(title="Аритмия, происхождение неизвестно", code="ARRHY", classifier=classifier),
                    _PathologyTemplate(
                        title="Брадикардия, происхождение неизвестно или не указано",
                        code="BRADO",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Мультифокальная тахикардия (полиморфная), наджелудочковая или желудочковая",
                        code="MTACH",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(title="Тахикардия с узким комплексом QRS", code="NQTAC", classifier=classifier),
                    _PathologyTemplate(
                        title="Тахикардия, происхождение неизвестно или не указано", code="TACHO", classifier=classifier
                    ),
                    _PathologyTemplate(title="Неустановленный ритм", code="UNRHY", classifier=classifier),
                    _PathologyTemplate(
                        title="Тахикардия с широким комплексом QRS", code="WQTAC", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Блокированная предсердная экстрасистола", code="BPAC", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Выскальзывающие комплексы, источник неизвестен", code="ESCUN", classifier=classifier
                    ),
                    _PathologyTemplate(title="Выскальзывающие узловые комплексы", code="JEC", classifier=classifier),
                    _PathologyTemplate(
                        title="Выскальзывающие наджелудочковые комплексы", code="SVEC(S)", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Выскальзывающие желудочковые комплексы", code="VEC(S)", classifier=classifier
                    ),
                    _PathologyTemplate(title="Сливные комплексы", code="FUSC(S)", classifier=classifier),
                    _PathologyTemplate(
                        title="Групповые интерполированные желудочковые экстрасистолы",
                        code="MVICS",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(title="Желудочковая тахикардия, устойчивая", code="SVT", classifier=classifier),
                    _PathologyTemplate(
                        title="Желудочковая тахикардия, неустойчивая", code="NSVT", classifier=classifier
                    ),
                    _PathologyTemplate(title="Желудочковая парасистолия", code="VPARA", classifier=classifier),
                    _PathologyTemplate(
                        title="Желудочковая экстрасистола (экстрасистолия)", code="PVC", classifier=classifier
                    ),
                    _PathologyTemplate(title="Парные желудочковые экстрасистолы", code="PVPCS", classifier=classifier),
                    _PathologyTemplate(title="Пробежка желудочковых экстрасистол", code="RPVCS", classifier=classifier),
                    _PathologyTemplate(title="Пробежка желудочковой тахикардии", code="RVTAC", classifier=classifier),
                    _PathologyTemplate(
                        title="Желудочковая тахикардия, типа «пируэт»", code="TORSA", classifier=classifier
                    ),
                    _PathologyTemplate(title="Желудочковая бигеминия", code="VBIG", classifier=classifier),
                    _PathologyTemplate(title="Желудочковая тригемения", code="VTRIG", classifier=classifier),
                    _PathologyTemplate(
                        title="Интерполированные желудочковые экстрасистолы", code="VIC", classifier=classifier
                    ),
                    _PathologyTemplate(title="Желудочковая квадригеминия", code="VQUAG", classifier=classifier),
                    _PathologyTemplate(title="Наджелудочковая бигеминия", code="SVBIG", classifier=classifier),
                    _PathologyTemplate(
                        title="Интерполированная наджелудочковая экстрасистола (экстрасистолия)",
                        code="SVIC(S)",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(title="Наджелудочковые экстрасистолы", code="SVPCS", classifier=classifier),
                    _PathologyTemplate(title="Наджелудочковая тригеминия", code="SVTRI", classifier=classifier),
                    _PathologyTemplate(
                        title="Аберрантные экстрасистолы, источник неизвестен", code="ABPCS", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Бигеминия (наджелудочковая либо желудочковая)", code="BIGU", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Тригеминия (наджелудочковая либо желудочковая)", code="TRIGU", classifier=classifier
                    ),
                    _PathologyTemplate(title="Предсердная бигеминия", code="ABIG", classifier=classifier),
                    _PathologyTemplate(title="Предсердная тригеминия", code="ATRIG", classifier=classifier),
                    _PathologyTemplate(title="Предсердная экстрасистолия", code="PAC", classifier=classifier),
                    _PathologyTemplate(title="Парные предсердные экстрасистолы", code="PAPCS", classifier=classifier),
                    _PathologyTemplate(title="Пробежка предсердной тахикардии", code="RATAC", classifier=classifier),
                    _PathologyTemplate(
                        title="Узловая экстрасистола (экстрасистолия)", code="JPC(S)", classifier=classifier
                    ),
                    _PathologyTemplate(title="Парные узловые экстрасистолы", code="PJPCS", classifier=classifier),
                    _PathologyTemplate(title="Пробежка узловых экстрасистол", code="RJPCS", classifier=classifier),
                    _PathologyTemplate(title="Пробежка узловой тахикардии", code="RJTAC", classifier=classifier),
                    _PathologyTemplate(title="Ускоренная АВ-проводимость", code="AAVCO", classifier=classifier),
                    _PathologyTemplate(title="Синдром Вольфа - Паркинсона - Уайта", code="WPW", classifier=classifier),
                    _PathologyTemplate(title="АВ-блокада 1-й степени", code="1AVB", classifier=classifier),
                    _PathologyTemplate(
                        title="АВ-блокада 2-й степени типа Мобиц I (Венкебах)", code="WENCK", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="АВ-блокада 2-й степени типа Мобиц II", code="MOBI2", classifier=classifier
                    ),
                    _PathologyTemplate(title="АВ-блокада 3-й степени (полная)", code="3AVB", classifier=classifier),
                    _PathologyTemplate(title="АВ-диссоциация", code="AVDIS", classifier=classifier),
                    _PathologyTemplate(title="Удлинение интервала PR", code="LRR", classifier=classifier),
                    _PathologyTemplate(title="Короткий интервал PR", code="SHTPR", classifier=classifier),
                    _PathologyTemplate(
                        title="АВ-блокада с изменяющимся коэффициентом проведения", code="VARBL", classifier=classifier
                    ),
                    _PathologyTemplate(title="Коэффициент АВ проводимости 2:1", code="C2T1", classifier=classifier),
                    _PathologyTemplate(title="Коэффициент АВ проводимости 3:1", code="C3T1", classifier=classifier),
                    _PathologyTemplate(
                        title="Аномальный прирост зубца R в грудных отведениях", code="ABRPR", classifier=classifier
                    ),
                    _PathologyTemplate(title="Горизонтальное положение ЭОС", code="AXHOR", classifier=classifier),
                    _PathologyTemplate(title="Неопределенная ЭОС", code="AXIND", classifier=classifier),
                    _PathologyTemplate(title="Нормальное положение ЭОС", code="AXNOR", classifier=classifier),
                    _PathologyTemplate(title="Вертикальное положение ЭОС", code="AXVER", classifier=classifier),
                    _PathologyTemplate(title="Электрическая альтернация", code="ELALT", classifier=classifier),
                    _PathologyTemplate(title="Высокий вольтаж QRS", code="HVOLT", classifier=classifier),
                    _PathologyTemplate(title="Отклонение ЭОС влево", code="LAD", classifier=classifier),
                    _PathologyTemplate(
                        title="Низкий вольтаж QRS в отведениях от конечностей и грудных отведениях",
                        code="LVOLT",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Малый прирост зубца R в грудных отведениях", code="POORR", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Высокий зубец R в правых грудных отведениях", code="PROMR", classifier=classifier
                    ),
                    _PathologyTemplate(title="Отклонение ЭОС вправо", code="RAD", classifier=classifier),
                    _PathologyTemplate(
                        title="Электрическая ось сердца по типу S1-S2-S3", code="S1S23", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Смещение переходной зоны в грудных отведениях влево", code="TRNZL", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Смещение переходной зоны в грудных отведениях вправо",
                        code="TRNZR",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Аберрантная проводимость наджелудочковых сокращений",
                        code="ABER(S)",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(title="Аномальная ось P", code="ABPAX", classifier=classifier),
                    _PathologyTemplate(title="Отклонение QRS от нормы", code="ABQRS", classifier=classifier),
                    _PathologyTemplate(
                        title="Полная блокада левой ножки пучка Гиса", code="CLBBB", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Полная блокада правой ножки пучка Гиса", code="CRBBB", classifier=classifier
                    ),
                    _PathologyTemplate(title="Эпсилон-волна", code="EPSW", classifier=classifier),
                    _PathologyTemplate(
                        title="Нарушение внутрипредсердной проводимости", code="IACA", classifier=classifier
                    ),
                    _PathologyTemplate(title="Задержка проведения в предсердии", code="IACD", classifier=classifier),
                    _PathologyTemplate(
                        title="Неполная блокада левой ножки пучка Гиса", code="ILBBB", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Неполная блокада правой ножки пучка Гиса", code="IRBBB", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Задержка внутрижелудочковой проводимости", code="IVCD", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Блокада передней ветви левой ножки пучка Гиса", code="LAFB", classifier=classifier
                    ),
                    _PathologyTemplate(title="Блокада левой ножки пучка Гиса", code="LBBB", classifier=classifier),
                    _PathologyTemplate(
                        title="Блокада задней ветви левой ножки пучка Гиса", code="LPFB", classifier=classifier
                    ),
                    _PathologyTemplate(title="Неспецифические аномалии зубца P", code="NSPEP", classifier=classifier),
                    _PathologyTemplate(
                        title="Перегрузка/расширение обоих предсердий", code="BAO/BAE", classifier=classifier
                    ),
                    _PathologyTemplate(title="Гипертрофия обоих желудочков", code="BVH", classifier=classifier),
                    _PathologyTemplate(title="Увеличение левого предсердия", code="LAO/LAE", classifier=classifier),
                    _PathologyTemplate(title="Гипертрофия левого желудочка", code="LVH", classifier=classifier),
                    _PathologyTemplate(title="Высокий зубец R в отведении V1", code="PRANT", classifier=classifier),
                    _PathologyTemplate(title="Увеличение правого предсердия", code="RAO/ RAE", classifier=classifier),
                    _PathologyTemplate(title="Гипертрофия правого желудочка", code="RVH", classifier=classifier),
                    _PathologyTemplate(
                        title="Критерии вольтажа (QRS) для гипертрофии левого желудочка",
                        code="VCLVH",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Критерии вольтажа (QRS) для гипертрофии правого желудочка",
                        code="VCRVH",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в переднебоковой стенке левого желудочка",
                        code="ALMI",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в передней стенке левого желудочка", code="AMI", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в верхушке левого желудочка", code="APMI", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в переднеперегородочной области левого желудочка",
                        code="ASMI",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в верхнем отделе боковой стенки левого желудочка",
                        code="HLMI",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в нижнебоковой области", code="ILMI", classifier=classifier
                    ),
                    _PathologyTemplate(title="Локализация ИМ в нижней области", code="IMI", classifier=classifier),
                    _PathologyTemplate(
                        title="Локализация ИМ в нижней задней боковой стенке левого желудочка",
                        code="IPLMI",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в нижней (задней) области", code="IPMI", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Локализация ИМ в боковой стенке левого желудочка", code="LMI", classifier=classifier
                    ),
                    _PathologyTemplate(title="Инфаркт миокарда", code="MI", classifier=classifier),
                    _PathologyTemplate(title="Локализация ИМ в задней области", code="PMI", classifier=classifier),
                    _PathologyTemplate(title="Наличие зубцов Q", code="QWAVE", classifier=classifier),
                    _PathologyTemplate(title="Удлинение интервала QT", code="LNGQT", classifier=classifier),
                    _PathologyTemplate(title="Короткий интервал QT", code="SHTQT", classifier=classifier),
                    _PathologyTemplate(title="Дигиталисный эффект", code="DIG", classifier=classifier),
                    _PathologyTemplate(
                        title="Неспецифическая депрессия сегмента ST", code="STDxx", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Изменения ST-T связанные с наличием желудочковой аневризмы",
                        code="ANEUR",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Изменения ST-T, совместимые с легочной эмболией", code="PULM", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Изменения сегмента ST, обусловленные работой ЭКС", code="ACET", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Неспецифическая элевация сегмента ST", code="STE_", classifier=classifier
                    ),
                    _PathologyTemplate(title="Ранняя реполяризация", code="REPOL", classifier=classifier),
                    _PathologyTemplate(
                        title="Электролитные или лекарственные нарушения", code="NSTEL", classifier=classifier
                    ),
                    _PathologyTemplate(title="Предположительно гипокальциемия", code="HPOCA", classifier=classifier),
                    _PathologyTemplate(title="Предположительно гипокалиемия", code="HPOK", classifier=classifier),
                    _PathologyTemplate(title="Предположительно гиперкальциемия", code="HPRCA", classifier=classifier),
                    _PathologyTemplate(title="Предположительно гиперкалиемия", code="HPRK", classifier=classifier),
                    _PathologyTemplate(
                        title="Субэндокардиальное повреждение в переднебоковых отведениях",
                        code="INJAL",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Субэндокардиальное повреждение в переднеперегородочных отведениях",
                        code="INJAS",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Субэндокардиальное повреждение в нижнебоковых отведениях",
                        code="INJIL",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Субэндокардиальное повреждение в нижних отведениях", code="INJIN", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Субэндокардиальное повреждение в боковых отведениях", code="INJLA", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Неспецифические ишемические изменения ST-T", code="ISC_", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в передне-нижних отведениях", code="ISCAF", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в переднебоковых отведениях", code="ISCAL", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в передних отведениях", code="ISCAN", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в переднеперегородочных отведениях",
                        code="ISCAS",
                        classifier=classifier,
                    ),
                    _PathologyTemplate(
                        title="Диффузные ишемические изменения ST-T", code="ISCDI", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в нижнебоковых отведениях", code="ISCIL", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в нижних отведениях", code="ISCIN", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в боковых отведениях", code="ISCLA", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Ишемические изменения в задней области", code="ISCPO", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Изменения ST-T, совместимые с перикардитом", code="PERIC", classifier=classifier
                    ),
                    _PathologyTemplate(
                        title="Неспецифическая депрессия сегмента ST", code="STD_", classifier=classifier
                    ),
                    _PathologyTemplate(title="Высокий вольтаж зубцов Т", code="HTVOL", classifier=classifier),
                    _PathologyTemplate(title="Инверсия зубца Т", code="INVT", classifier=classifier),
                    _PathologyTemplate(title="Низкая амплитуда зубцов Т", code="LOWT", classifier=classifier),
                    _PathologyTemplate(title="Неспецифические изменения зубца Т", code="NT_", classifier=classifier),
                    _PathologyTemplate(title="Отклонение от нормы зубца Т", code="TAB_", classifier=classifier),
                    _PathologyTemplate(title="Декстрокардия", code="DXTRO", classifier=classifier),
                    _PathologyTemplate(title="Блокада правой ножки пучка Гиса", code="RBBB", classifier=classifier),
                ]
            )
