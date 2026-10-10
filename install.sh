#!/usr/bin/env bash
# Azmoon Fa — fresh Ubuntu 24.04 installer. AGPL-3.0-or-later.
set -Eeuo pipefail
umask 077
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
APP=/var/www/azmoon-fa
STATE=/var/lib/azmoon-fa
SITE=/etc/apache2/sites-available/azmoon-fa.conf
BUILD=''
STEP='بررسی اولیه'
fail(){ printf '\nخطا: %s\n' "$*" >&2; exit 1; }
say(){ printf '\n%s\n' "$*"; }
cleanup(){
  if [[ -n "$BUILD" && "$BUILD" == /var/tmp/azmoon-build.* && -d "$BUILD" ]]; then
    # Preserve diagnostic files and generated configuration if database setup began.
    if [[ -f "$STATE/db-created" ]]; then
      printf '\nپوشه بررسی نصب ناموفق: %s\n' "$BUILD" >&2
    else
      rm -rf -- "$BUILD"
    fi
  fi
}
trap cleanup EXIT
trap 'printf "\nنصب در مرحله «%s» ناموفق شد (خط %s). گزارش: /var/log/azmoon-fa-install.log\n" "$STEP" "$LINENO" >&2' ERR
case "${1:-}" in
  --check)
    python3 "$BASE/tools/adapter.py" verify
    python3 -m unittest discover -s "$BASE/tests" -p 'test_*.py'
    for script in "$BASE"/*.sh; do bash -n "$script"; done
    exit 0;;
  --help) printf 'sudo bash install.sh\nbash install.sh --check\n'; exit 0;;
  '') ;;
  *) fail 'گزینه نامعتبر؛ --help را ببینید.';;
esac
[[ $# -le 1 ]] || fail 'تعداد گزینه‌ها معتبر نیست.'
[[ $EUID -eq 0 ]] || fail 'نصب را با sudo اجرا کنید.'
[[ -t 0 ]] || fail 'نصب را در ترمینال تعاملی اجرا کنید.'
# /etc/os-release is supplied by the target OS.
# shellcheck disable=SC1091
[[ "$(. /etc/os-release; printf '%s:%s' "$ID" "$VERSION_ID")" == ubuntu:24.04 ]] || fail 'این نصب‌کننده برای Ubuntu Server 24.04 است.'
for command in python3 flock ip; do command -v "$command" >/dev/null || fail "ابزار لازم موجود نیست: $command"; done
exec 9>/run/lock/azmoon-fa-install.lock
flock -n 9 || fail 'نصب دیگری در حال اجرا است.'
[[ ! -e "$APP" && ! -e "$SITE" && ! -e "$STATE" ]] || fail 'نصب قبلی یا نیمه‌تمام شناسایی شد. هیچ فایل یا آزمونی بازنویسی نمی‌شود؛ راهنمای بازیابی را بخوانید.'
python3 "$BASE/tools/adapter.py" verify
say 'آزمون‌فا | نصب سامانه آزمون فارسی'
read -r -p 'نام کوتاه مؤسسه: ' BRAND_SHORT
read -r -p 'نام کامل مؤسسه: ' BRAND_FULL
ADDR="$(ip -o -4 addr show scope global | awk 'NR==1 {print $4}')"
SERVER_IP="${ADDR%%/*}"
[[ -n "$SERVER_IP" ]] || SERVER_IP=127.0.0.1
read -r -p "آدرس سامانه با http یا https [http://$SERVER_IP]: " ORIGIN
ORIGIN="${ORIGIN:-http://$SERVER_IP}"
NETWORK="$(python3 - "$ADDR" <<'PY'
import ipaddress,sys
try: print(ipaddress.ip_interface(sys.argv[1]).network)
except ValueError: print('127.0.0.0/8')
PY
)"
read -r -p "شبکه مجاز (CIDR) [$NETWORK]: " ALLOWED
ALLOWED="${ALLOWED:-$NETWORK}"
TLS_CERT=''; TLS_KEY=''
if [[ "$ORIGIN" == https://* ]]; then
  read -r -p 'مسیر کامل گواهی TLS موجود: ' TLS_CERT
  read -r -p 'مسیر کامل کلید TLS موجود: ' TLS_KEY
fi
read -r -p 'نام کاربری مدیر [admin]: ' ADMIN_NAME
ADMIN_NAME="${ADMIN_NAME:-admin}"
while :; do
  read -r -s -p 'رمز مدیر (حداقل ۱۲ نویسه): ' ADMIN_PASSWORD; printf '\n'
  [[ ${#ADMIN_PASSWORD} -ge 12 && ${#ADMIN_PASSWORD} -le 72 ]] || { say 'رمز بین ۱۲ و ۷۲ نویسه باشد.'; continue; }
  read -r -s -p 'تکرار رمز مدیر: ' PASSWORD_REPEAT; printf '\n'
  [[ "$ADMIN_PASSWORD" == "$PASSWORD_REPEAT" ]] && break
  say 'رمزها یکسان نیستند.'
done
unset PASSWORD_REPEAT
export AZ_ADMIN_NAME="$ADMIN_NAME" AZ_ADMIN_PASSWORD="$ADMIN_PASSWORD"
VALID="$(python3 - "$ORIGIN" "$ALLOWED" "$BRAND_SHORT" "$BRAND_FULL" "$TLS_CERT" "$TLS_KEY" <<'PY'
import ipaddress,re,sys,os
from urllib.parse import urlparse
origin,network,short,full,cert,key=sys.argv[1:]
u=urlparse(origin)
if u.scheme not in ('http','https') or not u.hostname or u.path not in ('','/') or u.query or u.fragment or u.username or u.password: sys.exit('آدرس سامانه معتبر نیست؛ فقط مبدأ را وارد کنید.')
if not re.fullmatch(r'[A-Za-z0-9.:-]+',u.netloc): sys.exit('نام میزبان معتبر نیست.')
port=u.port or (443 if u.scheme=='https' else 80)
if not 1 <= port <= 65535: sys.exit('پورت معتبر نیست.')
n=ipaddress.ip_network(network,strict=False)
for value,limit in ((short,24),(full,160)):
    if not value.strip() or len(value)>limit or any(ord(c)<32 or ord(c)==127 for c in value): sys.exit('نام مؤسسه معتبر نیست.')
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{2,47}',os.environ['AZ_ADMIN_NAME']): sys.exit('نام مدیر باید با حرف لاتین شروع شود و ۳ تا ۴۸ نویسه باشد.')
if not 12 <= len(os.environ['AZ_ADMIN_PASSWORD'].encode()) <= 72: sys.exit('رمز مدیر باید ۱۲ تا ۷۲ بایت باشد.')
if u.scheme=='https':
    for file in (cert,key):
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+',file) or not os.path.isfile(file): sys.exit('مسیر گواهی یا کلید معتبر نیست.')
print(u.hostname); print(port); print(n); print(origin.rstrip('/'))
PY
)" || fail 'تنظیمات را اصلاح کنید.'
mapfile -t SETTINGS <<< "$VALID"
HOST="${SETTINGS[0]}"; PORT="${SETTINGS[1]}"; ALLOWED="${SETTINGS[2]}"; ORIGIN="${SETTINGS[3]}"
printf '\nمؤسسه: %s (%s)\nآدرس: %s\nشبکه: %s\n' "$BRAND_FULL" "$BRAND_SHORT" "$ORIGIN" "$ALLOWED"
read -r -p 'شروع نصب؟ [y/N]: ' CONFIRM
[[ "$CONFIRM" =~ ^[yY]$ ]] || exit 0
install -m 600 /dev/null /var/log/azmoon-fa-install.log
exec > >(tee -a /var/log/azmoon-fa-install.log) 2>&1
STEP='نصب پیش‌نیازها'
say '[۱/۸] نصب پیش‌نیازهای سرور'
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends apache2 libapache2-mod-php8.3 php8.3-cli php8.3-mysql php8.3-gd php8.3-intl php8.3-bcmath php8.3-mbstring php8.3-zip php8.3-curl php8.3-xml mariadb-server composer curl ca-certificates make git unzip openssl
systemctl enable --now mariadb
mariadb -Nse 'SELECT 1' >/dev/null
[[ "$(mariadb -Nse "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='azmoon_fa'")" == 0 ]] || fail 'پایگاه داده azmoon_fa از قبل وجود دارد؛ نصب متوقف شد.'
[[ "$(mariadb -Nse "SELECT COUNT(*) FROM mysql.user WHERE User='azmoon_fa'")" == 0 ]] || fail 'کاربر پایگاه داده از قبل وجود دارد.'
BUILD="$(mktemp -d /var/tmp/azmoon-build.XXXXXXXX)"
SOURCE="$BUILD/source"
STEP='شناسایی و دریافت آخرین نسخه رسمی'
say '[۲/۸] شناسایی آخرین نسخه پایدار TCExam'
python3 "$BASE/tools/adapter.py" latest > "$BUILD/upstream.json"
TAG="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["tag"])' "$BUILD/upstream.json")"
COMMIT="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["commit"])' "$BUILD/upstream.json")"
[[ "$TAG" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ && "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || fail 'پاسخ نسخه از گیت‌هاب معتبر نیست.'
say "نسخه انتخاب‌شده: $TAG | $COMMIT"
curl --fail --location --proto '=https' --tlsv1.2 --retry 3 --connect-timeout 20 --max-time 600 "https://codeload.github.com/tecnickcom/tcexam/tar.gz/$COMMIT" -o "$BUILD/engine.tar.gz"
python3 "$BASE/tools/adapter.py" extract "$BUILD/engine.tar.gz" "$SOURCE"
[[ "$(tr -d '\r\n ' < "$SOURCE/VERSION")" == "${TAG#v}" ]] || fail 'نسخه محتوای بسته با تگ رسمی یکسان نیست.'
[[ -f "$SOURCE/install/install_cli.php" && -f "$SOURCE/composer.json" ]] || fail 'بسته رسمی کامل نیست.'
STEP='بررسی سازگاری قالب و فارسی'
say '[۳/۸] بررسی و اعمال قالب فارسی'
python3 "$BASE/tools/adapter.py" apply "$SOURCE" --url "$ORIGIN" --short "$BRAND_SHORT" --full "$BRAND_FULL"
cp "$BUILD/upstream.json" "$SOURCE/shared/azmoon/upstream.json"
STEP='آماده‌سازی کتابخانه‌ها و فونت PDF'
say '[۴/۸] آماده‌سازی وابستگی‌ها و خروجی PDF'
cd "$SOURCE"
COMPOSER_ALLOW_SUPERUSER=1 COMPOSER_PROCESS_TIMEOUT=1200 composer install --no-dev --no-interaction --prefer-dist --optimize-autoloader
[[ -f vendor/autoload.php && -d vendor/tecnickcom/tc-lib-pdf-font/target/fonts ]] || fail 'کتابخانه یا فونت PDF کامل نصب نشده است.'
make lang
[[ -f cache/lang/language_tmx_fa.php ]] || fail 'ساخت ترجمه فارسی ناموفق بود.'
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find shared/azmoon admin/code public/code shared/code shared/config.default admin/config.default public/config.default -name '*.php' -print0)
STEP='ایجاد پایگاه داده و مدیر'
say '[۵/۸] ایجاد پایگاه داده جدید'
install -d -m 700 "$STATE"
DB_PASSWORD="$(openssl rand -hex 32)"
# Keep recoverable credentials private before the first database mutation.
printf '[client]\nuser=azmoon_fa\npassword=%s\nhost=localhost\n' "$DB_PASSWORD" > "$STATE/db.cnf"
chmod 600 "$STATE/db.cnf"
touch "$STATE/db-created"
mariadb <<SQL
CREATE DATABASE azmoon_fa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'azmoon_fa'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON azmoon_fa.* TO 'azmoon_fa'@'localhost';
SQL
TCEXAM_DB_TYPE=MYSQL TCEXAM_DB_HOST=localhost TCEXAM_DB_PORT=3306 TCEXAM_DB_NAME=azmoon_fa TCEXAM_DB_USER=azmoon_fa TCEXAM_DB_PASSWORD="$DB_PASSWORD" TCEXAM_PATH_HOST="$ORIGIN" TCEXAM_PATH_TCEXAM=/ TCEXAM_PATH_MAIN="$APP/" TCEXAM_STANDARD_PORT="$PORT" php install/install_cli.php
php "$BASE/tools/set_admin.php" "$SOURCE"
unset ADMIN_PASSWORD AZ_ADMIN_PASSWORD AZ_ADMIN_NAME DB_PASSWORD
# CLI adds config files only after all compatibility checks have passed.
while IFS= read -r -d '' file; do php -l "$file" >/dev/null; done < <(find shared/config admin/config public/config -name '*.php' -print0)
STEP='انتشار فایل‌ها و حفاظت سرور'
say '[۶/۸] تنظیم دسترسی فایل‌ها و وب‌سرور'
install -d -m 755 /var/www
mv "$SOURCE" "$APP"
chown -R root:www-data "$APP"
find "$APP" -type d -exec chmod 750 {} +
find "$APP" -type f -exec chmod 640 {} +
for dir in cache images admin/backup shared/azmoon/data; do
  [[ -d "$APP/$dir" ]] || install -d -m 750 "$APP/$dir"
  chown -R www-data:www-data "$APP/$dir"
done
# No writable location may execute uploaded scripts.
cat > "$SITE" <<APACHE
<VirtualHost *:$PORT>
    ServerName $HOST
    DocumentRoot $APP
    DirectoryIndex index.php
    ServerSignature Off
    <Directory $APP>
        Options -Indexes -FollowSymLinks
        AllowOverride None
        Require ip $ALLOWED 127.0.0.1 ::1
    </Directory>
    <DirectoryMatch "^$APP/(install|tools|test|vendor|doc|docker|shared/(config|config.default|azmoon/data)|admin/(config|config.default|backup)|public/(config|config.default))(/|$)">
        Require all denied
    </DirectoryMatch>
    <DirectoryMatch "^$APP/(cache|images|admin/backup|shared/azmoon/data)(/|$)">
        <FilesMatch "(?i)\.(php[0-9]?|phtml|phar|cgi|pl|py|sh)$">
            Require all denied
        </FilesMatch>
    </DirectoryMatch>
    <FilesMatch "^(\.env|composer\.(json|lock)|Makefile|install\.log)$">
        Require all denied
    </FilesMatch>
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "same-origin"
    Header always set X-Frame-Options "SAMEORIGIN"
    php_admin_flag display_errors Off
    php_admin_flag log_errors On
    php_admin_value date.timezone Asia/Tehran
    php_admin_value session.cookie_httponly 1
    php_admin_value session.cookie_samesite Strict
    php_admin_value upload_max_filesize 25M
    php_admin_value post_max_size 30M
    ErrorLog \${APACHE_LOG_DIR}/azmoon-fa-error.log
    CustomLog \${APACHE_LOG_DIR}/azmoon-fa-access.log combined
APACHE
if [[ "$ORIGIN" == https://* ]]; then
  a2enmod ssl
  cat >> "$SITE" <<APACHE
    SSLEngine on
    SSLCertificateFile $TLS_CERT
    SSLCertificateKeyFile $TLS_KEY
    php_admin_value session.cookie_secure 1
APACHE
fi
printf '</VirtualHost>\n' >> "$SITE"
a2enmod headers
if ! grep -Eq "^[[:space:]]*Listen[[:space:]]+$PORT([[:space:]]|$)" /etc/apache2/ports.conf; then
  printf 'Listen %s\n' "$PORT" > /etc/apache2/conf-available/azmoon-fa-port.conf
  a2enconf azmoon-fa-port
fi
a2ensite azmoon-fa
apache2ctl configtest
systemctl enable --now apache2
systemctl reload apache2
STEP='آزمایش ورود و پایگاه داده'
say '[۷/۸] بررسی سلامت نصب'
mariadb --defaults-extra-file="$STATE/db.cnf" azmoon_fa -Nse 'SELECT COUNT(*) FROM tce_users WHERE user_level=10' | grep -Eq '^[1-9][0-9]*$'
CURL_TLS=()
[[ "$ORIGIN" != https://* ]] || CURL_TLS=(--cacert "$TLS_CERT")
curl --fail --silent --show-error --resolve "$HOST:$PORT:127.0.0.1" "${CURL_TLS[@]}" "$ORIGIN/public/code/index.php" > "$STATE/health.html"
grep -q 'shared/azmoon/theme.js' "$STATE/health.html" || fail 'قالب در پاسخ وب‌سرور دیده نشد.'
grep -q 'dir="rtl"' "$STATE/health.html" || fail 'صفحه فارسی بارگذاری نشده است.'
cat > "$STATE/access.txt" <<ACCESS
Institution: $BRAND_FULL ($BRAND_SHORT)
TCExam: $TAG ($COMMIT)
Student login: $ORIGIN/public/code/
Admin login: $ORIGIN/admin/code/
Institution settings: $ORIGIN/admin/code/azmoon_settings.php
Results: $ORIGIN/public/code/tce_test_allresults.php
Admin username: $ADMIN_NAME
Password: the password entered during installation (not stored in plaintext)
Database credentials: $STATE/db.cnf
ACCESS
chmod 600 "$STATE/access.txt"
rm -f "$STATE/health.html" "$STATE/db-created"
STEP='پایان نصب'
say '[۸/۸] نصب با موفقیت انجام شد'
printf '\nورود کاربران: %s/public/code/\nپنل مدیر: %s/admin/code/\nویرایش هویت: %s/admin/code/azmoon_settings.php\nکارنامه‌ها: %s/public/code/tce_test_allresults.php\nنام کاربری مدیر: %s\nرمز: همان رمز واردشده هنگام نصب\nنسخه موتور: %s\nگزارش دسترسی: %s/access.txt\n' "$ORIGIN" "$ORIGIN" "$ORIGIN" "$ORIGIN" "$ADMIN_NAME" "$TAG" "$STATE"
