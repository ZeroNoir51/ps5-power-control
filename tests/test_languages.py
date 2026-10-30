from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

PACKAGE = Path(__file__).parents[1] / 'src/ps5_power_control'


def strings(code):
    root = ET.parse(PACKAGE / f'languages/{code}.xml').getroot()
    ids = [e.attrib['id'] for e in root]
    return root.attrib['code'], ids


class LanguageTests(unittest.TestCase):
    def test_languages_match(self):
        code_en, en = strings('en')
        code_es, es = strings('es')
        self.assertEqual((code_en, code_es), ('en', 'es'))
        self.assertEqual(len(en), len(set(en)), 'duplicate ids in en.xml')
        self.assertEqual(sorted(en), sorted(es))

    def test_translated_literals_exist(self):
        source = (PACKAGE / 'app.py').read_text()
        used = set(re.findall(r"self\.tr\('([^']+)'\)", source))
        self.assertTrue(used)
        self.assertEqual(used - set(strings('en')[1]), set())


if __name__ == '__main__': unittest.main()
