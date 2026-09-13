"""
seed_demo_data — populate the database with realistic Egyptian demo
crowdfunding projects so the site looks alive immediately after setup.

Safe to run repeatedly:

- Categories / tags / users are created with get_or_create.
- Projects are created one-time (matched by title). Re-running the command
  leaves existing projects untouched, so it never duplicates records.

Usage:

    python manage.py seed_demo_data

Demo accounts share the password: TakafulDemo@2026
"""

import io
import itertools
import random
from decimal import Decimal
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import text as text_utils
from django.utils import timezone

from PIL import Image, ImageDraw

from accounts.models import User
from core.models import Comment, Rating
from projects.models import Category, Donation, Project, ProjectImage, Tag

DEMO_PASSWORD = 'TakafulDemo@2026'

# ---------------------------------------------------------------------------
# Categories (name, slug) — Arabic to match the RTL frontend
# ---------------------------------------------------------------------------
CATEGORIES = [
    ('أجهزة ومعدات طبية', 'أجهزة-طبية'),
    ('التعليم', 'تعليم'),
    ('التقنية', 'تقنية'),
    ('البيئة', 'بيئة'),
    ('المشروعات الصغيرة', 'مشروعات-صغيرة'),
    ('المجتمع', 'مجتمع'),
    ('الفنون', 'فنون'),
    ('قضايا اجتماعية', 'قضايا-اجتماعية'),
]

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
CREATORS = [
    ('أحمد', 'الشناوي', 'ahmed.elshanawany@example.com', '01000000001'),
    ('منى', 'عبد العظيم', 'mona.abdelazim@example.com', '01000000002'),
    ('كريم', 'فؤاد', 'kareem.fouad@example.com', '01000000003'),
    ('سارة', 'إبراهيم', 'sara.ibrahim@example.com', '01000000004'),
    ('عمر', 'حسن', 'omar.hassan@example.com', '01000000005'),
    ('نورهان', 'مصطفى', 'nourhan.mostafa@example.com', '01000000006'),
    ('محمد', 'سامي', 'mohamed.samy@example.com', '01000000007'),
    ('هدى', 'محمود', 'hoda.mahmoud@example.com', '01000000008'),
    ('يوسف', 'عادل', 'youssef.adel@example.com', '01000000009'),
    ('رنا', 'الشريف', 'rana.elsherif@example.com', '01000000010'),
    ('مصطفى', 'جابر', 'mostafa.gaber@example.com', '01000000011'),
    ('أسماء', 'فتحي', 'asmaa.fathy@example.com', '01000000012'),
]

BACKERS = [
    ('خالد', 'عبد الله', 'khaled.abdallah@example.com', '01000000021'),
    ('دينا', 'سيد', 'dina.sayed@example.com', '01000000022'),
    ('تامر', 'منصور', 'tamer.mansour@example.com', '01000000023'),
    ('إيمان', 'رشدي', 'eman.roshedy@example.com', '01000000024'),
    ('حسام', 'عودة', 'hosam.awda@example.com', '01000000025'),
    ('ليلى', 'سمير', 'layla.samir@example.com', '01000000026'),
    ('محمود', 'عبد الرازق', 'mahmoud.abdelrazek@example.com', '01000000027'),
    ('شيماء', 'النجار', 'shaimaa.elnaggar@example.com', '01000000028'),
    ('باسل', 'عاطف', 'bassel.atef@example.com', '01000000029'),
    ('رضوى', 'حلمي', 'radwa.helmy@example.com', '01000000030'),
    ('إسلام', 'رجب', 'eslam.ragab@example.com', '01000000031'),
    ('فاطمة', 'عوض', 'fatma.awad@example.com', '01000000032'),
    ('هشام', 'طارق', 'hesham.tarek@example.com', '01000000033'),
    ('أمل', 'سعيد', 'amal.saeed@example.com', '01000000034'),
    ('زياد', 'نبيل', 'ziad.nabil@example.com', '01000000035'),
]

