#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'با sudo اجرا کنید.' >&2; exit 1; }
APP=/var/www/azmoon-fa
STATE=/var/lib/azmoon-fa
[[ -s "$STATE/access.txt" && -s "$STATE/db.cnf" ]] || { echo 'نصب کامل پیدا نشد.' >&2; exit 1; }
apache2ctl configtest
systemctl is-active --quiet apache2
systemctl is-active --quiet mariadb
mariadb --defaults-extra-file="$STATE/db.cnf" azmoon_fa -Nse 'SELECT 1' >/dev/null
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find "$APP/shared/azmoon" "$APP/admin/config" "$APP/public/config" "$APP/shared/config" -name '*.php' -print0)
[[ -s "$APP/vendor/autoload.php" && -s "$APP/cache/lang/language_tmx_fa.php" ]] || { echo 'کتابخانه‌ها یا ترجمه کامل نیستند.' >&2; exit 1; }
[[ -s "$APP/vendor/tecnickcom/tc-lib-pdf-font/target/fonts/dejavu/dejavusans.json" ]] || { echo 'فونت PDF یافت نشد.' >&2; exit 1; }
[[ "$(stat -c '%a' "$STATE/db.cnf")" == 600 ]] || { echo 'سطح دسترسی فایل رمز پایگاه داده باید ۶۰۰ باشد.' >&2; exit 1; }
[[ ! -w "$APP/shared/code/tce_authorization.php" || $(stat -c '%U' "$APP/shared/code/tce_authorization.php") == root ]] || exit 1
cat "$APP/shared/azmoon/source.json"
printf '\nسلامت سرویس‌ها، پایگاه داده، ترجمه و تنظیمات تأیید شد.\n'
cat "$STATE/access.txt"
