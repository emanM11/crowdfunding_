"""
seed_data — generate rich, realistic Arabic demo data.

Idempotent: users are matched by email, categories by slug, projects by
title, and all nested content (donations, updates, rewards, comments,
ratings, images) is only created for projects that did not already exist.
Running the command twice never duplicates records.

Usage:

    python manage.py seed_data [--projects 15] [--backers-per-project 12]

Demo accounts all share the password: TakafulDemo@2026
"""

import io
import random
from decimal import Decimal
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import text as text_utils
from django.utils import timezone
from PIL import Image, ImageDraw

from accounts.models import User
from core.models import Comment, Rating
from projects.models import Category, Donation, Project, ProjectImage, ProjectUpdate, RewardTier, Tag

DEMO_PASSWORD = 'TakafulDemo@2026'
EGYPTIAN_PREFIXES = ['010', '011', '012', '015']

# faker has no ar_EG *person* provider in the pinned version (40.38.0), so
# Faker('ar_EG').first_name() silently falls back to English names. Use
# curated Egyptian names instead of importing English names into an Arabic
# demo dataset.
MALE_FIRST_NAMES = [
    'أحمد', 'محمد', 'مصطفى', 'كريم', 'عمر', 'يوسف', 'خالد', 'تامر',
    'حسام', 'محمود', 'باسل', 'إسلام', 'هشام', 'زياد', 'عبدالرحمن', 'مهاب',
]
FEMALE_FIRST_NAMES = [
    'منى', 'سارة', 'نورهان', 'هدى', 'رنا', 'أسماء', 'دينا', 'إيمان',
    'ليلى', 'شيماء', 'رضوى', 'فاطمة', 'أمل', 'هند', 'مريم', 'ياسمين',
]
LAST_NAMES = [
    'الشناوي', 'عبدالعظيم', 'فؤاد', 'إبراهيم', 'حسن', 'مصطفى', 'سامي',
    'محمود', 'عادل', 'الشريف', 'جابر', 'فتحي', 'عبدالله', 'سيد', 'منصور',
    'رشدي', 'عودة', 'سمير', 'عبدالرازق', 'النجار', 'عاطف', 'حلمي', 'رجب',
    'عوض', 'طارق', 'سعيد', 'نبيل', 'الخطيب', 'سالم', 'عيسى',
]

BIO_TEMPLATES = [
    'بصممت حياتي على إن فكرة صغيرة تتحتمل لو حد صدّق فيها. بشارك المجتمع في بناء حاجة حقيقية.',
    'مهتمة بالمساحات اللي التغيير فيها بيحصل فعلاً — المدارس، المستشفيات، والأسواق المحلية.',
    'أؤمن إن كل جنيه بيتجمع صح يقدر يغيّر سيرة عيلة أو مدينة. حريصة على الشفافية في كل حاجة.',
    'شيف وفنان أكل شعبي، بصدّق إن المشاريع المصرية تبدأ من المطبخ والورشة قبل أي حاجة تانية.',
    'بشتغل في التقنية ومن المبادرات اللي بتعلّم جيل جديد مهارات برمجة حقيقية وتفكير منطقي.',
    'بساعد المشاريع الناشئة تحوّل فكرتها لخطة تشغيل قابلة للتنفيذ، الأرقام بتحكي الحكاية.',
    'فنانة تشكيلية، بستثمر الفن في تحويل المساحات العامة لحاجة تفرح الناس وتلمهم.',
    'من البحيرة، وبحاول أوثّق تجارب الزراعة العضوية عشان تتحول لممارسة أوسع في الدلتا.',
    'مدرّبة مهنية عندي شغف بتمكين الستات في المشروعات المنزلية الصغيرة.',
    'طبيب بشري بمشارك في كل المبادرات الصحية اللي بتقرب الخدمة لسكان القرى.',
    'مهندس بيئة، وبشتغل على حلول نظيفة للمياه والطاقة للأحياء غير المخدمة.',
    'شابة من أسوان، وبتبني منصة ببيع بيها منتجات الحرف اليدوية من مدار المدن.',
    'مصوّر ومخرج وثائقي، بحكي قصص الناس اللي شايلين التراث المصري على كتافهم.',
    'ريادي أعمال، بدمج الاستدامة بالربحية عشان المشروع يعيش بعد ما ينتهي التمويل.',
]

