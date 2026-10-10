#!/usr/bin/env python3
"""Additive TCExam adapter. Refuses unknown hooks before any database is touched."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
PAYLOAD = BASE / 'payload'
API = 'https://api.github.com/repos/tecnickcom/tcexam'

class CompatibilityError(RuntimeError):
    pass

def request_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Azmoon-Fa-installer', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)

def stable_tag(tags):
    stable = [t for t in tags if re.fullmatch(r'v?\d+\.\d+\.\d+', t['name'])]
    if not stable:
        raise CompatibilityError('No stable upstream tag found')
    return max(stable, key=lambda t: tuple(map(int, t['name'].lstrip('v').split('.'))))

def latest():
    tags = []
    for page in range(1, 51):
        batch = request_json(f'{API}/tags?per_page=100&page={page}')
        tags.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise CompatibilityError('Tag pagination limit reached; refusing an incomplete latest-version lookup')
    tag = stable_tag(tags)
    return {'tag': tag['name'], 'commit': tag['commit']['sha']}

def extract(archive, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        roots = set()
        total = 0
        for member in members:
            p = Path(member.name)
            if p.is_absolute() or '..' in p.parts or not p.parts or not (member.isfile() or member.isdir()):
                raise CompatibilityError('Unsafe upstream archive entry: ' + member.name)
            roots.add(p.parts[0])
            total += member.size
            if total > 1_000_000_000:
                raise CompatibilityError('Upstream archive too large')
        if len(roots) != 1:
            raise CompatibilityError('Archive must have one root directory')
        for member in members:
            parts = Path(member.name).parts[1:]
            if not parts:
                continue
            target = destination.joinpath(*parts)
            if not target.resolve().is_relative_to(destination):
                raise CompatibilityError('Archive escapes destination')
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, target.open('wb') as out:
                    shutil.copyfileobj(source, out)

def php_string(value):
    return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"

def set_define(text, name, value):
    pattern = re.compile(r"(?m)^define\('" + re.escape(name) + r"',\s*.*?\);", re.S)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise CompatibilityError(f'Expected one configuration constant {name}, found {len(matches)}')
    return pattern.sub(lambda _: f"define('{name}', {value});", text, count=1)

def replace_once(text, old, new, name):
    if text.count(old) != 1:
        raise CompatibilityError('Upstream hook changed: ' + name)
    return text.replace(old, new, 1)

def verify_payload():
    manifest = json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(PAYLOAD).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in PAYLOAD.rglob('*') if p.is_file()}
    if actual != manifest['files'] or any(p.is_symlink() for p in PAYLOAD.rglob('*')):
        raise CompatibilityError('Theme payload checksum mismatch')
    return actual

def plan(root, url, short, full):
    root = Path(root).resolve(strict=True)
    if root.is_symlink() or not (root / 'VERSION').is_file():
        raise CompatibilityError('Not a TCExam staging directory')
    if any((root / area / 'config').exists() for area in ('shared', 'public', 'admin')):
        raise CompatibilityError('Only fresh unconfigured source can be adapted. Existing site preserved.')
    if not re.fullmatch(r'v?\d+\.\d+\.\d+', (root / 'VERSION').read_text().strip()):
        raise CompatibilityError('Invalid VERSION')
    from urllib.parse import urlparse
    origin = urlparse(url)
    if origin.scheme not in ('http', 'https') or not origin.hostname or origin.path not in ('', '/') or origin.query or origin.fragment or origin.username or origin.password:
        raise CompatibilityError('Enter an HTTP(S) origin without a path, query or credentials')
    if not re.fullmatch(r'[A-Za-z0-9.:-]+', origin.netloc):
        raise CompatibilityError('Invalid hostname or port')
    try:
        origin.port
    except ValueError as e:
        raise CompatibilityError(str(e))
    for name, limit in ((short, 24), (full, 160)):
        if not name.strip() or len(name) > limit or any(ord(c) < 32 or ord(c) == 127 for c in name):
            raise CompatibilityError('Institution name is empty, too long or contains control characters')
    changes = {}
    def read(rel):
        p = root / rel
        if p.is_symlink() or not p.is_file():
            raise CompatibilityError('Missing or unsafe upstream file: ' + rel)
        return p.read_text(encoding='utf-8')
    def store(rel, text):
        changes[rel] = text

    shared = read('shared/config.default/tce_config.php')
    for key, value in {'K_LANGUAGE': "'fa'", 'K_LANGUAGE_SELECTOR': 'false', 'K_PASSWORD_RESET': 'false',
                       'K_AVAILABLE_LANGUAGES': "serialize(['fa' => 'فارسی'])",
                       'K_TIMEZONE': "'Asia/Tehran'", 'K_COOKIE_SECURE': 'true' if origin.scheme == 'https' else 'false'}.items():
        shared = set_define(shared, key, value)
    shared = replace_once(shared, '<?php', "<?php\nrequire_once __DIR__ . '/../azmoon/runtime.php';", 'runtime boot')
    shared = shared.replace('//date_default_timezone_set(K_TIMEZONE);', 'date_default_timezone_set(K_TIMEZONE);')
    store('shared/config.default/tce_config.php', shared)

    for area, prefix, theme in (('admin', 'K_TCEXAM', 'K_ADMIN_THEME'), ('public', 'K_SITE', 'K_PUBLIC_THEME')):
        rel = area + '/config.default/tce_config.php'
        cfg = read(rel)
        for key, val in {theme: "'azmoon'", prefix+'_TITLE': "AZMOON_BRAND_FULL", prefix+'_DESCRIPTION': "'سامانه آزمون آنلاین ' . AZMOON_BRAND_FULL", prefix+'_KEYWORDS': "'آزمون، سنجش، آموزش'", prefix+'_ICON': "'../../shared/azmoon/mark.svg'"}.items():
            cfg = set_define(cfg, key, val)
        if area == 'public':
            cfg = set_define(cfg, 'K_ENABLE_PUBLIC_PDF', 'true')
            cfg = set_define(cfg, 'K_MAX_MEMORY_LIMIT', "'256M'")
        store(rel, cfg)
        headrel = area + '/code/tce_xhtml_header.php'
        head = read(headrel)
        head = replace_once(head, "echo '</head>' . K_NEWLINE;", "Azmoon_head();\necho '</head>' . K_NEWLINE;", area+' head')
        store(headrel, head)
        headerrel = area + '/code/tce_page_header.php'
        header = read(headerrel)
        header = replace_once(header, "echo '<div class=\"left\"></div>' . K_NEWLINE;", "Azmoon_brand_header();", area+' brand')
        if area == 'admin':
            header = replace_once(header, "echo '</nav>' . K_NEWLINE;", "Azmoon_settings_link();\necho '</nav>' . K_NEWLINE;", 'settings link')
        store(headerrel, header)
        changes[area+'/styles/azmoon.css'] = '@import url("../../shared/azmoon/theme.css?v=1.0.0");\n'
        changes[area+'/styles/azmoon_rtl.css'] = changes[area+'/styles/azmoon.css']
        changes[area+'/config.default/theme/azmoon.php'] = '<?php\n// Assets are loaded in the head to prevent visual flicker.\n'

    timerrel = 'shared/jscripts/timer.js'
    timer = replace_once(read(timerrel), "let sign = '-';", "let sign = '';", 'countdown presentation')
    store(timerrel, timer)
    footerrel = 'shared/code/tce_page_userbar.php'
    footer = read(footerrel).replace('TCExam</a> ver. ', 'TCExam</a> نسخه ').replace(' - Copyright &copy;', ' · حقوق مؤلف &copy;')
    store(footerrel, footer)

    pdfrel = 'shared/config.default/tce_pdf.php'
    pdf = read(pdfrel)
    for key, value in {'PDF_HEADER_TITLE': 'AZMOON_BRAND_FULL', 'PDF_HEADER_STRING': "AZMOON_BRAND_SHORT . ' | کارنامه آزمون'", 'PDF_HEADER_LOGO': "'azmoon-mark.png'", 'PDF_AUTHOR': 'AZMOON_BRAND_FULL', 'PDF_FONT_SIZE_DATA': '9'}.items():
        pdf = set_define(pdf, key, value)
    store(pdfrel, pdf)
    editorrel = 'admin/code/tce_functions_tcecode_editor.php'
    editor = read(editorrel)
    icons = set(re.findall(r'buttons/([a-z]+)\.gif', editor))
    if not icons or any(not (PAYLOAD / 'images/azmoon-icons' / (icon + '.svg')).is_file() for icon in icons):
        raise CompatibilityError('Editor icon contract changed')
    editor = re.sub(r'buttons/([a-z]+)\.gif', r'azmoon-icons/\1.svg', editor)
    labels = {'bold':'ضخیم', 'italic':'مورب', 'underline':'زیرخط', 'strikethrough':'خط‌خورده', 'small':'متن کوچک', 'subscript':'زیرنویس', 'superscript':'بالانویس', 'link':'پیوند', 'unordered list':'فهرست بدون شماره', 'ordered list':'فهرست شماره‌دار', 'list item':'مورد فهرست', 'LRT':'چپ به راست', 'RTL':'راست به چپ', 'code':'کد', 'latex':'فرمول لاتک', 'mathml':'فرمول ریاضی', 'object':'رسانه'}
    for old, new in labels.items():
        editor = editor.replace("getImageButton('" + old + "'", "getImageButton('" + new + "'")
    for old, new in {'background-color':'رنگ پس‌زمینه', 'color':'رنگ متن'}.items():
        for attribute in ('alt', 'title', 'aria-label'):
            editor = editor.replace(attribute + '=\"' + old + '\"', attribute + '=\"' + new + '\"')
    for old, new in {'xx-small':'بسیار ریز', 'x-small':'ریز', 'small':'کوچک', 'medium':'متوسط', 'large':'بزرگ', 'x-large':'خیلی بزرگ', 'xx-large':'بسیار بزرگ'}.items():
        editor = editor.replace('>' + old + '</option>', '>' + new + '</option>')
    store(editorrel, editor)

    regrel = 'shared/config.default/tce_user_registration.php'
    store(regrel, set_define(read(regrel), 'K_USRREG_ENABLED', 'false'))
    statsrel = 'shared/code/tce_functions_test_stats.php'
    stats = read(statsrel).replace("date('i:s',", "gmdate('i:s',")
    start = stats.index('function F_printUserTestStat(')
    end = stats.index('\n/**', start)
    function = stats[start:end]
    option_start = function.index("                        $ret .= '<li>';")
    option_end = function.index("                        $ret .= F_decode_tcecode($ma['answer_description']);", option_start)
    function = function[:option_start] + "                        $ret .= Azmoon_result_option($m, $ma);\n" + function[option_end:]
    meta_start = function.index("            $ret .= '<strong>['")
    meta_end = function.index('            // display question description', meta_start)
    function = function[:meta_start] + "            $ret .= Azmoon_question_meta($m);\n" + function[meta_end:]
    store(statsrel, stats[:start] + function + stats[end:])

    menurel = 'public/code/tce_page_menu.php'
    menu = read(menurel)
    menu = replace_once(menu, "'enabled' => $_SESSION['session_user_level'] > K_AUTH_PUBLIC_TEST_RESULTS,", "'enabled' => $_SESSION['session_user_level'] >= K_AUTH_PUBLIC_TEST_RESULTS && $_SESSION['session_user_level'] > 0,", 'student results navigation')
    store(menurel, menu)

    resultrel = 'public/code/tce_show_result_user.php'
    result = read(resultrel)
    marker = "echo '<div class=\"tceformbox\">' . K_NEWLINE;"
    result = replace_once(result, marker, marker + "\nAzmoon_result_summary($teststat);\nAzmoon_print_button();", 'result summary/print')
    result = replace_once(result, "F_printTestStat($test_id, 0, $user_id, 0, 0, $testuser_id, $teststat, 2, true)", "Azmoon_subject_summary($teststat)", 'student subject summary')
    store(resultrel, result)

    # Keep reporting access tied to the completed attempt and its publication flags.
    pdfresultrel = 'public/code/tce_pdf_results.php'
    pdfresult = read(pdfresultrel)
    pdfresult = replace_once(pdfresult, "require_once '../../shared/code/tce_authorization.php';", "$pagelevel = K_AUTH_PUBLIC_TEST_RESULTS;\nrequire_once '../../shared/code/tce_authorization.php';\nif (!K_ENABLE_PUBLIC_PDF) { http_response_code(403); exit(); }", 'PDF access level')
    pdfresult = replace_once(pdfresult, "$_REQUEST['testuser_id'] > 1", "$_REQUEST['testuser_id'] > 0", 'first attempt PDF')
    old_auth = "    if (!isset($_REQUEST['email']) && !F_isAuthorizedUser(K_TABLE_TESTS, 'test_id', $test_id, 'test_user_id')) {\n        exit();\n    }"
    new_auth = """    if ($testuser_id > 0) {
        $azSql = 'SELECT test_report_to_users, test_results_to_users FROM ' . K_TABLE_TEST_USER . ', ' . K_TABLE_TESTS . ' WHERE testuser_test_id=test_id AND testuser_id=' . $testuser_id . ' AND test_id=' . $test_id . ' AND testuser_user_id=' . $user_id . ' AND testuser_status>3';
        $azResult = F_db_query($azSql, $db);
        $azRow = $azResult ? F_db_fetch_assoc($azResult) : false;
        if (!$azRow || !F_getBoolean($azRow['test_results_to_users']) || ($mode > 2 && !F_getBoolean($azRow['test_report_to_users']))) {
            http_response_code(403); exit('دسترسی به این کارنامه مجاز نیست.');
        }
    }"""
    pdfresult = replace_once(pdfresult, old_auth, new_auth, 'PDF attempt ownership')
    store(pdfresultrel, pdfresult)

    reportrel = 'shared/code/tce_pdf_report.php'
    report = read(reportrel).replace("date('i:s',", "gmdate('i:s',")
    report = report.replace('Powered by TCExam (www.tcexam.org)', 'با موتور TCExam (www.tcexam.org)')
    report = report.replace('<b><i><u>', '<b>').replace('</u></i></b>', '</b>').replace(" . ' [sec]'", " . ' (ثانیه)'")
    report = report.replace("$qtype = ['S', 'M', 'T', 'O'];", "$qtype = ['تک‌گزینه‌ای', 'چندگزینه‌ای', 'تشریحی', 'ترتیبی'];")
    option_start = report.index('                            [$marker, $markfill, $index, $idxfill]')
    option_end = report.index("                            $html .= '</tr>';", option_start) + len("                            $html .= '</tr>';")
    report = report[:option_start] + """                            $state = Azmoon_option_state($m, $ma);
                            $html .= '<tr><td style="width:35%;">' . Azmoon_e($state['label']) . '</td><td style="width:65%;">' . F_decode_tcecode($ma['answer_description']) . '</td></tr>';""" + report[option_end:]
    report = report.replace('<tr><td colspan="3">', '<tr><td colspan="2">')
    meta_start = report.index("                $html = '<table border=\"0.5\" cellpadding=\"2\" style=\"font-size:8pt;")
    meta_end = report.index("                $html .= '<div style=", meta_start)
    report = report[:meta_start] + """                $html = '<table border="0.5" cellpadding="5" style="font-size:9pt;"><tr style="background-color:#edf3ff;font-weight:bold;"><td style="width:55%;">سؤال ' . $itemcount . ' · ' . $qtype[$m['question_type'] - 1] . '</td><td style="width:25%;">نمره: ' . Azmoon_e($m['testlog_score'] === null ? 'در انتظار تصحیح' : $m['testlog_score']) . '</td><td style="width:20%;">زمان: ' . Azmoon_e($diff_time) . '</td></tr></table>';

