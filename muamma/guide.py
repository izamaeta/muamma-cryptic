"""Guide and glossary content, from docs/guide-content.md.

One source for both the guide page and the indicator glossary. A clue is a
list of runs so every part can carry its own colour and label; runs without
a role are plain text.
"""

TANIM = "tanım"
GOSTERGE = "gösterge"
MALZEME = "malzeme"

INTRO = {
    "title": "Muamma nasıl çözülür?",
    "subtitle": "Muamma bir bilgi yarışması değil; kelimelerle kurulmuş küçük bir şifre.",
    "golden_rule": [
        (
            "Tanım",
            "Cevabın düz anlamı. Neredeyse her zaman ipucunun başında ya da sonundadır.",
        ),
        ("Kelime oyunu", "Harflerle oynayarak cevabı kurduğun şifre."),
    ],
    "enumeration": (
        "Parantezdeki sayı cevabın harf sayısıdır. İki kelimeli cevaplarda, (4,3) "
        "gibi, her kelimenin harf sayısı ayrı yazılır."
    ),
    "surface": (
        "Bir ipucunu iki kez oku. İlk okuyuşta (yüzey) sıradan, hatta biraz tuhaf "
        "bir cümle görürsün. İkinci okuyuşta (formül) her kelimenin bir görevi "
        "vardır: biri tanımdır, biri talimat verir, biri malzemedir. İşin sırrı, "
        "cümlenin sana anlattığı hikâyeye kanmamak."
    ),
}

ANATOMY = {
    "clue": [
        {"key": "gosterge", "role": GOSTERGE, "text": "Bozuk"},
        {"text": " "},
        {"key": "malzeme", "role": MALZEME, "text": "kalem"},
        {"text": ", "},
        {"key": "tanim", "role": TANIM, "text": "söz"},
        {"text": " demek"},
    ],
    "enumeration": "5",
    "rows": [
        {
            "key": "gosterge",
            "part": "Bozuk",
            "role": GOSTERGE,
            "note": "“Harfleri karıştır” talimatı",
        },
        {
            "key": "malzeme",
            "part": "kalem",
            "role": MALZEME,
            "note": "Karıştırılacak harfler",
        },
        {"key": "tanim", "part": "söz", "role": TANIM, "note": "Cevabın düz anlamı"},
    ],
    "formula": "gösterge + malzeme → K-A-L-E-M karışır → KELAM = söz",
    "surface": "Bozulmuş bir kalemden söz ediyor gibi.",
    "reading": "KALEM'in harfleri karışınca, “söz” anlamına gelen KELAM çıkar.",
}


def _run(text, role=None):
    return {"text": text, "role": role} if role else {"text": text}