# ---------------------------------------------------------------------------
# Demo projects
# ---------------------------------------------------------------------------
# Each project dict:
#   title, details, category(slug), creator(index), target, pct (funded %),
#   days_left (end_date = today + days_left), start_offset (start_date =
#   today - days), status ('running' | 'ended' | 'cancelled'), featured,
#   tags, images (unsplash photo ids), ratings, comments
PROJECTS = [
    {
        'title': 'ألواح شمسية لمدرسة قروية في سوهاج',
        'details': (
            'مدرسة أبو تيج الابتدائية في سوهاج بتعتمد على الكهرباء الحكومية اللي بتتفصل كتير '
            'في الشتاء، وده بيوقف الدروس والمعامل. الحملة هدفها تركيب ألواح شمسية تولّد طاقة كافية '
            'لتشغيل الإضاءة والمراوح وأجهزة العرض طول اليوم الدراسي.\n\n'
            'التكلفة شاملة التركيب، الصيانة لسنتين، وتدريب مدرسين من علوم وبايدجوجيا على تشغيل النظام. '
            'أي تعليمة مش بتكفي هتتحول لتشغيل مشروع ميكروباص مدرسي للمواصلات.'
        ),
        'category': 'بيئة',
        'creator': 0,
        'target': 250000.00,
        'pct': 78,
        'start_offset': 38,
        'end_offset': 52,
        'status': 'running',
        'featured': True,
        'tags': ['طاقة شمسية', 'تعليم', 'الريف'],
        'images': ['1509391366360-2e959784a276', '1503676260728-1c00da094a0b', '1580582932707-520aed937b7b'],
        'ratings': [5, 5, 4, 5, 4],
    },
    {
        'title': 'جهاز أشعة إكس لمستشفى القرية في المنيا',
        'details': (
            'مركز رعاية القرية في ملوي بيخدم أكتر من 40 ألف مواطن من القرى المجاورة، وأقرب جهاز '
            'أشعة ليه على بعد 60 كيلو. المرضى بينضطروا يسافروا بدري جدًا ويدفعوا من جيوبهم.\n\n'
            'الهدف توفير جهاز أشعة رقمي حديث ومستلزمات التشغيل الأولية. المستشفى هتتكفل بالتشغيل '
            'والصيانة، وكل كتب القرى الحوالين هتستفيد بشكل مباشر.'
        ),
        'category': 'أجهزة-طبية',
        'creator': 1,
        'target': 500000.00,
        'pct': 63,
        'start_offset': 22,
        'end_offset': 68,
        'status': 'running',
        'featured': False,
        'tags': ['رعاية صحية', 'معدات طبية', 'صعيد مصر'],
        'images': ['1579684385127-1ef15d508118', '1584433144859-1fc3ab64a957', '1519494026892-80bbd2d6fd0d'],
        'ratings': [5, 5, 5, 4],
    },
    {
        'title': 'مخبز أسرة محمد في الفيوم — من فكرة لفرن حقيقي',
        'details': (
            'أسرة محمد، أم لخمسة عيال، بتخبز عيش بلدي وبتيعه جنب مدرسة عيالها. الحلم إن المخبز '
            'الصغير ده يبقى مشروع عيلة كامل بفرن حديث وشغل مرتب.\n\n'
            'التمويل هيغطي تجهيز الفرن، رخصة التشغيل، وتغليف المنتج. الأسرة هتستقدم بالمخبز وتوظَّف '
            'شاب من القرية معاهم. كل جنيه بيدخل هيقدّموا منه الأولاد للمدرسة.'
        ),
        'category': 'مشروعات-صغيرة',
        'creator': 2,
        'target': 90000.00,
        'pct': 41,
        'start_offset': 15,
        'end_offset': 45,
        'status': 'running',
        'featured': False,
        'tags': ['مخبز', 'تمكين المرأة', 'صناعة أسرية'],
        'images': ['1509440159596-0249088772ff', '1555507036-ab1f4038808a', '1599058917212-d750089bc07e'],
        'ratings': [4, 4, 5, 4],
    },
    {
        'title': 'مياه نظيفة لكل بيت في الدقهلية',
        'details': (
            'ست قرى في مركز السنبلاوين بتحصل على مياه بيها ملوثات عالية، وبيتغذا منها '
            'خصوصًا أطفال المدارس. الحملة بتشتغل مع الوحدة المحلية على تركيب محطة معالجة صغيرة '
            'وشبكة توزيع بطاقة سعة تكفي القرى كلها.\n\n'
            'بعد التشغيل هتنضاف محطات قياس جودة شهرية بيقوم بيها مهندسين متطوعين من الجامعة، '
            'والنتايج هتتنشر علنًا.'
        ),
        'category': 'بيئة',
        'creator': 3,
        'target': 180000.00,
        'pct': 91,
        'start_offset': 55,
        'end_offset': 18,
        'status': 'running',
        'featured': True,
        'tags': ['مياه', 'قرى', 'صحة عامة'],
        'images': ['1548839140-29a749e1cf4d', '1501785888041-af3ef285b470', '1470252649378-9c29740c9fa8'],
        'ratings': [5, 5, 4, 5, 5],
    },
    {
        'title': 'أكاديمية برمجة لجيل مصري فاهم التكنولوجيا',
        'details': (
            'مبادرة بتدرب 200 شاب وشابة من محافظات الصعيد على أساسيات البرمجة وتطوير الويب '
            'عن بُعد، مع سكن ووجبات للي محتاج في معسكرات نهاية الأسبوع.\n\n'
            'الميزانية بتغطي مدربين متخصصين، أجهزة لاب توب للملتحقين الغير قادرين، وشهادات معتمدة. '
            'الخريجين هيتوظفوا مع شركات تقنية شريكة أو يشتغلوا فريلانس.'
        ),
        'category': 'تعليم',
        'creator': 4,
        'target': 400000.00,
        'pct': 24,
        'start_offset': 12,
        'end_offset': 75,
        'status': 'running',
        'featured': False,
        'tags': ['برمجة', 'تدريب', 'شباب'],
        'images': ['1522202176988-66273c2fd55f', '1517180102446-f3ece451e9d8', '1498050108023-c5249f4df085'],
        'ratings': [4, 3, 5, 4],
    },
    {
        'title': 'حلي وإكسسوارات بإيدين بنات أسوان',
        'details': (
            'فريق من 12 بنت من أسوان بيعمل حلي وإكسسوارات من خامات محلية (خرز، جلد، وتقبلة ) '
            'وبيبعوها على المواسم السياحية. المشروع ده بيديهن دخل ثابت بدل الشغل الموسمي.\n\n'
            'تمويل الحملة هيشتري خامات بكميات كبيرة (توفير 30% من التكلفة)، ماكينة درزة، '
            'وحسابات تسويق على السوشيال ميديا. البنات بيشتغلوا من بيتهم بأجير عادل.'
        ),
        'category': 'مشروعات-صغيرة',
        'creator': 5,
        'target': 120000.00,
        'pct': 35,
        'start_offset': 20,
        'end_offset': 40,
        'status': 'running',
        'featured': False,
        'tags': ['حرف يدوية', 'تمكين المرأة', 'صناعة محلية'],
        'images': ['1608042314453-ae338d80c427', '1512436991641-6745cdb1723f', '1543825619-7d5a7cf51a4d'],
        'ratings': [4, 5, 4, 4],
    },
    {
        'title': 'مزرعة عضوية صديقة للبيئة في البحيرة',
        'details': (
            'مزرعة عيلة أبو العز في إدكو هتتحول لزراعة عضوية بالكامل: بيدر سماد، اقتصاد في استخدام '
            'المياه، وترشيد الأسمدة. التجربة هتتوتق وتتشارك مع 50 مزارع في المنطقة عشان يطبقوها.\n\n'
            'الهدف شراء تقاوي عضوية، شبكة ري بالتنقيط، وشهادة تصديق للمنتج العضوي عشان المنتج '
            'يتباع بسعر عادل في الأسواق.'
        ),
        'category': 'بيئة',
        'creator': 6,
        'target': 300000.00,
        'pct': 52,
        'start_offset': 30,
        'end_offset': 60,
        'status': 'running',
        'featured': False,
        'tags': ['زراعة عضوية', 'أمن غذائي', 'ري'],
        'images': ['1625246333195-78d9c38ad449', '1464226184884-fa280b87c399', '1434682881908-b43d0467b798'],
        'ratings': [5, 4, 4, 5, 4],
    },
    {
        'title': 'مهرجان جداريات: دعم فنانين الشارع في القاهرة',
        'details': (
            'مبادرة فنية بتحول واجهات عمارات المناطق الشعبية لجداريات ملونة، وبتوفر مصدر دخل '
            'مؤقت لعدد من فنانين الجرافيتي وفنون الشارع في مصر.\n\n'
            'الميزانية بتغطي خامات الطلاء، تصاريح المحافظة، وبدل الأجير للفنانين المشاركين — '
            'ومع نهاية المهرجان هيتوثق كل الجداريات في ألبوم رقمي.'

        ),
        'category': 'فنون',
        'creator': 7,
        'target': 150000.00,
        'pct': 18,
        'start_offset': 8,
        'end_offset': 35,
        'status': 'running',
        'featured': True,
        'tags': ['فن', 'جداريات', 'ثقافة'],
        'images': ['1516979187457-637abb4f9353', '1517824806704-9040b037703b', '1517048676732-d65bc937f952'],
        'ratings': [3, 4, 4],
    },
    {
        'title': 'شنط مدرسية وكتب لكل طالب في أسوان',
        'details': (
            'مع بداية السنة الدراسية، كتير من أولاد أسوان بيحضروا المدرسة من غير شنطة ولا أدوات '
            'كتابة. الحملة بتجمع شنط مدرسية متكاملة (شفشق، دفاتر، أقلام) وتوزعها على طلاب '
            'المدارس الحكومية الأكثر احتياجًا.\n\n'
            'كل جنيه هيتحول لشنطة حقيقية بتوصلك بالنيابة عنك لأولاد العيلة. اللجنة المحلية '
            'بتساعدنا في تحديد المستفيدين بشفافية تامة.'
        ),
        'category': 'قضايا-اجتماعية',
        'creator': 8,
        'target': 80000.00,
        'pct': 100,
        'start_offset': 90,
        'end_offset': 10,
        'status': 'ended',
        'featured': False,
        'tags': ['تعليم', 'أطفال', 'تساوي فرص'],
        'images': ['1472162072942-cd5147eb3902', '1523240795612-9a054b0db644', '1531482615713-2afd69097998'],
        'ratings': [5, 5, 5, 5, 5],
    },
    {
        'title': 'سلسلة ساندويتشات صحية من جامعة المنصورة',
        'details': (
            'أربع خريجات تجارة بينظموا مطعم صغير متنقل قدام كلية الهندسة ببيع ساندويتشات فاهيتا '
            'وصحية بأسعار الطلبة. المشروع نجح في الموقع التجريبي وبيحتاج رسملة عشان يبقى '
            'فرع ثاني وتشغيل عربتين.\n\n'
            'التمويل يغطي معدات المطبخ، سيارة مجهزة، ورأس مال خامات أول شهر. خطة التشغيل '
            'اتعملت مع محاسب مستقل والنموذج سليم.'
        ),
        'category': 'مشروعات-صغيرة',
        'creator': 9,
        'target': 200000.00,
        'pct': 8,
        'start_offset': 10,
        'end_offset': 55,
        'status': 'running',
        'featured': False,
        'tags': ['مشروع صغير', 'وجبات', 'شباب'],
        'images': ['1504674900247-0877df9cc836', '1555400038-63f5ba517a47', '1512058564366-18510be2db19'],
        'ratings': [],
    },
    {
        'title': 'إعادة تدوير البلاستيك في الإسكندرية',
        'details': (
            'المبادرة بتجمع زجاجات البلاستيك من مطاعم وشواطئ الإسكندرية، وبتشغلها لرقائق معاد '
            'تدويرها عبر وحدة فرز وتكسير صغيرة. الوحدة هتشتغل بيها 8 عمال من المنطقة.\n\n'
            'الإيراد من بيع الرقائق للشركات هيمول تشغيل الوحدة، والعائد بيستثمر في توسعة '
            'شبكة الجمع في حي كامل.'
        ),
        'category': 'بيئة',
        'creator': 10,
        'target': 600000.00,
        'pct': 12,
        'start_offset': 18,
        'end_offset': 80,
        'status': 'running',
        'featured': False,
        'tags': ['إعادة تدوير', 'بلاستيك', 'وظائف'],
        'images': ['1532996122724-e3c354a0b15b', '1558618720-8bd7b7a6634b', '1504307661254-35680f356dfd'],
        'ratings': [4, 3],
    },
    {
        'title': 'مركز شباب وملعب خماسي في قنا',
        'details': (
            'شباب قرية قنا محتاجين مكان يلعبوا فيه بدل الشارع. الحملة بتعمل ملعب نجيلة صناعي '
            'للخماسي مع إنارة وتبديل ملابس ومركز شبابي يضم انشطة للناشئة.\n\n'
            'الملعب هيتبنى على أرض تابعة لمركز الشباب بموافقة رسمية، وإيراد تشغيل الملعب '
            'هيمول صيانته ومصاريف المركز.'
        ),
        'category': 'مجتمع',
        'creator': 11,
        'target': 350000.00,
        'pct': 47,
        'start_offset': 14,
        'end_offset': 70,
        'status': 'running',
        'featured': True,
        'tags': ['رياضة', 'شباب', 'تجمعات'],
        'images': ['1461896836934-ffe607ba8211', '1579952363873-27f3bade9f55', '1571019613454-1cb2f99b2d8b'],
        'ratings': [4, 5, 4, 4, 5],
    },
    {
        'title': 'منصة تعليمية بالمحمول لطلاب الثانوية في مصر',
        'details': (
            'تطبيق بيشرح المنهج المصري بالفيديو والاختبارات التفاعلية، ومصمم يشتغل على أضعف '
            'الأجهزة وأبطأ النت — عشان يوصل لكل طالب في كل محافظة.\n\n'
            'التمويل هيغطي تسجيل أول 3 سنين من المحتوى، استضافة سحابية، وفريق مراجعة تربوية. '
            'الاشتراك هيبقى مجاني للطلاب الغير قادرين.'
        ),
        'category': 'تقنية',
        'creator': 4,
        'target': 450000.00,
        'pct': 64,
        'start_offset': 25,
        'end_offset': 65,
        'status': 'running',
        'featured': True,
        'tags': ['تعليم', 'تطبيقات موبايل', 'منهج مصري'],
        'images': ['1511707171634-5f897ff02aa9', '1519389950473-47ba0277781c', '1488190211105-8b0e65b80b4e'],
        'ratings': [5, 4, 5, 5, 4],
    },
    {
        'title': 'حملة تنظيف نهر النيل في الأقصر',
        'details': (
            'متطوعين من الأقصر بيعملو حملات تنظيف دورية بس، والقمامة بترجع تاني. المشروع بيدور '
            'على إنشاء نقطة جمع ثابتة مع حواجز عائمة بتتجمع عليها المخلفات قبل ما تدخل مجرى النهر.\n\n'
            'أي دعم بيساعد في تجهيز الحواجز وسلة الجمع، ومتابعة الانتظام مع جمعية أهلية محلية.'
        ),
        'category': 'بيئة',
        'creator': 3,
        'target': 220000.00,
        'pct': 30,
        'start_offset': 35,
        'end_offset': 25,
        'status': 'running',
        'featured': False,
        'tags': ['نهر النيل', 'متطوعين', 'بيئة'],
        'images': ['1536265309753-0da95d80d2f4', '1500530855697-b586d89ba3ee', '1506967439472-bc5dfa4f1e63'],
        'ratings': [4, 4, 3],
    },
    {
        'title': 'فيلم وثائقي عن صنّاع الفن في القاهرة',
        'details': (
            'فيلم وثائقي حقيقي بيوّثق رحلة صنّاع التراث (نحاس، زجاج، جلد) في شوارع القاهرة '
            'القديمة قبل ما المهن دي تندثر. الوثائقي هيتعمل بالتعاون مع صناع فعليين.'
        ),
        'category': 'فنون',
        'creator': 7,
        'target': 300000.00,
        'pct': 55,
        'start_offset': 40,
        'end_offset': 50,
        'status': 'running',
        'featured': False,
        'tags': ['سينما', 'وثائقي', 'تراث'],
        'images': ['1478720568477-152d9b164e26', '1485846234645-a62644f84728', '1516035069371-29a1b244cc32'],
        'ratings': [5, 4, 5],
    },
    {
        'title': 'مهرجان طعام الشارع في شرم الشيخ',
        'details': (
            'فكرة مهرجان موسمي بيجمع أكل الشارع المصري في شرم — فطير، فلافل، كشري، وكبابجي. '
            'المهرجان كان هيوفر منصة لعشرات أصحاب العربيات من كل المحافظات.\n\n'
            'التنظيم واجه صعوبات في الترخيص خلال الشهور اللي فاتت، واتقرر تجميد الحملة لحد ما '
            'تتأكد التراخيص بشكل نهائي.'
        ),
        'category': 'مجتمع',
        'creator': 9,
        'target': 260000.00,
        'pct': 5,
        'start_offset': 12,
        'end_offset': 33,
        'status': 'cancelled',
        'featured': False,
        'tags': ['طعام الشارع', 'سياحة', 'فعاليات'],
        'images': ['1517248135467-4c7edcad34c4', '1504674900247-0877df9cc836', '1556910103-1c02745aae4d'],
        'ratings': [],
    },
]