UPDATE_TITLES = [
    'شكرًا على دعمكم — بدأنا التنفيذ',
    'أول تقرير تقدم: الأرقام والأثر',
    'خطوة جديدة: التعاقد مع الموردين',
    'وصول أول دفعة تجهيزات',
    'تحديث ميداني من موقع العمل',
    'لقاء المساندين ونبذة عن المرحلة القادمة',
]

UPDATE_BODIES = [
    'الحمد لله، الأسبوع ده شهدنا التعاقد مع الشركة المنفذة وتم بدء الأعمال التمهيدية. سننشر صورًا '
    'وتقارير دورية كل أسبوعين، وأي تأخير هنعلنه بوضوح مع السبب.',
    'عدد المساهمين زاد عن المتوقع، والحمد لله تم توجيه جزء من التمويل لتغطية تكاليف النقل للقرى '
    'المجاورة. التقرير المالي الكامل متاح عند الطلب.',
    'تم شراء أغلب التجهيزات الأساسية والبدء في تركيبها. الجدول الزمني يسير كما هو مخطط له، ونأمل '
    'إنهاء المرحلة الأولى قبل نهاية الشهر.',
    'تم تأمين الترخيص الرسمي بعد استكمال الأوراق المطلوبة مع الوحدة المحلية. ده معناه إننا نقدر '
    'نبدأ التشغيل التجريبي الأسبوع المقبل.',
    'أخذنا ملاحظاتكم في التعليقات بعين الاعتبار، وعدّلنا الأولويات: التشغيل أولاً ثم التوسع. زيارات '
    'المتابعة مفتوحة لأي مساند يريد أن يرى المشروع على أرض الواقع.',
    'انتهت المرحلة الأولى بنجاح، وسنعلن قريبًا عن فعالية مفتوحة للمساندين للاحتفال بنتائج المرحلة.',
]

REWARD_TEMPLATES = [
    'شكر وتقدير: رسالة شكر عبر البريد واسمك على صفحة الموقع',
    'نامة رقمية: إصدار حصري بمحتوى خلف الكواليس والقصص الكاملة',
    'قطعة مميزة: منتج ملموس يوضّل لحد باب البيت (تكلفة الشحن داخل مصر)',
    'تذكرة فعالية: حضور حفل إطلاق أو جولة ميدانية للمشروع',
    'بطاقة شكر خاصة: بطاقة مخطوطة من فريق المشروع مع صورة موقعة',
]

RATINGS_POOL = [3, 4, 4, 5, 5, 5]

# Unspash photo ids — reused from the existing demo (all real photo ids).
PHOTO_POOL = [
    '1509391366360-2e959784a276', '1503676260728-1c00da094a0b', '1580582932707-520aed937b7b',
    '1579684385127-1ef15d508118', '1584433144859-1fc3ab64a957', '1519494026892-80bbd2d6fd0d',
    '1509440159596-0249088772ff', '1555507036-ab1f4038808a', '1599058917212-d750089bc07e',
    '1548839140-29a749e1cf4d', '1501785888041-af3ef285b470', '1470252649378-9c29740c9fa8',
    '1522202176988-66273c2fd55f', '1517180102446-f3ece451e9d8', '1498050108023-c5249f4df085',
    '1608042314453-ae338d80c427', '1512436991641-6745cdb1723f', '1543825619-7d5a7cf51a4d',
    '1625246333195-78d9c38ad449', '1464226184884-fa280b87c399', '1434682881908-b43d0467b798',
    '1516979187457-637abb4f9353', '1517824806704-9040b037703b', '1517048676732-d65bc937f952',
    '1472162072942-cd5147eb3902', '1523240795612-9a054b0db644', '1531482615713-2afd69097998',
    '1504674900247-0877df9cc836', '1555400038-63f5ba517a47', '1512058564366-18510be2db19',
    '1532996122724-e3c354a0b15b', '1558618720-8bd7b7a6634b', '1504307661254-35680f356dfd',
    '1461896836934-ffe607ba8211', '1579952363873-27f3bade9f55', '1571019613454-1cb2f99b2d8b',
    '1511707171634-5f897ff02aa9', '1519389950473-47ba0277781c', '1488190211105-8b0e65b80b4e',
    '1536265309753-0da95d80d2f4', '1500530855697-b586d89ba3ee', '1506967439472-bc5dfa4f1e63',
    '1478720568477-152d9b164e26', '1485846234645-a62644f84728', '1516035069371-29a1b244cc32',
    '1517248135467-4c7edcad34c4', '1556910103-1c02745aae4d', '1550547660-d9450f859349',
    '1512149177596-f817c7dd5c79', '1534639464436-12205de0511f', '1523614059038-f4ceb0b71dec',
]


