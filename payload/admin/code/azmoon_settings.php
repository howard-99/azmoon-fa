<?php
/** Editable institution identity; restricted to administrators. */
require_once '../config/tce_config.php';
$pagelevel = 10;
require_once '../../shared/code/tce_authorization.php';
if ((int)($_SESSION['session_user_level'] ?? 0) < 10) {
    http_response_code(403); exit('دسترسی مجاز نیست.');
}
require_once '../../shared/code/tce_functions_form.php';
$message = '';
$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_POST['csrf_token']) || !is_string($_POST['csrf_token']) || !checkCSRFToken($_POST['csrf_token'])) {
        http_response_code(403); exit('درخواست معتبر نیست. صفحه را تازه کنید.');
    }
    try {
        Azmoon_save_brand($_POST);
        // Redirect after save also refreshes the immutable per-request brand constants.
        header('Location: azmoon_settings.php?saved=1'); exit();
    } catch (InvalidArgumentException|RuntimeException $e) {
        $error = $e->getMessage();
    }
}
$thispage_title = 'هویت و ظاهر مؤسسه';
require_once 'tce_page_header.php';
$brand = Azmoon_brand();
echo '<div class="container"><div class="tceformbox az-settings">';
if (isset($_GET['saved'])) echo '<p class="az-success" role="status">تنظیمات مؤسسه ذخیره شد.</p>';
if ($error !== '') echo '<p class="az-error" role="alert">' . Azmoon_e($error) . '</p>';
echo '<p>نام مؤسسه در عنوان صفحات، سربرگ و کارنامه‌ها نمایش داده می‌شود.</p>';
echo '<form method="post" action="azmoon_settings.php">';
echo '<label for="short_name">نام کوتاه مؤسسه</label><input id="short_name" name="short_name" maxlength="24" required value="' . Azmoon_e($brand['short_name']) . '" />';
echo '<label for="full_name">نام کامل مؤسسه</label><input id="full_name" name="full_name" maxlength="160" required value="' . Azmoon_e($brand['full_name']) . '" />';
echo '<label for="accent">رنگ اصلی</label><input type="color" id="accent" name="accent" value="' . Azmoon_e($brand['accent']) . '" />';
echo F_getCSRFTokenField();
echo '<button type="submit">ذخیره تغییرات</button></form></div></div>';
require_once 'tce_page_footer.php';
