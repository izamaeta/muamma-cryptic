# Canlıya çıkış

Bu belge sıfırdan bir sunucu kurar, siteyi açar, günceller ve gerekirse
yedekten geri döner. Adımlar sırayla okunacak şekilde yazıldı.

Hiçbir yerde gerçek şifre, anahtar ya da token yazmıyoruz: üretilen her sır
doğrudan sunucudaki `.env.production` dosyasına girilir, o dosya da git'e
girmez (`.gitignore`).

## İstek nereden geçiyor

```
Oyuncu  →  Cloudflare  →  Caddy  →  gunicorn (muamma)
                             │          │
                             │          ├── PostgreSQL
                             │          └── Redis (hız sınırı)
                             └── /static/* (doğrudan, bir yıl önbellek)
```

Dışarıya açık olan tek şey Caddy'nin 80 ve 443 portları. Veritabanı ve Redis
compose ağının içinde kalır, hiçbir portu yayınlamazlar.

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

- **Güvenlik grubu**: 80 ve 443 **yalnızca** Cloudflare aralıklarına açık
  olsun (https://www.cloudflare.com/ips/). Böylece origin'e doğrudan
  ulaşılamaz, herkes Cloudflare'den geçmek zorunda kalır. 22 yalnızca kendi
  adresine açık olsun; mümkünse SSM Session Manager kullan ve 22'yi hiç açma.

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
| `ACME_EMAIL` | Let's Encrypt bildirimleri için bir adres |
| `CONTACT_EMAIL` | Sitede görünen iletişim adresi |
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` çıktısı |
| `AWS_REGION` | Sunucunun bölgesi |
| `BACKUP_BUCKET` | 1. adımdaki kova |

`SESSION_COOKIE_SECURE=1`, `HSTS_ENABLED=1` ve `TRUSTED_PROXY_HOPS=2`
örnekte doğru geliyor; dokunma.

## 6. İlk açılış

```bash
docker compose -f compose.prod.yaml --env-file .env.production up -d --build
docker compose -f compose.prod.yaml --env-file .env.production ps
```

Migrationlar web konteyneri açılırken kendiliğinden çalışır, ayrı bir adım
yok. Kontrol etmek istersen:

```bash
docker compose -f compose.prod.yaml --env-file .env.production logs web | head -30
```

Yönetici hesabını aç (şifre sorulur, komut satırında görünmez):

```bash
docker compose -f compose.prod.yaml --env-file .env.production \
    exec web flask create-admin sen@ornek.com
```

Site şu an sunucunun kendi adresinde ayakta, ama sertifika için alan adının
sunucuya bakması gerekiyor. Sıradaki adım o.

## 7. Cloudflare

1. DNS'te alan adı için bir **A kaydı** aç, sunucunun genel IP'si.
2. Kaydı önce **DNS only** (gri bulut) bırak. Caddy sertifikayı böyle alır:

   ```bash
   docker compose -f compose.prod.yaml --env-file .env.production logs caddy | tail -20
   ```

   `certificate obtained successfully` satırını gör, sonra devam et.
3. Kaydı **Proxied** (turuncu bulut) yap.
4. SSL/TLS → Overview → **Full (strict)**.
5. SSL/TLS → Edge Certificates → **Always Use HTTPS** açık. Cloudflare
   ACME doğrulama adresini (`/.well-known/acme-challenge/`) bu
   yönlendirmeden muaf tutar, yani sertifika yenilemesi turuncu bulutla da
   çalışır.
6. Caching → HTML'i önbelleğe alan bir kural **kurma**: günün bulmacası ve
   oyuncunun durumu her istekte sunucudan gelmeli. `/static/*` zaten bir yıl
   önbellekli geliyor, Cloudflare onu kendiliğinden tutar.

Statik adreslerin sonunda `?v=<özet>` var: dosya değişince adres de
değişiyor, bu yüzden uzun önbellek güvenli ve dağıtımdan sonra önbellek
temizlemek gerekmiyor.

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