# ---------------------------------------------------------------------------
# Categories (slug, name)
# ---------------------------------------------------------------------------
def _categories():
    return [
        ('التقنية', 'تقنية'),
        ('فنون إبداعية', 'فنون'),
        ('المجتمع', 'مجتمع'),
        ('البيئة والطاقة', 'بيئة'),
        ('الصحة', 'صحة'),
        ('التعليم', 'تعليم'),
        ('المشروعات الصغيرة', 'مشروعات-صغيرة'),
        ('الرياضة', 'رياضة'),
    ]


# ---------------------------------------------------------------------------
# Projects — title, details, category key, target (EGP), pct funded,
# start days ago, end days ahead/behind, status, featured, tags.
# ---------------------------------------------------------------------------
def _projects():
    return [
        {
            'title': 'ألواح شمسية لمدرسة قروية في سوهاج',
            'details': (
                'مدرسة أبو تيج الابتدائية بتعتمد على الكهرباء الحكومية اللي بتتفصل كتير في الشتاء، '
                'وبتسبب ده في وقف الدروس والمعامل. الحملة هدفها تركيب ألواح شمسية لتشغيل الإضاءة '
                'والمراوح وأجهزة العرض طول اليوم الدراسي.\n\n'
                'التكلفة شاملة التركيب، الصيانة لسنتين، وتدريب مدرسين على تشغيل النظام. أي تعليمة '
                'مش بتكفي هتتحول لتشغيل ميكروباص مدرسي للمواصلات.'
            ),
            'category': 'بيئة', 'target': 260000, 'pct': 81, 'start_offset': 38, 'end_offset': 52,
            'status': 'running', 'featured': True, 'tags': ['طاقة شمسية', 'تعليم', 'الريف'],
        },
        {
            'title': 'جهاز أشعة إكس رقمي لمستشفى القرية في المنيا',
            'details': (
                'مركز رعاية القرية في ملوي بيخدم أكتر من 40 ألف مواطن، وأقرب جهاز أشعة على بعد 60 '
                'كيلو. المرضى بينضطروا يسافروا بدري جدًا ويدفعوا من جيوبهم.\n\n'
                'الهدف توفير جهاز أشعة رقمي حديث ومستلزمات التشغيل الأولية. المستشفى هتتكفل بالتشغيل '
                'والصيانة، وكل قرى الصعيد الحوالين هتستفيد بشكل مباشر.'
            ),
            'category': 'صحة', 'target': 520000, 'pct': 66, 'start_offset': 22, 'end_offset': 68,
            'status': 'running', 'featured': False, 'tags': ['رعاية صحية', 'معدات طبية', 'صعيد مصر'],
        },
        {
            'title': 'منصة أسطوانات تعليمية بالمحمول لطلاب الثانوية',
            'details': (
                'تطبيق بيشرح المنهج المصري بالفيديو والاختبارات التفاعلية، ومصمم يشتغل على أضعف '
                'الأجهزة وأبطأ النت عشان يوصل لكل طالب في كل محافظة.\n\n'
                'التمويل هيغطي تسجيل أول 3 سنين من المحتوى، استضافة سحابية، وفريق مراجعة تربوية. '
                'الاشتراك هيبقى مجاني للطلاب الغير قادرين.'
            ),
            'category': 'تقنية', 'target': 460000, 'pct': 70, 'start_offset': 25, 'end_offset': 65,
            'status': 'running', 'featured': True, 'tags': ['تعليم', 'تطبيقات موبايل', 'منهج مصري'],
        },
        {
            'title': 'مياه نظيفة لكل بيت في الدقهلية',
            'details': (
                'ست قرى في مركز السنبلاوين بتحصل على مياه بيها ملوثات عالية، وبيتغذى منها خصوصًا '
                'أطفال المدارس. الحملة بتشتغل مع الوحدة المحلية على محطة معالجة صغيرة وشبكة توزيع '
                'بطاقة تكفي القرى كلها.\n\n'
                'بعد التشغيل هتضاف محطات قياس جودة شهرية يقوم بيها مهندسين متطوعين، والنتايج هتتنشر '
                'علنًا.'
            ),
            'category': 'بيئة', 'target': 190000, 'pct': 94, 'start_offset': 55, 'end_offset': 18,
            'status': 'running', 'featured': True, 'tags': ['مياه', 'قرى', 'صحة عامة'],
        },
        {
            'title': 'أكاديمية برمجة لشباب الصعيد',
            'details': (
                'مبادرة بتدرب 200 شاب وشابة من محافظات الصعيد على أساسيات البرمجة وتطوير الويب عن '
                'بُعد، مع سكن ووجبات للمحتاجين في معسكرات نهاية الأسبوع.\n\n'
                'الميزانية بتغطي مدربين متخصصين، لابتوبات للملتحقين الغير قادرين، وشهادات معتمدة. '
                'الخريجين هيتوظفوا مع شركات تقنية شريكة أو يشتغلوا فريلانس.'
            ),
            'category': 'تقنية', 'target': 410000, 'pct': 27, 'start_offset': 12, 'end_offset': 75,
            'status': 'running', 'featured': False, 'tags': ['برمجة', 'تدريب', 'شباب'],
        },
        {
            'title': 'ورشة حلي وإكسسوارات بإيدين بنات أسوان',
            'details': (
                'فريق من 12 بنت من أسوان بيصنع حلي وإكسسوارات من خامات محلية (خرز، جلد، تقبلة) '
                'ويبيعها في المواسم السياحية. المشروع ده بيديهن دخل ثابت بدل الشغل الموسمي.\n\n'
                'التمويل هيشتري خامات بكميات كبيرة (توفير 30% من التكلفة)، ماكينة درزة، وحسابات '
                'تسويق على السوشيال ميديا.'
            ),
            'category': 'فنون', 'target': 125000, 'pct': 38, 'start_offset': 20, 'end_offset': 40,
            'status': 'running', 'featured': False, 'tags': ['حرف يدوية', 'تمكين المرأة', 'صناعة محلية'],
        },
        {
            'title': 'مزرعة عضوية صديقة للبيئة في البحيرة',
            'details': (
                'مزرعة عيلة أبو العز في إدكو هتتحول لزراعة عضوية بالكامل: بيدر سماد، اقتصاد في استهلاك '
                'المياه، وترشيد الأسمدة. التجربة هتتوتق وتتشارك مع 50 مزارع في المنطقة.\n\n'
                'الهدف شراء تقاوي عضوية، شبكة ري بالتنقيط، وشهادة تصديق عشان المنتج يتباع بسعر عادل '
                'في الأسواق.'
            ),
            'category': 'بيئة', 'target': 300000, 'pct': 55, 'start_offset': 30, 'end_offset': 60,
            'status': 'running', 'featured': False, 'tags': ['زراعة عضوية', 'أمن غذائي', 'ري'],
        },
        {
            'title': 'مهرجان جداريات: دعم فنانين الشارع في القاهرة',
            'details': (
                'مبادرة فنية بتحول واجهات عمارات المناطق الشعبية لجداريات ملونة، وبتوفر مصدر دخل '
                'مؤقت لفنانين الجرافيتي وفنون الشارع في مصر.\n\n'
                'الميزانية بتغطي خامات الطلاء، تصاريح المحافظة، وبدل الأجير للفنانين المشاركين. '
                'مع نهاية المهرجان هيتوثق كل الجداريات في ألبوم رقمي.'
            ),
            'category': 'فنون', 'target': 150000, 'pct': 20, 'start_offset': 8, 'end_offset': 35,
            'status': 'running', 'featured': True, 'tags': ['فن', 'جداريات', 'ثقافة'],
        },
        {
            'title': 'شنط مدرسية وكتب لكل طالب في أسوان',
            'details': (
                'مع بداية السنة الدراسية، كتير من أولاد أسوان بيحضروا المدرسة من غير شنطة ولا أدوات '
                'كتابة. الحملة بتجمع شنط مدرسية متكاملة وتوزعها على طلاب المدارس الحكومية الأكثر '
                'احتياجًا.\n\n'
                'كل جنيه هيتحول لشنطة حقيقية توصل بالنيابة عنك لأولاد العيلة، واللجنة المحلية '
                'بتساعدنا في تحديد المستفيدين بشفافية تامة.'
            ),
            'category': 'تعليم', 'target': 85000, 'pct': 100, 'start_offset': 90, 'end_offset': 10,
            'status': 'ended', 'featured': False, 'tags': ['تعليم', 'أطفال', 'تساوي فرص'],
        },
        {
            'title': 'سلسلة ساندويتشات صحية من جامعة المنصورة',
            'details': (
                'أربع خريجات تجارة بينظموا مطعم صغير متنقل قدام كلية الهندسة ببيع ساندويتشات صحية '
                'بأسعار الطلبة. المشروع نجح في الموقع التجريبي وبيحتاج رسملة عشان يبقى فرع تاني '
                'وتشغيل عربتين.\n\n'
                'التمويل يغطي معدات المطبخ، سيارة مجهزة، ورأس مال خامات أول شهر، وخطة التشغيل '
                'اتعملت مع محاسب مستقل.'
            ),
            'category': 'مشروعات-صغيرة', 'target': 200000, 'pct': 9, 'start_offset': 10, 'end_offset': 55,
            'status': 'running', 'featured': False, 'tags': ['مشروع صغير', 'وجبات', 'شباب'],
        },
        {
            'title': 'إعادة تدوير البلاستيك في الإسكندرية',
            'details': (
                'المبادرة بتجمع زجاجات البلاستيك من مطاعم وشواطئ الإسكندرية وتشغلها لرقائق معاد '
                'تدويرها عبر وحدة فرز وتكسير صغيرة هتشتغل بيها 8 عمال من المنطقة.\n\n'
                'الإيراد من بيع الرقائق هيمول تشغيل الوحدة، والعائد بيستثمر في توسعة شبكة الجمع في '
                'حي كامل.'
            ),
            'category': 'بيئة', 'target': 600000, 'pct': 12, 'start_offset': 18, 'end_offset': 80,
            'status': 'running', 'featured': False, 'tags': ['إعادة تدوير', 'بلاستيك', 'وظائف'],
        },
        {
            'title': 'مركز شباب وملعب خماسي في قنا',
            'details': (
                'شباب قرية قنا محتاجين مكان يلعبوا فيه بدل الشارع. الحملة بتعمل ملعب نجيلة صناعي '
                'للخماسي مع إنارة وتبديل ملابس ومركز شبابي يضم أنشطة للناشئة.\n\n'
                'الملعب هيتبنى على أرض تابعة لمركز الشباب بموافقة رسمية، وإيراد تشغيل الملعب '
                'هيمول صيانته ومصاريف المركز.'
            ),
            'category': 'رياضة', 'target': 360000, 'pct': 49, 'start_offset': 14, 'end_offset': 70,
            'status': 'running', 'featured': False, 'tags': ['رياضة', 'شباب', 'تجمعات'],
        },
        {
            'title': 'حملة تنظيف نهر النيل في الأقصر',
            'details': (
                'متطوعين من الأقصر بيعملوا حملات تنظيف دورية بس، والقمامة بترجع تاني. المشروع بيدور '
                'على إنشاء نقطة جمع ثابتة مع حواجز عائمة بتتجمع عليها المخلفات قبل ما تدخل مجرى '
                'النهر.\n\n'
                'أي دعم بيساعد في تجهيز الحواجز وسلة الجمع، مع متابعة الانتظام مع جمعية أهلية محلية.'
            ),
            'category': 'بيئة', 'target': 220000, 'pct': 32, 'start_offset': 35, 'end_offset': 25,
            'status': 'running', 'featured': False, 'tags': ['نهر النيل', 'متطوعين', 'بيئة'],
        },
        {
            'title': 'بنية تحتية لمركز مجتمعي رقمي في أسيوط',
            'details': (
                'تحويل قاعة شعبية مهجورة في أسيوط لمركز مجتمعي رقمي: إنترنت مدعوم، 15 جهاز حاسوب، '
                'وقاعة ورش مجانية للطلاب والخريجين.\n\n'
                'المركز هيتشغل بالشراكة مع مبادرة محلية، والخدمات كلها مجانية أو مدعومة لسكان '
                'الحي.'
            ),
            'category': 'مجتمع', 'target': 280000, 'pct': 44, 'start_offset': 28, 'end_offset': 45,
            'status': 'running', 'featured': False, 'tags': ['رقمنة', 'مجتمع', 'حصص مجانية'],
        },
        {
            'title': 'فيلم وثائقي عن صنّاع الفن في القاهرة',
            'details': (
                'فيلم وثائقي حقيقي بيوثق رحلة صنّاع التراث (نحاس، زجاج، جلد) في شوارع القاهرة '
                'القديمة قبل ما المهن دي تندثر، بالتعاون مع صنّاع فعليين.\n\n'
                'التمويل يغطي التصوير، المونتاج، حفلات العرض، وحقوق التوزيع في المهرجانات.'
            ),
            'category': 'فنون', 'target': 310000, 'pct': 58, 'start_offset': 40, 'end_offset': 50,
            'status': 'running', 'featured': False, 'tags': ['سينما', 'وثائقي', 'تراث'],
        },
        {
            'title': 'مهرجان طعام الشارع في شرم الشيخ',
            'details': (
                'فكرة مهرجان موسمي بيجمع أكل الشارع المصري في شرم — فطير، فلافل، كشري، وكبابجي — '
                'هيوفر منصة لعشرات أصحاب العربيات من كل المحافظات.\n\n'
                'التنظيم واجه صعوبات في الترخيص خلال الشهور اللي فاتت، واتقرر تجميد الحملة لحد ما '
                'تتأكد التراخيص بشكل نهائي.'
            ),
            'category': 'مجتمع', 'target': 260000, 'pct': 5, 'start_offset': 12, 'end_offset': 33,
            'status': 'cancelled', 'featured': False, 'tags': ['طعام الشارع', 'سياحة', 'فعاليات'],
        },
    ]


