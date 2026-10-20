import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NavalValidationTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'tools/PN_validate_naval.py'
        self.assertTrue(path.exists(), 'Naval validator has not been implemented')
        spec = importlib.util.spec_from_file_location('naval', path)
        self.n = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.n)

    def test_comments_strings_and_repeated_keys(self):
        tree = self.n.parse('fleet = { name = "A # }" ship = { name = "One" } # }\n ship = { name = "Two" } }')
        fleet = self.n.first(tree, 'fleet')
        self.assertEqual(self.n.first(fleet, 'name'), 'A # }')
        self.assertEqual(len(self.n.values(fleet, 'ship')), 2)

    def test_unbalanced_script_rejected(self):
        with self.assertRaises(ValueError):
            self.n.parse('units = { ship = { }')

    def test_missing_hull_and_module_detected(self):
        design = self.n.parse('name = "Test" type = missing modules = { engine = missing_engine }')
        issues = self.n.check_design(design, {}, {})
        self.assertTrue(any('hull' in issue for issue in issues))
        hulls = {'missing': self.n.parse('module_slots = { engine = { required = yes allowed_module_categories = { engine } } }')}
        issues = self.n.check_design(design, hulls, {})
        self.assertTrue(any('missing_engine' in issue for issue in issues))

    def test_required_slots_and_categories(self):
        hulls = {'hull': self.n.parse('module_slots = { role = { required = yes allowed_module_categories = { cruiser_role } } }')}
        modules = {'dd': self.n.parse('category = destroyer_role')}
        self.assertTrue(self.n.check_design(self.n.parse('type = hull modules = {}'), hulls, modules))
        self.assertTrue(self.n.check_design(self.n.parse('type = hull modules = { role = dd }'), hulls, modules))

    def test_oob_owner_class_resolution(self):
        ship = self.n.parse('name = "Ship" equipment = { hull = { owner = UKR version_name = "Class" amount = 1 } }')
        self.assertTrue(self.n.check_ship(ship, {('SOV', 'Class'): 'hull'}))
        self.assertFalse(self.n.check_ship(ship, {('UKR', 'Class'): 'hull'}))


if __name__ == '__main__':
    unittest.main()