# ---------------------------------------------------------------------------
# Comments (project index -> list of [author index, text, [replies]])
# Reply: [author index, text]
# ---------------------------------------------------------------------------
COMMENTS = {
    0: [
        ['باسل', 'فكرة حلوة جدًا، المدرسة دي كانت محتاجة الكهرباء من سنين. ربنا يبارك فيكم.'],
        ['شيماء', 'ابني في المدرسة دي، كل يوم بيحكي عن قطع الكهرباء. ادعمت ومستنية النتيجة.', [
            ['أحمد', 'شكرًا شيماء، كل جنيه وصل فعلًا بيشارك فيه. هنعلن عن التركيب أول ما يكتمل التمويل.'],
        ]],
        ['إسلام', 'قريت إن تركيبات ألواح أكبر بتكلف أكتر، الفريق حاسب على المتابعة؟'],
    ],
    3: [
        ['أمل', 'من أحسن المشاريع اللي شفتها على المنصة. المياه دي حياتنا كلها.'],
        ['هشام', 'اتبرعت إمبارح وحاسس بالفرق الحقيقي. كملوا.', [
            ['سارة', 'شكرًا هشام. التقرير الدوري بالقياسات هيبدأ ينزل الشهر الجاي.'],
        ]],
    ],
    12: [
        ['ليلى', 'كنت بدور على حاجة زي كده من زمان لمراتي في ثانوية عامة. بالتوفيق.'],
        ['تامر', 'التطبيق اشتغل معايا على موبايل قديم جدًا في التجرية! الإنجاز دا يستاهل الدعم.', [
            ['عمر', 'ده أهم تعليق لينا والله. دي كانت الأولوية رقم واحد.'],
        ]],
    ],
    1: [
        ['رضوى', 'عشنا المأساة دي بنفسنا مع ماما. جهاز الأشعة هيفرق مع الستات اللي زيها.'],
        ['زياد', 'الحملة محتاجة توثيق أكتر للاحتياج، بس الفكرة جدية.', [
            ['منى', 'هنا توثيق الفحص المعملي والاحتياج، ودي صور من أرشيف المستشفى: https://example.com'],
        ]],
    ],
    6: [
        ['فاطمة', 'ربنا يبارك — الزراعة العضوية دي مستقبل مصر.'],
        ['محمود', 'ليه مفيش تعاون مع وزارة الزراعة؟ برضه فكرة تستاهل، ادعمت.'],
    ],
    2: [
        ['دينا', 'أخلاق أهل الفيوم محترمة، نفسي يكون المخبز ده نجاح كبير.'],
    ],
    8: [
        ['خالد', 'مبروك على تكملة الهدف! شنطة لكل طالب دي حاجة فعيلة.'],
        ['إيمان', 'الأطفال دول مستقبلنا. مبروك.', [
            ['يوسف', 'شكرًا جدًا. التوزيع بدأ فعلاً بالأسبقية للأسر الكبرى.'],
        ]],
    ],
    11: [
        ['أمل', 'ملعب في القرية دي كان طلب كبير من الأهالي. بالتوفيق.'],
        ['حسام', 'الإيراد من تأجير الملعب فكرة عملية جدًا هتضمن استمراريته.'],
    ],
    7: [
        ['زياد', 'جداريات بتغير نفسية الحي كله. استمروا.'],
    ],
    13: [
        ['شيماء', 'ناس تانية بتجيب فلوس في نضارة الإسكندرية، وإحنا بنضف نهرنا. بالتوفيق.'],
    ],
}

# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
FALLBACK_GRADIENTS = [
    ((11, 46, 44), (31, 122, 110)),
    ((22, 33, 62), (37, 99, 235)),
    ((162, 78, 38), (217, 119, 6)),
    ((134, 0, 53), (217, 70, 0)),
]

image_counter = itertools.count()


def _fallback_image(index):
    """Generate an attractive abstract gradient when a photo can't be
    downloaded (offline / dead URL) — keeps the demo self-contained."""
    top, bottom = FALLBACK_GRADIENTS[index % len(FALLBACK_GRADIENTS)]
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
        (200, 120, 180, (255, 255, 255)),
        (650, 420, 220, (0, 0, 0)),
        (760, 90, 130, (255, 255, 255)),
    ]:
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(*color, 28))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)
    for i in range(8):
        x = 60 + i * 110
        y = height - 110 + (i % 3) * 22
        draw.rounded_rectangle([x, y, x + 46, y + 24], radius=12, outline=(255, 255, 255), width=3)
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=82, optimize=True)
    return buffer.getvalue()


def _fetch_image(photo_id):
    url = f'https://images.unsplash.com/photo-{photo_id}?w=900&q=80&auto=format&fit=crop'
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200 and resp.headers.get('content-type', '').startswith('image/'):
            return resp.content
    except requests.RequestException:
        pass
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_or_create_user(first_name, last_name, email, phone):
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone,
            'is_active': True,
        },
    )
    if created:
        user.set_password(DEMO_PASSWORD)
        user.save()
    return user, created


