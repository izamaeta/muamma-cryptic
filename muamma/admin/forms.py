from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional, Regexp

TECHNIQUES = [
    ("anagram", "Anagram"),
    ("hidden", "Gizli kelime"),
    ("initials", "Baş, son ve orta harfler"),
    ("reversal", "Ters çevirme"),
    ("synonym", "Eşanlamlılar"),
    ("charade", "Birleştirme"),
    ("container", "İç içe"),
    ("deletion", "Harf atma"),
    ("abbreviation", "Kısaltmalar"),
    ("double_definition", "Çift tanım"),
    ("andlit", "&lit"),
    ("visual", "Görsel ipuçları"),
    ("foreign", "Yabancı kelimeler"),
    ("letter_names", "Harf adları"),
    ("homophone", "Sesteş"),
    ("cryptic_definition", "Cryptic tanım"),
    ("other", "Diğer"),
]


class LoginForm(FlaskForm):
    email = EmailField("E-posta", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Şifre", validators=[DataRequired(), Length(max=256)])


class PuzzleForm(FlaskForm):
    kind = SelectField("Tür", choices=[("daily", "Günlük"), ("practice", "Tadımlık")])
    status = SelectField("Durum", choices=[("draft", "Taslak"), ("ready", "Hazır")])
    clue = TextAreaField("İpucu", validators=[DataRequired(), Length(max=500)])
    definition = StringField(
        "Tanım (ipucunda geçtiği haliyle, yoksa boş bırak)",
        validators=[Optional(), Length(max=200)],
    )
    answer = StringField("Cevap", validators=[DataRequired(), Length(max=64)])
    enumeration = StringField(
        "Harf sayısı (örn. 5 veya 4,3)",
        validators=[
            DataRequired(),
            Regexp(r"^\d+([,-]\d+)*$", message="Örnek: 5, 4,3 veya 3-4"),
        ],
    )
    hints = TextAreaField(
        "Ek ipuçları (her satıra bir tane)", validators=[Optional(), Length(max=1000)]
    )
    explanation = TextAreaField("Açıklama", validators=[DataRequired(), Length(max=2000)])
    technique = SelectField("Teknik", choices=TECHNIQUES)
    difficulty = SelectField(
        "Zorluk", choices=[(1, "Kolay"), (2, "Orta"), (3, "Zor")], coerce=int
    )
    publish_date = DateField("Yayın tarihi", validators=[Optional()])
    next_free_day = BooleanField("Sıradaki boş güne koy")