""" + report[meta_end:]
    store(reportrel, report)

    schemarel = 'install/mysql_db_structure.sql'
    schema = read(schemarel)
    if 'CHARACTER SET utf8 COLLATE utf8_unicode_ci;' not in schema:
        raise CompatibilityError('Database Unicode schema contract changed')
    store(schemarel, schema.replace('CHARACTER SET utf8 COLLATE utf8_unicode_ci;', 'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'))

    tmxrel = 'shared/config.default/lang/language_tmx.xml'
    xmltext = read(tmxrel)
    tree = ET.fromstring(xmltext)
    translations = json.loads((BASE / 'translations.fa.json').read_text(encoding='utf-8'))
    missing = []
    for unit in tree.findall('.//tu'):
        key = unit.get('tuid')
        variants = {v.get('{http://www.w3.org/XML/1998/namespace}lang', v.get('lang', '')).lower(): v for v in unit.findall('tuv')}
        fa = variants.get('fa')
        if key in translations:
            if fa is None:
                fa = ET.SubElement(unit, 'tuv', {'{http://www.w3.org/XML/1998/namespace}lang': 'fa'})
            fa.clear()
            fa.set('{http://www.w3.org/XML/1998/namespace}lang', 'fa')
            ET.SubElement(fa, 'seg').text = translations[key]
        elif fa is None or not ''.join(fa.itertext()).strip():
            missing.append(key)
    if missing:
        raise CompatibilityError('Untranslated Persian keys in new upstream: ' + ', '.join(missing))
    store(tmxrel, '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(tree, encoding='unicode'))
    changes['shared/azmoon/data/branding.json'] = json.dumps({'short_name': short.strip(), 'full_name': full.strip(), 'accent': '#2563eb'}, ensure_ascii=False, indent=2)+'\n'
    changes['shared/azmoon/source.json'] = json.dumps({'engine': read('VERSION').strip(), 'theme': '1.0.0', 'upstream': 'https://github.com/tecnickcom/tcexam'}, indent=2)+'\n'
    return changes

def apply(root, **settings):
    verify_payload()
    changes = plan(root, **settings)
    root = Path(root).resolve()
    all_paths = set(changes) | set(verify_payload())
    for rel in all_paths:
        p = root / rel
        if not p.resolve().is_relative_to(root) or any(parent.is_symlink() for parent in [p, *p.parents] if parent.is_relative_to(root)):
            raise CompatibilityError('Unsafe adapter destination: '+rel)
    for rel, content in changes.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8', newline='\n')
    for rel in verify_payload():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PAYLOAD / rel, p)
    print(f'Compatible: adapted TCExam {changes["shared/azmoon/source.json"].strip()}')

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('latest')
    sub.add_parser('verify')
    x = sub.add_parser('extract'); x.add_argument('archive'); x.add_argument('destination')
    for cmd in ('check', 'apply'):
        x = sub.add_parser(cmd); x.add_argument('root'); x.add_argument('--url', required=True); x.add_argument('--short', required=True); x.add_argument('--full', required=True)
    a = p.parse_args()
    if a.command == 'latest': print(json.dumps(latest()))
    elif a.command == 'verify': print('Verified', len(verify_payload()), 'theme files')
    elif a.command == 'extract': extract(a.archive, a.destination)
    elif a.command == 'apply': apply(a.root, url=a.url, short=a.short, full=a.full)
    else: plan(a.root, a.url, a.short, a.full); print('Upstream hooks and Persian translations: compatible')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, CompatibilityError) as exc:
        print('ERROR: '+str(exc), file=sys.stderr); sys.exit(1)