COMMENT_TEXTS = [
    'فكرة ممتازة والمشروع واضح ومحدد، بالتوفيق إن شاء الله.',
    'ادعمت من أول يوم، والناس المحتاجة دي أولى بكل حاجة.',
    'أتمنى يكون فيه تقارير دورية واضحة — الشفافية بتخلي الثقة.',
    'شفت التوثيق والصور، والحسابات منطقية وسليمة.',
    'ربنا يبارك فيكم، ده النوع ده من المشاريع اللي محتاجينه فعلًا.',
    'ممكن توضحوا تفاصيل أكتر عن الجدول الزمني للمرحلة التانية؟',
    'المشروع استحوذ على اهتمام كبير في الدوائر اللي حولي.',
    'دايمًا معاكم، وأتمنى إعلان نهاية مرحلة التمويل بحفلة لتقدير الداعمين.',
]

REPLY_TEXTS = [
    'شكرًا جدًا على كلامك، الدعم ده بيسوى كتير.',
    'تمام، هننزل تقرير مفصل خلال أيام — التزمنا بالوضوح.',
    'ربنا يجزيكم خير، باب التطوع مفتوح دايمًا.',
    'سؤال ممتاز، الجدول الزمني المحدث موجود في آخر تحديث.',
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _egyptian_phone():
    prefix = random.choice(EGYPTIAN_PREFIXES)
    return prefix + ''.join(str(random.randint(0, 9)) for _ in range(8))


def _fetch_bytes(url):
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200 and resp.headers.get('content-type', '').startswith('image/'):
            return resp.content
    except requests.RequestException:
        pass
    return None


def _fallback_image(index, palette):
    """Self-contained gradient image so seeding never depends on the net."""
    top, bottom = palette
    width, height = 900, 600
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    for cx, cy, radius, color in [
        (200, 120, 200, (255, 255, 255)),
        (650, 420, 240, (0, 0, 0)),
        (760, 90, 150, (255, 255, 255)),
    ]:
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*color, 26))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    for i in range(index % 3 + 2):
        x = 60 + i * 120
        y = height - 110 + (i % 3) * 22
        draw.rounded_rectangle([x, y, x + 46, y + 24], radius=12, outline=(255, 255, 255), width=3)
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=82, optimize=True)
    return buffer.getvalue()


