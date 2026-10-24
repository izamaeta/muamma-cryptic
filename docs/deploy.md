# Canlıya çıkış

Bu belge sıfırdan bir sunucu kurar, siteyi açar, günceller ve gerekirse
yedekten geri döner. Adımlar sırayla okunacak şekilde yazıldı.

Hiçbir yerde gerçek şifre, anahtar ya da token yazmıyoruz: üretilen her sır
doğrudan sunucudaki `.env.production` dosyasına girilir, o dosya da git'e
girmez (`.gitignore`). Aynısı sertifika için de geçerli: origin sertifikası
ve özel anahtarı sunucudaki `certs/` klasöründe durur, o da git'e girmez.

## İstek nereden geçiyor

```
Oyuncu  →  Cloudflare  →  Caddy  →  gunicorn (muamma)
                             │          │
                             │          ├── PostgreSQL
                             │          └── Redis (hız sınırı)
                             └── /static/* (doğrudan, bir yıl önbellek)
```

Dışarıya açık olan tek şey Caddy'nin 443 portu, o da yalnızca Cloudflare
aralıklarına. Veritabanı ve Redis compose ağının içinde kalır, hiçbir portu
yayınlamazlar.

Caddy sertifikayı kendi almaz: Cloudflare'in verdiği Origin CA sertifikasını
dosyadan okur. Yani origin'e giden bağlantı da şifreli, ama o sertifikayı
tarayıcılar değil yalnızca Cloudflare doğrular.

## 1. S3 kovası

Yedekler için tek bir kova yeterli:

1. S3'te yeni kova aç (sunucuyla aynı bölge, örneğin `eu-central-1`).
2. **Block all public access** açık kalsın.
3. **Default encryption**: SSE-S3 (ya da istersen KMS).
4. **Versioning** açmak iyi fikir: yanlışlıkla silinen yedek geri gelir.
5. Kovanın adını not et, `.env.production` içinde `BACKUP_BUCKET` olacak.

Yedekler `s3://<kova>/muamma/muamma-<zaman>.sql.gz` biçiminde durur.

## 2. IAM rolü

Sunucu S3'e kendi kimliğiyle yazar. Ortam değişkenine anahtar koymuyoruz:
anahtar olmayınca sızacak bir şey de olmaz.

