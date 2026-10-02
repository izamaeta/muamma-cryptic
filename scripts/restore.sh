#!/usr/bin/env bash
# Yedekten geri yükleme. Sunucuda, depo kökünde çalıştırılır.
#
#   scripts/restore.sh --list            yedekleri listele
#   scripts/restore.sh                   en yeni yedeği geri yükle
#   scripts/restore.sh muamma/muamma-20261001T031500Z.sql.gz
#   scripts/restore.sh --yes <anahtar>   sormadan geri yükle
#
# Geri yükleme sırasında site kapalıdır: web durdurulur, veritabanı
# değiştirilir, web geri açılır.
set -euo pipefail

cd "$(dirname "$0")/.."

compose=(docker compose -f compose.prod.yaml --env-file .env.production)
run_in_backup=("${compose[@]}" run --rm --no-deps --entrypoint sh backup)

assume_yes=0
key=""
for argument in "$@"; do
    case "$argument" in
        --list)
            "${run_in_backup[@]}" -c 'aws s3 ls "s3://$BACKUP_BUCKET/$BACKUP_PREFIX/"'
            exit 0
            ;;
        --yes | -y)
            assume_yes=1
            ;;
        -*)
            echo "Bilinmeyen seçenek: $argument" >&2
            exit 2
            ;;
        *)
            key="$argument"
            ;;
    esac
done

echo "Geri yüklenecek: ${key:-en yeni yedek}"
echo "Bu işlem şu andaki veritabanının üstüne yazar."

if [ "$assume_yes" -eq 0 ]; then
    read -r -p "Devam edilsin mi? (evet yaz) " answer
    if [ "$answer" != "evet" ]; then
        echo "Vazgeçildi."
        exit 1
    fi
fi

echo "--> web durduruluyor"
"${compose[@]}" stop web

restore_status=0
echo "--> geri yükleniyor"
"${run_in_backup[@]}" /usr/local/bin/restore.sh "$key" || restore_status=$?

echo "--> web açılıyor"
"${compose[@]}" up -d web

if [ "$restore_status" -ne 0 ]; then
    echo "Geri yükleme başarısız oldu (çıkış kodu ${restore_status}); web yine açıldı." >&2
    exit "$restore_status"
fi

echo "Bitti. Siteyi bir kontrol et."
