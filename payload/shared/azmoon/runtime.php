<?php
/** Azmoon Fa — Persian interface adapter, AGPL-3.0-or-later. */
function Azmoon_brand_path(): string {
    return __DIR__ . '/data/branding.json';
}
function Azmoon_brand(): array {
    $defaults = ['short_name' => 'آزمون', 'full_name' => 'سامانه آزمون آنلاین', 'accent' => '#2563eb'];
    $raw = @file_get_contents(Azmoon_brand_path());
    $data = $raw === false ? null : json_decode($raw, true);
    if (!is_array($data)) return $defaults;
    foreach (['short_name' => 24, 'full_name' => 160] as $key => $limit) {
        if (isset($data[$key]) && is_string($data[$key]) && mb_strlen($data[$key]) <= $limit && trim($data[$key]) !== '') {
            $defaults[$key] = $data[$key];
        }
    }
    if (isset($data['accent']) && preg_match('/^#[0-9a-fA-F]{6}$/D', $data['accent'])) $defaults['accent'] = $data['accent'];
    return $defaults;
}
function Azmoon_e($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
$azmoonBrand = Azmoon_brand();
define('AZMOON_BRAND_SHORT', $azmoonBrand['short_name']);
define('AZMOON_BRAND_FULL', $azmoonBrand['full_name']);
define('AZMOON_ACCENT', $azmoonBrand['accent']);
unset($azmoonBrand);

function Azmoon_head(): void {
    $area = defined('K_ADMIN_THEME') ? 'admin' : 'public';
    echo '<meta name="theme-color" content="' . Azmoon_e(AZMOON_ACCENT) . '" />';
    echo '<link rel="icon" type="image/svg+xml" href="../../shared/azmoon/mark.svg" />';
    echo '<style>:root{--brand:' . Azmoon_e(AZMOON_ACCENT) . ';}</style>';
    echo '<script defer src="../../shared/azmoon/theme.js?v=1.0.0"></script>';
    echo '<meta name="azmoon-area" content="' . $area . '" />';
}
function Azmoon_brand_header(): void {
    echo '<a class="az-brand" href="index.php" aria-label="' . Azmoon_e(AZMOON_BRAND_FULL) . '">';
    echo '<img src="../../shared/azmoon/mark.svg" alt="" width="46" height="46" />';
    echo '<span><b>' . Azmoon_e(AZMOON_BRAND_FULL) . '</b><small><bdi>' . Azmoon_e(AZMOON_BRAND_SHORT) . '</bdi> · سامانه آزمون آنلاین</small></span></a>';
}
function Azmoon_settings_link(): void {
    if ((int)($_SESSION['session_user_level'] ?? 0) < 10) return;
    echo '<a class="az-settings-link" href="azmoon_settings.php">هویت مؤسسه</a>';
}
function Azmoon_print_button(): void {
    echo '<div class="az-result-toolbar"><button type="button" class="az-print" onclick="window.print()">چاپ کارنامه / ذخیره PDF</button>';
    echo '<span>گزارش کامل با پاسخ‌ها و توضیحات قابل چاپ است.</span></div>';
}
function Azmoon_result_summary(array $stats): void {
    $t = $stats['testinfo'];
    $q = $stats['qstats'];
    $max = (float)($t['test_max_score'] ?? 0);
    $score = (float)($t['user_score'] ?? 0);
    $percent = $max > 0 ? round(100*$score/$max, 1) : null;
    $threshold = (float)($t['test_score_threshold'] ?? 0);
    $status = $threshold > 0 ? ($score >= $threshold ? 'قبول' : 'نیاز به تلاش بیشتر') : 'کارنامه آزمون';
    echo '<section class="az-score" aria-label="خلاصه نتیجه آزمون"><div><small>نتیجه تلاش شما</small><h2>' . Azmoon_e($status) . '</h2>';
    echo '<p>' . Azmoon_e($t['test_name'] ?? '') . '</p></div>';
    echo '<div class="az-score-value"><bdi>' . Azmoon_e($percent === null ? $score : $percent.'%') . '</bdi><small>نمره: <bdi>' . Azmoon_e($score . ' / ' . $max) . '</bdi></small></div></section>';
    echo '<div class="az-metrics">';
    foreach (['right'=>'پاسخ درست', 'wrong'=>'پاسخ نادرست', 'unanswered'=>'بی‌پاسخ', 'unrated'=>'در انتظار تصحیح'] as $key=>$label) {
        echo '<div><strong>' . Azmoon_e($q[$key] ?? 0) . '</strong><span>' . $label . '</span></div>';
    }
    echo '</div>';
}
function Azmoon_option_state(array $question, array $answer): array {
    $type = (int)$question['question_type'];
    $selected = (int)$answer['logansw_selected'];
    $right = F_getBoolean($answer['answer_isright']);
    $class = 'az-option';
    $label = '';
    if ($type === 4) {
        $position = (int)$answer['logansw_position'];
        $correct = (int)$answer['answer_position'];
        $class .= $position === $correct ? ' az-correct' : ' az-incorrect';
        $label = 'ترتیب شما: ' . ($position > 0 ? $position : 'بی‌پاسخ') . ' · ترتیب درست: ' . $correct;
    } else {
        if ($selected > 0) {
            $class .= $right ? ' az-correct az-selected' : ' az-incorrect az-selected';
            $label = 'انتخاب شما · ' . ($right ? 'پاسخ درست' : 'پاسخ نادرست');
        } elseif ($type === 1) {
            $class .= $right ? ' az-correct' : '';
            $label = $right ? 'پاسخ درست' : 'انتخاب نشده';
        } else {
            // MCMA false choices and omissions are not inferred from CSS colours.
            $class .= $selected < 0 ? '' : ($right ? ' az-incorrect' : ' az-correct');
            $label = ($selected < 0 ? 'بی‌پاسخ' : 'انتخاب شما: علامت زده نشده') . ' · پاسخ صحیح: ' . ($right ? 'درست' : 'نادرست');
        }
    }
    return ['class' => $class, 'label' => $label];
}
function Azmoon_result_option(array $question, array $answer): string {
    $state = Azmoon_option_state($question, $answer);
    return '<li class="' . $state['class'] . '"><span class="az-answer-label">' . Azmoon_e($state['label']) . '</span> ';
}
function Azmoon_save_brand(array $input): void {
    $data = [];
    foreach (['short_name' => 24, 'full_name' => 160] as $key=>$limit) {
        $value = $input[$key] ?? null;
        if (!is_string($value) || trim($value) === '' || mb_strlen($value) > $limit || preg_match('/[\x00-\x1f\x7f]/u', $value)) {
            throw new InvalidArgumentException('نام مؤسسه معتبر نیست؛ نام کوتاه حداکثر ۲۴ و نام کامل حداکثر ۱۶۰ نویسه باشد.');
        }
        $data[$key] = trim($value);
    }
    $data['accent'] = $input['accent'] ?? '#2563eb';
    if (!is_string($data['accent']) || !preg_match('/^#[0-9a-fA-F]{6}$/D', $data['accent'])) throw new InvalidArgumentException('رنگ انتخاب‌شده معتبر نیست.');
    $dir = dirname(Azmoon_brand_path());
    $lock = fopen($dir . '/branding.lock', 'c');
    if (!$lock || !flock($lock, LOCK_EX)) throw new RuntimeException('ذخیره تنظیمات ممکن نشد.');
    $temp = tempnam($dir, 'brand-');
    try {
        if (!$temp || file_put_contents($temp, json_encode($data, JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT|JSON_THROW_ON_ERROR)."\n") === false) {
            throw new RuntimeException('ذخیره تنظیمات ممکن نشد.');
        }
        chmod($temp, 0640);
        if (!rename($temp, Azmoon_brand_path())) throw new RuntimeException('جایگزینی تنظیمات ممکن نشد.');
    } finally {
        if ($temp && is_file($temp)) unlink($temp);
        flock($lock, LOCK_UN); fclose($lock);
    }
}

function Azmoon_question_meta(array $question): string {
    $score = $question['testlog_score'];
    $elapsed = '—';
    if (!empty($question['testlog_display_time']) && !empty($question['testlog_change_time'])) {
        $seconds = max(0, strtotime($question['testlog_change_time']) - strtotime($question['testlog_display_time']));
        $elapsed = gmdate('H:i:s', $seconds);
    }
    return '<div class="az-question-meta">نمره: ' . Azmoon_e($score === null ? 'در انتظار تصحیح' : $score) . ' · زمان پاسخ: <bdi>' . Azmoon_e($elapsed) . '</bdi></div>';
}
function Azmoon_subject_summary(array $stats): string {
    $html = '<table><caption>نتیجه به تفکیک درس</caption><thead><tr><th>درس</th><th>تعداد سؤال</th><th>درصد نمره</th><th>پاسخ درست</th><th>پاسخ نادرست</th></tr></thead><tbody>';
    foreach (($stats['qstats']['module'] ?? []) as $module) {
        $html .= '<tr><td>' . Azmoon_e($module['name'] ?? '') . '</td>';
        foreach (['recurrence', 'average_score_perc', 'right', 'wrong'] as $key) $html .= '<td>' . Azmoon_e($module[$key] ?? 0) . ($key === 'average_score_perc' ? '%' : '') . '</td>';
        $html .= '</tr>';
    }
    return $html . '</tbody></table>';
}
