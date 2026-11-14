"""Pure-file tests: safe on CI without AltDSS or a proprietary solver license."""
from pathlib import Path
import csv
import hashlib
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from course_utils.core import verify_inputs, new_output, INPUT,sha

class CourseIntegrityTests(unittest.TestCase):
    def test_all_input_hashes(self):
        self.assertEqual(verify_inputs()['status'],'PASS')
    def test_expected_feeders_and_licenses(self):
        for feeder in ('ieee123_base','ieee123_pesgm2027','ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic'):
            p=INPUT/'feeders'/feeder
            self.assertTrue((p/'IEEE123Master.dss').is_file())
            self.assertTrue((p/'OpenDSS_License.txt').is_file())
    def test_mpc_case_pins(self):
        import json
        root=INPUT/'mpc_baseline'
        pins=json.loads((root/'CASE_PINS.json').read_text())
        for name,digest in pins['files_sha256'].items():
            self.assertEqual(sha(root/name),digest)
    def test_no_generated_output_in_versioned_inputs(self):
        self.assertFalse((INPUT/'output').exists())
    def test_cli_lessons_exist(self):
        import ast
        for p in (HERE/'lessons').glob('lesson*.py'):
            self.assertTrue(any(isinstance(node,ast.FunctionDef) and node.name=='run' for node in ast.parse(p.read_text()).body),p.name)
if __name__=='__main__':unittest.main()
