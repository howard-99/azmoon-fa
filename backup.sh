#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'با sudo اجرا کنید.' >&2; exit 1; }
APP=/var/www/azmoon-fa
STATE=/var/lib/azmoon-fa
[[ -s "$STATE/db.cnf" && -s "$APP/shared/config/tce_db_config.php" ]] || { echo 'نصب کامل شناسایی نشد.' >&2; exit 1; }
umask 077
install -d -m 700 "$STATE/backups"
BACKUP="$(mktemp -d "$STATE/backups/backup-$(date -u +%Y%m%dT%H%M%SZ).XXXXXXXX")"
# Consistent InnoDB snapshot; no locks or changes to running exam records.
mariadb-dump --defaults-extra-file="$STATE/db.cnf" --single-transaction --routines --triggers azmoon_fa | gzip > "$BACKUP/database.sql.gz"
tar -czf "$BACKUP/application.tar.gz" -C /var/www azmoon-fa
cp /etc/apache2/sites-available/azmoon-fa.conf "$BACKUP/apache.conf"
cp "$STATE/db.cnf" "$BACKUP/db.cnf"
cd "$BACKUP"
sha256sum database.sql.gz application.tar.gz apache.conf db.cnf > SHA256SUMS
printf 'پشتیبان کامل ایجاد شد: %s\nاین پوشه شامل اطلاعات محرمانه است و فقط برای مدیر سرور قابل خواندن است.\n' "$BACKUP"