def _split_donations(target_piasters, pct, count):
    """Split a funding amount into `count` nice-looking donations in
    piasters, summing exactly to target_piasters * pct / 100."""
    wanted = int(target_piasters * pct // 100)
    if wanted <= 0:
        return []
    nice = [50, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000, 3000]
    amounts = [random.choice(nice) * 100 for _ in range(count)]
    scale = wanted / sum(amounts)
    if scale > 10:
        scale = 10
    amounts = [max(100, int(a * scale)) for a in amounts]
    amounts[-1] += wanted - sum(amounts)
    return [Decimal(a) / 100 for a in amounts]


class Command(BaseCommand):
    help = 'Seed realistic Egyptian demo projects, users, donations, comments and ratings.'

    def handle(self, *args, **options):
        random.seed(42)  # deterministic demo data across runs
        today = timezone.localdate()

        # --- categories ----------------------------------------------------
        cat_map = {}
        for name, slug in CATEGORIES:
            cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            cat_map[slug] = cat
        self.stdout.write(self.style.SUCCESS(f'categories: {len(cat_map)}'))
        self.stdout.write('  ' + ', '.join(str(c) for c in cat_map.values()))

        # --- users ---------------------------------------------------------
        creators = {}
        for fname, lname, email, phone in CREATORS:
            user, _ = _get_or_create_user(fname, lname, email, phone)
            creators[fname] = user

        backers = []
        for fname, lname, email, phone in BACKERS:
            user, _ = _get_or_create_user(fname, lname, email, phone)
            backers.append(user)
        self.stdout.write(self.style.SUCCESS(f'demo users: {len(creators) + len(backers)}'))

        # --- tags ----------------------------------------------------------
        tag_map = {}
        for spec in PROJECTS:
            for tag_name in spec['tags']:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                tag_map[tag_name] = tag

        created_projects = 0
        skipped_projects = 0
        for spec in PROJECTS:
            if Project.objects.filter(title=spec['title']).exists():
                skipped_projects += 1
                self.stdout.write(self.style.WARNING(f"  skip (exists): {spec['title']}"))
                continue

            creator = creators[CREATORS[spec['creator']][0]]
            category = cat_map[spec['category']]

            start_date = today - timezone.timedelta(days=spec['start_offset'])
            end_date = today + timezone.timedelta(days=spec['end_offset'])
            if spec['status'] == 'ended':
                end_date = today - timezone.timedelta(days=spec['end_offset'])

            project = Project.objects.create(
                title=spec['title'],
                details=spec['details'],
                category=category,
                creator=creator,
                total_target=Decimal(str(spec['target'])),
                start_date=start_date,
                end_date=end_date,
                status=spec['status'],
                is_featured=spec['featured'],
            )
            project.tags.set(tag_map[t] for t in spec['tags'])
            self._attach_images(project, spec)
            self._attach_donations(project, spec, backers)
            self._attach_ratings(project, spec, backers)
            created_projects += 1
            self.stdout.write(self.style.SUCCESS(f"  created: {spec['title']}"))

        # --- comments & replies -------------------------------------------
        for idx, items in COMMENTS.items():
            spec = PROJECTS[idx]
            project = Project.objects.filter(title=spec['title']).first()
            if project is None or project.comments.exists():
                continue
            for item in items:
                if len(item) == 3:
                    author_key, text, replies = item
                else:
                    author_key, text = item
                    replies = None
                author = creators.get(author_key) or next(b for b in backers if b.first_name == author_key)
                comment = Comment.objects.create(user=author, project=project, text=text)
                for reply_key, reply_text in replies or []:
                    replier = creators.get(reply_key) or next(b for b in backers if b.first_name == reply_key)
                    Comment.objects.create(user=replier, project=project, parent=comment, text=reply_text)

        self.stdout.write(self.style.SUCCESS('\nDone.'))
        self.stdout.write(f'  projects created : {created_projects}')
        self.stdout.write(f'  projects skipped : {skipped_projects}')
        self.stdout.write(
            self.style.WARNING(f'  demo account password for all seeded users: {DEMO_PASSWORD}')
        )

    def _attach_images(self, project, spec):
        for i, photo_id in enumerate(spec['images']):
            data = _fetch_image(photo_id)
            if data is None:
                self.stdout.write(self.style.WARNING(f"    image fallback: {photo_id}"))
                data = _fallback_image(next(image_counter))
            slug = text_utils.slugify(project.title, allow_unicode=True)[:40] or 'project'
            name = f'{slug}-{i + 1}.jpg'
            image = ProjectImage(project=project)
            image.image.save(name, ContentFile(data), save=True)

    def _attach_donations(self, project, spec, backers):
        target_piasters = int(Decimal(str(spec['target'])) * 100)
        count = min(len(backers) - 1, max(5, int(spec['pct'] * 0.25)))
        pool = [b for b in backers if b != project.creator]
        random.shuffle(pool)
        chosen = pool[:count]
        amounts = _split_donations(target_piasters, spec['pct'], len(chosen))
        for user, amount in zip(chosen, amounts):
            if amount > 0:
                Donation.objects.create(
                    user=user, project=project, amount=amount,
                    status=Donation.STATUS_SUCCESSFUL,
                )
        if chosen:
            project.sync_current_fund()

    def _attach_ratings(self, project, spec, backers):
        values = spec['ratings']
        if not values:
            return
        pool = [b for b in backers if b != project.creator]
        random.shuffle(pool)
        for user, value in zip(pool, values):
            Rating.objects.update_or_create(
                user=user, project=project, defaults={'value': value}
            )