def _avatar_image(seed):
    """Small square gradient avatar, unique per user."""
    palettes = [
        ((11, 46, 44), (31, 122, 110)),
        ((22, 33, 62), (37, 99, 235)),
        ((90, 24, 62), (217, 70, 0)),
        ((24, 60, 34), (5, 150, 105)),
        ((58, 34, 12), (245, 158, 11)),
        ((26, 26, 74), (124, 58, 237)),
    ]
    top, bottom = palettes[seed % len(palettes)]
    size = 240
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    for cx, cy, radius, color in [
        (size * 0.28, size * 0.3, size * 0.22, (255, 255, 255)),
        (size * 0.72, size * 0.7, size * 0.35, (255, 255, 255)),
    ]:
        overlay = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*color, 40))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=80, optimize=True)
    return buffer.getvalue()


class Command(BaseCommand):
    help = 'Seed rich, realistic Arabic demo data (users, projects, donations, updates, rewards, comments).'

    def add_arguments(self, parser):
        parser.add_argument('--projects', type=int, default=16, help='Number of projects to create.')
        parser.add_argument('--backers-per-project', type=int, default=12, help='Max backers per project.')
        parser.add_argument('--no-downloads', action='store_true', help='Never hit the network (pure generated images).')

    def handle(self, *args, **options):
        random.seed(42)
        downloads = not options['no_downloads']

        self._create_categories()
        backers = self._create_users()
        created_projects = 0
        skipped_projects = 0

        for spec in _projects()[:options['projects']]:
            created, extra = self._create_project(spec, backers, downloads)
            if created:
                created_projects += 1
            else:
                skipped_projects += 1
            self.stdout.write(extra)

        self.stdout.write(self.style.SUCCESS('\nDone.'))
        self.stdout.write(f'  projects created: {created_projects}')
        self.stdout.write(f'  projects skipped: {skipped_projects}')
        self.stdout.write(
            self.style.WARNING(f'  demo account password for all seeded users: {DEMO_PASSWORD}')
        )

    def _create_categories(self):
        for name, slug in _categories():
            Category.objects.get_or_create(slug=slug, defaults={'name': name})
        self.stdout.write(self.style.SUCCESS(f'categories: {_categories().__len__()}'))

    def _create_users(self):
        specs = _projects()
        creators_count = min(len(specs), 14)
        backers_count = 24
        pool = []

        for i in range(creators_count):
            first = random.choice(FEMALE_FIRST_NAMES if i % 2 else MALE_FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f'{first}@{random.choice(["takaful", "example"])}.com'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'phone_number': _egyptian_phone(),
                    'bio': random.choice(BIO_TEMPLATES),
                    'is_active': True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                if not user.profile_picture:
                    self._set_avatar(user, i)
            pool.append(user)

        for i in range(backers_count):
            first = random.choice(FEMALE_FIRST_NAMES if i % 2 else MALE_FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f'backer{i}.{first}@{random.choice(["takaful", "example"])}.com'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'phone_number': _egyptian_phone(),
                    'bio': random.choice(BIO_TEMPLATES),
                    'is_active': True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                if not user.profile_picture:
                    self._set_avatar(user, i + 100)
            pool.append(user)

        self.stdout.write(self.style.SUCCESS(f'demo users: {len(pool)}'))
        return pool

    def _set_avatar(self, user, seed):
        data = _avatar_image(seed)
        user.profile_picture.save(f'avatar-{user.pk or seed}.jpg', ContentFile(data), save=True)

    def _create_project(self, spec, backers, downloads):
        if Project.objects.filter(title=spec['title']).exists():
            return False, self.style.WARNING(f"  skip (exists): {spec['title']}")

        category = Category.objects.get(slug=spec['category'])
        creator = random.choice([u for u in backers[:14]])
        today = timezone.localdate()
        start_date = today - timezone.timedelta(days=spec['start_offset'])
        end_date = today + timezone.timedelta(days=spec['end_offset'])
        if spec['status'] == 'ended':
            end_date = today - timezone.timedelta(days=spec['end_offset'])

        target = Decimal(str(spec['target']))

        project = Project.objects.create(
            title=spec['title'],
            details=spec['details'],
            category=category,
            creator=creator,
            total_target=target,
            start_date=start_date,
            end_date=end_date,
            status=spec['status'],
            is_featured=spec['featured'],
        )

        tag_map = {}
        for tag_name in spec['tags']:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            tag_map[tag_name] = tag
        project.tags.set(tag_map.values())

        if downloads:
            self._attach_images(project, spec)
        else:
            self._attach_generated_images(project)

        self._attach_rewards(project, target)
        self._attach_updates(project)
        self._attach_donations(project, spec, backers)
        self._attach_comments(project, backers)
        self._attach_ratings(project, backers)

        return True, self.style.SUCCESS(f"  created: {spec['title']}")

    def _attach_images(self, project, spec):
        seg = random.sample(PHOTO_POOL, 3)
        for i, photo_id in enumerate(seg):
            data = _fetch_bytes(f'https://images.unsplash.com/photo-{photo_id}?w=900&q=80&auto=format&fit=crop')
            if data is None:
                data = _fallback_image(i, [(11, 46, 44), (37, 99, 235)])
            slug = text_utils.slugify(project.title, allow_unicode=True)[:40] or 'project'
            img = ProjectImage(project=project)
            img.image.save(f'{slug}-{i + 1}.jpg', ContentFile(data), save=True)

    def _attach_generated_images(self, project):
        for i in range(3):
            data = _fallback_image(i, [(22, 33, 62), (37, 99, 235)] if i % 2 else [(11, 46, 44), (31, 122, 110)])
            slug = text_utils.slugify(project.title, allow_unicode=True)[:40] or 'project'
            img = ProjectImage(project=project)
            img.image.save(f'{slug}-{i + 1}.jpg', ContentFile(data), save=True)

    def _attach_rewards(self, project, target):
        fixed = [Decimal(str(v)) for v in (100, 250, 500, 1000, 2000, 5000) if Decimal(str(v)) < target]
        if not fixed:
            fixed = [Decimal('50'), Decimal('100')]
        tier_count = random.randint(2, min(4, len(fixed)))
        amounts = sorted(random.sample(fixed, tier_count))
        for j, amount in enumerate(amounts):
            template = REWARD_TEMPLATES[j % len(REWARD_TEMPLATES)]
            RewardTier.objects.create(
                project=project,
                title=f'المستوى {j + 1}: {template.split(":")[0]}',
                description=template,
                amount=amount,
                quantity=None if j % 3 else random.randint(20, 80),
                estimated_delivery=random.choice(['شهر من نهاية الحملة', 'شهرين', '3 أشهر', 'بنهاية الموسم']),
            )

    def _attach_updates(self, project):
        count = random.randint(1, 3)
        shuffled = UPDATE_TITLES[:]
        random.shuffle(shuffled)
        for j in range(count):
            ProjectUpdate.objects.create(
                project=project,
                title=shuffled[j % len(shuffled)],
                body=random.choice(UPDATE_BODIES),
            )

    def _attach_donations(self, project, spec, backers):
        target_piasters = int(Decimal(str(spec['target'])) * 100)
        ct = random.randint(5, 12)
        pool = [u for u in backers if u != project.creator][:ct]
        if not pool:
            return
        amounts = self._split_donations(target_piasters, spec['pct'], len(pool))
        for user, amount in zip(pool, amounts):
            if amount > 0:
                Donation.objects.create(
                    user=user, project=project, amount=amount,
                    status=Donation.STATUS_SUCCESSFUL,
                )
        if pool:
            project.sync_current_fund()

    def _split_donations(self, target_piasters, pct, count):
        wanted = int(target_piasters * pct // 100)
        if wanted <= 0:
            return [Decimal('0')] * count
        nice = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]
        amounts = [random.choice(nice) * 100 for _ in range(count)]
        scale = wanted / sum(amounts)
        if scale > 10:
            scale = 10
        amounts = [max(100, int(a * scale)) for a in amounts]
        amounts[-1] += wanted - sum(amounts)
        return [Decimal(a) / 100 for a in amounts]

    def _attach_comments(self, project, backers):
        count = random.randint(2, 4)
        chosen = random.sample([u for u in backers if u != project.creator], min(count, len(backers) - 1))
        for user in chosen:
            parent = Comment.objects.create(user=user, project=project, text=random.choice(COMMENT_TEXTS))
            if random.random() < 0.4:
                reply_user = random.choice(backers)
                Comment.objects.create(user=reply_user, project=project, parent=parent, text=random.choice(REPLY_TEXTS))

    def _attach_ratings(self, project, backers):
        count = random.randint(1, 5)
        chosen = random.sample([u for u in backers if u != project.creator], min(count, len(backers) - 1))
        for user in chosen:
            Rating.objects.get_or_create(
                user=user, project=project, defaults={'value': random.choice(RATINGS_POOL)}
            )