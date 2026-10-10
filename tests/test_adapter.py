import io
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import adapter

class SafetyTests(unittest.TestCase):
    def test_latest_uses_numeric_stable_tags(self):
        tags=[{'name':x,'commit':{'sha':'a'*40}} for x in ('17.2.9','v17.2.11','17.2.10','18.0.0-beta','99.0.0-rc1')]
        self.assertEqual(adapter.stable_tag(tags)['name'],'v17.2.11')

    def test_extract_rejects_traversal_and_links(self):
        for name,kind in [('root/../../secret',tarfile.REGTYPE),('root/link',tarfile.SYMTYPE)]:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                archive=Path(tmp)/'bad.tar.gz'
                with tarfile.open(archive,'w:gz') as tar:
                    entry=tarfile.TarInfo(name);entry.type=kind;entry.linkname='/etc/passwd';entry.size=0;tar.addfile(entry,io.BytesIO())
                with self.assertRaises(adapter.CompatibilityError):adapter.extract(archive,Path(tmp)/'out')
                self.assertFalse((Path(tmp)/'secret').exists())

    def test_payload_integrity(self):
        self.assertGreater(len(adapter.verify_payload()),20)

    def test_php_string_escapes_quotes_and_backslashes(self):
        self.assertEqual(adapter.php_string("O'Neil\\School"),"'O\\'Neil\\\\School'")

    def test_brand_is_supplied_by_installation(self):
        self.assertFalse((adapter.PAYLOAD/'shared/azmoon/data/branding.json').exists())
        self.assertIn('AZMOON_BRAND_FULL',(adapter.PAYLOAD/'shared/azmoon/runtime.php').read_text(encoding='utf-8'))

class UpstreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('UPSTREAM_DIR')
        if not value:raise unittest.SkipTest('Set UPSTREAM_DIR to test the real upstream source')
        cls.root=Path(value).resolve()

    def test_preserves_exam_auth_and_pdf_controllers(self):
        changes=adapter.plan(self.root,'https://exam.example.org','ABC',"آموزشگاه نمونه O'Neil")
        for key in ('shared/code/tce_authorization.php','shared/code/tce_functions_authorization.php','shared/code/tce_functions_test.php','public/code/tce_test_execute.php'):
            self.assertNotIn(key,changes)
        self.assertIn('testuser_user_id=',changes['public/code/tce_pdf_results.php'])
        self.assertIn('AZMOON_BRAND_FULL',changes['shared/config.default/tce_pdf.php'])
        self.assertIn("'K_ENABLE_PUBLIC_PDF', true",changes['public/config.default/tce_config.php'])

    def test_invalid_origin_and_name(self):
        for url in ('https://exam.example.org/path','file:///tmp/x','https://evil@exam.example.org','https://exam.example.org?x=1'):
            with self.subTest(url=url),self.assertRaises(adapter.CompatibilityError):adapter.plan(self.root,url,'ABC','نمونه')
        with self.assertRaises(adapter.CompatibilityError):adapter.plan(self.root,'http://localhost','ABC','bad\nname')

    def test_changed_upstream_fails_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged=Path(tmp)/'engine';shutil.copytree(self.root,staged)
            file=staged/'public/code/tce_page_header.php'
            file.write_text('<?php // changed upstream',encoding='utf-8')
            before=(staged/'shared/config.default/tce_config.php').read_bytes()
            with self.assertRaises(adapter.CompatibilityError):adapter.apply(staged,url='http://localhost',short='ABC',full='نمونه')
            self.assertEqual(before,(staged/'shared/config.default/tce_config.php').read_bytes())
            self.assertFalse((staged/'shared/azmoon').exists())

    def test_refuses_existing_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged=Path(tmp)/'engine';shutil.copytree(self.root,staged)
            (staged/'shared/config').mkdir()
            with self.assertRaises(adapter.CompatibilityError):adapter.plan(staged,'http://localhost','ABC','نمونه')

if __name__=='__main__':unittest.main()