GROUPS = [
    {
        "key": "harf",
        "label": "Harfle oynayanlar",
        "intro": "Harflerin sırasıyla, yeriyle ya da seçimiyle oynanan temel türler.",
        "types": [
            {
                "key": "anagram",
                "name": "Anagram",
                "summary": "Malzemenin harfleri karıştırılarak cevap kurulur.",
                "indicators": [
                    "karışık",
                    "bozuk",
                    "serseri",
                    "sarhoş",
                    "dağınık",
                    "deli",
                    "yeniden",
                    "garip",
                    "çalkalanmış",
                ],
                "example": {
                    "clue": [
                        _run("Serseri", GOSTERGE),
                        _run(" "),
                        _run("alim", MALZEME),
                        _run(" "),
                        _run("bir mahkeme kararı", TANIM),
                        _run(" getirdi"),
                    ],
                    "enumeration": "4",
                    "parts": [
                        (GOSTERGE, GOSTERGE, "Serseri"),
                        (MALZEME, MALZEME, "alim"),
                        (TANIM, TANIM, "bir mahkeme kararı"),
                    ],
                    "solution": "ALİM'in harfleri karışır",
                    "answer": "İLAM",
                },
            },
            {
                "key": "gizli",
                "name": "Gizli kelime",
                "summary": (
                    "Cevap, ipucundaki bir ya da birkaç kelimenin içinde harfi "
                    "harfine saklıdır."
                ),
                "indicators": [
                    "içinde",
                    "saklı",
                    "gizli",
                    "barındıran",
                    "saklanan",
                    "kısmen",
                ],
                "example": {
                    "clue": [
                        _run("Karıncanın", MALZEME),
                        _run(" "),
                        _run("içinde saklanan", GOSTERGE),
                        _run(" "),
                        _run("bal yapıcı", TANIM),
                    ],
                    "enumeration": "3",
                    "parts": [
                        (GOSTERGE, GOSTERGE, "içinde saklanan"),
                        (MALZEME, MALZEME, "Karıncanın"),
                        (TANIM, TANIM, "bal yapıcı"),
                    ],
                    "solution": "kARInca",
                    "answer": "ARI",
                },
            },
            {
                "key": "harfler",
                "name": "Baş, son ve orta harfler",
                "summary": (
                    "Kelimelerin tamamı değil, sadece ilk harfleri, son harfleri ya "
                    "da ortası alınır."
                ),
                "indicators": [
                    "başları",
                    "ilk harfleri",
                    "sonları",
                    "kuyrukları",
                    "kalbi",
                    "ortası",
                ],
                "example": {
                    "clue": [
                        _run("Erik, limon, muz ve armudun", MALZEME),
                        _run(" "),
                        _run("başları", GOSTERGE),
                        _run(" "),
                        _run("bir meyve", TANIM),
                    ],
                    "enumeration": "4",
                    "parts": [
                        (GOSTERGE, GOSTERGE, "başları"),
                        (MALZEME, MALZEME, "Erik, limon, muz ve armudun"),
                        (TANIM, TANIM, "bir meyve"),
                    ],
                    "solution": "Erik + Limon + Muz + Armut",
                    "answer": "ELMA",
                },
            },
            {
                "key": "ters",
                "name": "Ters çevirme",
                "summary": "Malzeme tersten okunur.",
                "indicators": ["geri dönünce", "tersten", "dönen", "aynada", "geriye"],
                "example": {
                    "clue": [
                        _run("Ayak", MALZEME),
                        _run(" "),
                        _run("geri dönünce", GOSTERGE),
                        _run(" "),
                        _run("taş", TANIM),
                        _run(" olur"),
                    ],
                    "enumeration": "4",
                    "parts": [
                        (GOSTERGE, GOSTERGE, "geri dönünce"),
                        (MALZEME, MALZEME, "Ayak"),
                        (TANIM, TANIM, "taş"),
                    ],
                    "solution": "AYAK tersten",
                    "answer": "KAYA",
                },
            },
        ],
    },
    {
        "key": "parca",
        "label": "Parçalarla kuranlar",
        "intro": (
            "Küçük parçaların eklenmesi, iç içe geçmesi ya da kırpılmasıyla kurulan "
            "türler. Parçalar çoğu zaman kendileri de birer küçük tanımdır."
        ),
        "types": [
            {
                "key": "birlestirme",
                "name": "Birleştirme",
                "summary": "Küçük parçalar yan yana gelerek cevabı oluşturur.",
                "indicators": ["ile", "yan yana", "ardından", "peşinden", "eklenince"],
                "example": {
                    "clue": [
                        _run("Uydu", MALZEME),
                        _run(" ile "),
                        _run("beyaz", MALZEME),
                        _run(" "),
                        _run("yan yana", GOSTERGE),
                        _run(", "),
                        _run("yürümeye yarar", TANIM),
                    ],
                    "enumeration": "4",
                    "parts": [
                        ("parça 1", MALZEME, "Uydu → AY"),
                        ("parça 2", MALZEME, "beyaz → AK"),
                        (GOSTERGE, GOSTERGE, "yan yana"),
                        (TANIM, TANIM, "yürümeye yarar"),
                    ],
                    "solution": "AY + AK",
                    "answer": "AYAK",
                },
            },
            {
                "key": "icice",
                "name": "İç içe",
                "summary": "Bir parça diğerinin içine girer.",
                "indicators": [
                    "içine koy",
                    "saran",
                    "kucaklayan",
                    "yutan",
                    "arasına giren",
                ],
                "example": {
                    "clue": [
                        _run("Beyazı", MALZEME),
                        _run(" "),
                        _run("salın", MALZEME),
                        _run(" "),
                        _run("içine koy", GOSTERGE),
                        _run(", "),
                        _run("yüzde uzar", TANIM),
                    ],
                    "enumeration": "5",
                    "parts": [
                        ("parça 1", MALZEME, "Beyaz → AK"),
                        ("parça 2", MALZEME, "sal → SAL"),
                        (GOSTERGE, GOSTERGE, "içine koy"),
                        (TANIM, TANIM, "yüzde uzar"),
                    ],
                    "solution": "S(AK)AL",
                    "answer": "SAKAL",
                },
            },
            {
                "key": "harfatma",
                "name": "Harf atma",
                "summary": "Bir kelimeden harf düşer.",
                "indicators": [
                    "başsız",
                    "başını kaybeden",
                    "sonsuz",
                    "kuyruksuz",
                    "eksik",
                    "kalpsiz",
                ],
                "example": {
                    "clue": [
                        _run("Başını kaybeden", GOSTERGE),
                        _run(" "),
                        _run("kalem", MALZEME),
                        _run(" "),
                        _run("dünya", TANIM),
                        _run(" olur"),
                    ],
                    "enumeration": "4",
                    "parts": [
                        (GOSTERGE, GOSTERGE, "Başını kaybeden"),
                        (MALZEME, MALZEME, "kalem"),
                        (TANIM, TANIM, "dünya"),
                    ],
                    "solution": "KALEM − K",
                    "answer": "ALEM",
                },
            },
            {
                "key": "kisaltma",
                "name": "Kısaltmalar",
                "summary": (
                    "Bazı kelimeler ipucunda tek bir harfin yerine geçer. Muamma'da "
                    "şimdilik yalnızca şunları kullanıyoruz:"
                ),
                "indicators": [],
                "example": None,
                "table": [
                    ("kuzey, güney, doğu, batı", "K, G, D, B"),
                    ("sıfır, halka, yüzük", "O"),
                ],
                "note": "Yeni bir kısaltma kullanmaya başladığımızda bu listeye ekleyeceğiz.",
            },
        ],
    },
    {
        "key": "siradisi",
        "label": "Sıra dışı olanlar",
        "intro": "Kuralları esneten, nadir ama en keyifli türler.",
        "types": [
            {
                "key": "cift",
                "name": "Çift tanım",
                "summary": (
                    "Harf oyunu yoktur; ipucu, aynı kelimenin iki farklı anlamını yan "
                    "yana koyar."
                ),
                "indicators": [],
                "example": {
                    "clue": [
                        _run("Hem "),
                        _run("surat", TANIM),
                        _run(" hem "),
                        _run("sayı", TANIM),
                    ],
                    "enumeration": "3",
                    "parts": [
                        ("tanım 1", TANIM, "surat"),
                        ("tanım 2", TANIM, "sayı"),
                    ],
                    "solution": "ikisi de",
                    "answer": "YÜZ",
                },
            },
            {
                "key": "hepsi",
                "name": "Hepsi bir arada",
                "summary": (
                    "İpucunun tamamı hem tanım hem de kelime oyunudur; ikisi "
                    "birbirinden ayrılamaz. En nadir ve en ustalıklı ipucu türüdür. "
                    "Böyle bir ipucunda tanımı başta ya da sonda aramak işe yaramaz; "
                    "bütün cümle hem ne olduğunu anlatır hem de nasıl kurulduğunu."
                ),
                "indicators": [],
                "example": None,
            },
            {
                "key": "gorsel",
                "name": "Görsel ipuçları",
                "summary": "Bazen ipucu bir şakadır; harflerin kendisine bakmak gerekir.",
                "indicators": [],
                "example": {
                    "clue": [_run("HIİJKLMNO")],
                    "enumeration": "2",
                    "parts": [],
                    "solution": "Harfler H'den O'ya: H₂O",
                    "answer": "SU",
                },
            },
        ],
    },
]