1. IAM'de yeni bir **rol** oluştur, güvenilen servis: EC2.
2. Şu satır içi politikayı ekle (`KOVA` yerine kendi kovanı yaz):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::KOVA/muamma/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::KOVA",
      "Condition": { "StringLike": { "s3:prefix": "muamma/*" } }
    }
  ]
}
```

3. Rolü sunucuya bağla (EC2 → Actions → Security → Modify IAM role).

## 3. Sunucu

- Tür: **t4g.small** (ARM, Graviton). Bütün imajlar arm64'te çalışır.
- İşletim sistemi: Ubuntu 24.04 LTS **arm64**.
- Disk: 20 GB gp3 yeter; veritabanı küçük, yedekler S3'te.

Örnek oluşturulurken iki ayar önemli:

- **IMDSv2: required**, **hop limit: 2**. Yedek alıcı bir konteynerin içinde
  çalışıyor; kimlik bilgisini örnek meta verisinden alabilmesi için ikinci
  atlamaya izin vermek gerekiyor. Sonradan değiştirmek için:

  ```bash
  aws ec2 modify-instance-metadata-options \
      --instance-id i-XXXXXXXX \
      --http-tokens required \
      --http-put-response-hop-limit 2
  ```

- **Güvenlik grubu**: sadece **443**, o da **yalnızca** Cloudflare
  aralıklarına açık olsun (https://www.cloudflare.com/ips/). 80'e hiç gerek
  yok: ACME doğrulaması yapılmıyor ve Cloudflare origin'e her zaman HTTPS
  ile bağlanıyor. Böylece origin'e doğrudan ulaşılamaz, herkes
  Cloudflare'den geçmek zorunda kalır. 22 yalnızca kendi adresine açık
  olsun; mümkünse SSM Session Manager kullan ve 22'yi hiç açma.

## 4. Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" |
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Son komuttan sonra bir kez çıkıp gir, grup üyeliği öyle geçerli oluyor.

## 5. Depo ve ayarlar

```bash
git clone https://github.com/izamaeta/muamma-cryptic.git
cd muamma-cryptic
cp .env.production.example .env.production
chmod 600 .env.production
```

`.env.production` içinde doldurulacaklar:

| Ayar | Ne yazılacak |
| --- | --- |
| `SECRET_KEY` | `openssl rand -hex 32` çıktısı. Değiştirirsen bütün oyuncuların ilerlemesi sıfırlanır. |
| `SITE_URL` | `https://muamma.com.tr` gibi, sonunda eğik çizgi olmadan |
| `SITE_DOMAIN` | Aynı alan adı, şemasız (`muamma.com.tr`) |
| `CONTACT_EMAIL` | Sitede görünen iletişim adresi |
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` çıktısı |
| `AWS_REGION` | Sunucunun bölgesi |
| `BACKUP_BUCKET` | 1. adımdaki kova |

`SESSION_COOKIE_SECURE=1`, `HSTS_ENABLED=1` ve `TRUSTED_PROXY_HOPS=2`
örnekte doğru geliyor; dokunma.

## 6. Cloudflare

Sertifika Cloudflare'den geliyor, bu yüzden bu adım ilk açılıştan önce
yapılır: dosyalar yerinde olmadan Caddy başlamaz.

**Önce origin sertifikası.** SSL/TLS → Origin Server → **Create
Certificate**:

- Özel anahtarı Cloudflare üretsin (varsayılan), tür **RSA (2048)**.
- Alan adları: `muamma.com.tr` ve `*.muamma.com.tr`.
- Geçerlilik: 15 yıl. Bitiş tarihini bir yere not et; bu sertifika
  kendiliğinden yenilenmiyor.

Açılan sayfada iki metin var ve **özel anahtar bir daha gösterilmiyor**.
İkisini de sunucuda şu dosyalara yaz:

```bash
mkdir -p certs && chmod 700 certs
nano certs/origin.pem          # Origin Certificate bloğu
nano certs/origin.key          # Private Key bloğu
chmod 600 certs/origin.key
```

`certs/` hem `.gitignore` hem `.dockerignore` içinde: anahtar ne git'e ne
de imaja girer. Caddy bu klasörü salt okunur görür.

Sertifikayı sonradan değiştirmek gerekirse — süresi dolduğunda ya da anahtar
sızdıysa — yeni dosyaları aynı yere yaz, sonra Caddy'yi yeniden başlat.
Dosyalar yalnızca açılışta okunuyor, `git pull` ile gelen bir güncelleme
Caddy'ye dokunmuyor:

```bash
docker compose -f compose.prod.yaml --env-file .env.production restart caddy
```

**Sonra DNS ve SSL ayarları:**

1. DNS'te alan adı için bir **A kaydı** aç, sunucunun genel IP'si, kayıt
   **Proxied** (turuncu bulut). Gri buluta hiç gerek yok: ACME doğrulaması
   yapılmıyor, ayrıca güvenlik grubu origin'e yalnızca Cloudflare'den gelen
   isteği alıyor.
2. SSL/TLS → Overview → **Full (strict)**. Origin sertifikasını doğrulayan
   mod bu; "Flexible" ya da "Full" seçilirse origin'e giden bağlantının
   doğrulanmadığı bir boşluk kalır.
3. SSL/TLS → Edge Certificates → **Always Use HTTPS** açık.
4. Caching → HTML'i önbelleğe alan bir kural **kurma**: günün bulmacası ve
   oyuncunun durumu her istekte sunucudan gelmeli. `/static/*` zaten bir
   yıl önbellekli geliyor, Cloudflare onu kendiliğinden tutar.

Statik adreslerin sonunda `?v=<özet>` var: dosya değişince adres de
değişiyor, bu yüzden uzun önbellek güvenli ve dağıtımdan sonra önbellek
temizlemek gerekmiyor.

## 7. İlk açılış

```bash
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
docker compose -f compose.prod.yaml --env-file .env.production ps
```

Migrationlar web konteyneri açılırken kendiliğinden çalışır, ayrı bir adım
yok. Kontrol etmek istersen:

```bash
docker compose -f compose.prod.yaml --env-file .env.production logs web | head -30
```

Caddy'nin sertifikayı okuduğunu da gör; dosyalar yoksa ya da bozuksa
konteyner burada durur:

```bash
docker compose -f compose.prod.yaml --env-file .env.production logs caddy | tail -20
```

Yönetici hesabını aç (şifre sorulur, komut satırında görünmez):

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    exec web flask create-admin sen@ornek.com
```

Son kontrol, artık alan adı üzerinden:

```bash
curl -I https://muamma.com.tr
```

## 8. Güncelleme

```bash
cd muamma-cryptic
git pull
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
```

Yeni web konteyneri açılırken migrationları da uygular. Sağlık kontrolü
geçene kadar Caddy eski konteynere konuşmaya devam eder, kısa bir kesinti
olur ama istek düşmez.

Sonrasında bir bakış:

```bash
docker compose -f compose.prod.yaml --env-file .env.production ps
docker compose -f compose.prod.yaml --env-file .env.production logs -n 50 web
curl -I https://muamma.com.tr
```

Eski imajlar diski doldurursa:

```bash
docker image prune -f
```

## 9. Yedekler

`backup` servisi her gün `BACKUP_AT` saatinde (varsayılan 03:15, sunucu saat
diliminde) şunu yapar:

1. `pg_dump` ile tam bir döküm alır, `gzip` ile sıkıştırır.
2. `s3://<kova>/muamma/muamma-<zaman>.sql.gz` adresine yükler.
3. 30 günden eski yedekleri siler (`BACKUP_KEEP_DAYS`).

Kurulumdan sonra bir yedeği elle alıp çalıştığını gör:

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    run --rm --entrypoint sh backup /usr/local/bin/backup.sh
```

Listeyi görmek için:

```bash
./scripts/restore.sh --list
```

Günlük çalıştığını doğrulamak için `docker compose ... logs backup`.

## 10. Yedekten geri dönme

```bash
./scripts/restore.sh --list                 # hangi yedekler var
./scripts/restore.sh                        # en yenisini geri yükle
./scripts/restore.sh muamma/muamma-20261001T001500Z.sql.gz
```

Script sırayla: onay ister, `web`'i durdurur, dökümü S3'ten doğrudan
`psql`'e akıtır, `web`'i geri açar. Döküm `--clean --if-exists` ile
alındığından mevcut tabloların üstüne yazar; yarım kalmış bir geri yükleme
olmasın diye `psql` ilk hatada durur.

Geri yükleme bittikten sonra bir günlük bulmacayı açıp oynanabildiğini
kontrol et.

## 11. Bulmaca aktarımı

Bulmacalar yerel makinede hazırlanıp sunucuya taşınabilir.

Yerelde:

```bash
flask export-puzzles bulmacalar.json
```

Sunucuda (dosyayı önce `scp` ile at):

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    cp bulmacalar.json web:/tmp/bulmacalar.json
docker compose -f compose.prod.yaml --env-file .env.production \
    exec web flask import-puzzles /tmp/bulmacalar.json \
    --start 2026-11-01 --dry-run
```

`--dry-run` ne olacağını yazar, hiçbir şey kaydetmez. Çıktı iyi görünüyorsa
aynı komutu `--dry-run` olmadan çalıştır.

Günlükler verilen tarihten itibaren **boş** günlere sırayla yerleşir; dolu
bir gün atlanır. Tadımlıklar tarihsiz eklenir. Aynı ipucu ve cevap daha önce
eklenmişse tekrar eklenmez, "atlandı" diye yazar. Cevap rehber sayfasındaki
çözümlü örneklerden biriyse uyarı çıkar — kayıt engellenmez, kararı sen
verirsin.

## 12. Ara sıra bakılacaklar

```bash
df -h                     # disk
docker compose -f compose.prod.yaml --env-file .env.production ps
docker compose -f compose.prod.yaml --env-file .env.production logs -n 100 web
```

Log'lar Docker tarafında döndürülüyor (dosya başına 10 MB, üç dosya), yani
disk log yüzünden dolmaz.

Sunucu paketlerini güncellemek için `sudo apt-get update && sudo apt-get
upgrade`; çekirdek güncellemesinden sonra yeniden başlatmak gerekirse
konteynerler `restart: unless-stopped` sayesinde kendiliğinden geri gelir.