SOLVING_TIPS = [
    "Önce tanımı ara: ipucunun ilk ya da son kelimeleri.",
    (
        "Gösterge kelimelerini tanımayı öğren; “bozuk”, “içinde”, "
        "“geri dönünce” gibi kelimeler sana ne yapacağını söyler."
    ),
    "Harf sayısını her zaman kontrol et.",
    (
        "Takılırsan ipucu al: ilk ipucu tanımı gösterir. Harf açmak ve ipucu almak "
        "serini bozmaz; sadece mührü açmak bozar."
    ),
]

ORIGIN = [
    (
        "Muamma, divan edebiyatında bir şiir türünün adı: bir ismin, harfler üzerinde "
        "oynanarak beyitlerin içine gizlendiği bir bilmece. Harf düşürmek, tersine "
        "çevirmek, parçaları birleştirmek… Bugünkü cryptic ipuçlarının "
        "teknikleriyle şaşırtıcı derecede benzer."
    ),
    (
        "Yani oynadığın oyun, bu toprakların yüzyıllık bir kelime geleneğinin modern "
        "hali. Adını da oradan alıyor."
    ),
]

CLOSING = "Hazırsan bugünün muamması seni bekliyor."

ROLE_CLASSES = {TANIM: "tanim", GOSTERGE: "gosterge", MALZEME: "malzeme"}


def glossary_groups():
    """Groups and types that actually carry indicator words."""
    groups = []
    for group in GROUPS:
        types = [kind for kind in group["types"] if kind["indicators"]]
        if types:
            groups.append({"label": group["label"], "types": types})
    return groups


def all_indicators():
    return [
        word for group in GROUPS for kind in group["types"] for word in kind["indicators"]
    ]
