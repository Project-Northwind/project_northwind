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

    def test_comparison_operators_survive_rendering(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        from PN_import_vnr import render
        text = render(self.n.parse('limit = { num_of_naval_factories > 0 count < 2 }'))
        self.assertIn('num_of_naval_factories > 0', text)
        self.assertIn('count < 2', text)

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

    def test_import_manifest_paths_and_naming(self):
        import json
        path = ROOT / 'docs/naval/PN_vnr_import_manifest.json'
        self.assertTrue(path.exists(), 'Import manifest is missing')
        entries = json.loads(path.read_text(encoding='utf-8'))['files']
        self.assertGreater(len(entries), 1500)
        for entry in entries:
            destination = ROOT / entry['destination']
            self.assertTrue(destination.exists(), entry['destination'])
            self.assertTrue(destination.name.startswith('PN_') or entry.get('exception'), entry['destination'])

    def test_inherited_and_alias_slots_use_defaults(self):
        hulls = {'base': self.n.parse('module_slots = { a = { required = yes allowed_module_categories = { engine } } b = a } default_modules = { a = motor }'), 'child': self.n.parse('archetype = base module_slots = inherit')}
        modules = {'motor': self.n.parse('category = engine')}
        design = self.n.parse('type = child modules = { b = motor }')
        self.assertEqual(self.n.check_design(design, hulls, modules), [])

    def test_northwind_fleet_conversion_preserves_inventory(self):
        import json
        mapping = ROOT / 'docs/naval/PN_naval_conversion.json'
        self.assertTrue(mapping.exists(), 'Northwind fleet conversion is missing')
        entries = json.loads(mapping.read_text(encoding='utf-8'))
        self.assertEqual(len(entries['ships']), 139)
        self.assertEqual(self.n.validate_custom_fleets(), [])

    def test_startup_uses_one_guarded_dispatcher(self):
        path = ROOT / 'common/scripted_effects/PN_naval_initialization.txt'
        self.assertTrue(path.exists(), 'Guarded initialization is missing')
        tree = self.n.parse(self.n.read(path))
        dispatcher = self.n.first(tree, 'PN_initialize_navy')
        guard = self.n.first(dispatcher, 'if')
        self.assertIn('PN_naval_initialized', str(self.n.first(guard, 'limit')))
        self.assertEqual(self.n.values(guard,'set_global_flag').count('PN_naval_initialized'), 1)
        for tag in ('GRE','LAT','SOV','SWE','TUR','UKR'):
            self.assertEqual(str(guard).count('PN_'+tag+'_1936_naval'), 1)
        startup = self.n.read(ROOT / 'common/on_actions/PN_naval_startup.txt')
        self.assertIn('PN_initialize_navy', startup)
        gui = self.n.read(ROOT / 'common/scripted_guis/PN_00_navy_rework_welcome_splash_gui.txt')
        self.assertNotIn('country_event = navy_rework.0', gui)

    def test_imported_designs_use_compatible_slots(self):
        hulls, modules = self.n.equipment_database(self.n.GAME, ROOT)
        issues = []
        for path in (ROOT / 'common/scripted_effects').glob('PN_*.txt'):
            for design in self.n.walk(self.n.parse(self.n.read(path)), 'create_equipment_variant'):
                if str(self.n.first(design,'type','')).startswith('vnr_'):
                    issues.extend(f'{path.name}/{self.n.first(design,"name")}: {i}' for i in self.n.check_design(design,hulls,modules))
        self.assertEqual(issues, [])

    def test_naval_rewards_are_converted(self):
        import json
        path = ROOT / 'docs/naval/PN_naval_rewards.json'
        self.assertTrue(path.exists(), 'Reachable naval rewards have not been converted')
        records = json.loads(self.n.read(path))
        self.assertGreaterEqual(len(records['designs']), 202)
        hulls, modules = self.n.equipment_database(self.n.GAME, ROOT)
        for filename in records['files']:
            tree = self.n.parse(self.n.read(ROOT / filename))
            for design in self.n.walk(tree,'create_equipment_variant'):
                hull = str(self.n.first(design,'type',''))
                self.assertFalse(hull.startswith('ship_hull_'), f'{filename}: {hull}')
                if hull.startswith(('vnr_ship_', 'PN_ship_')):
                    self.assertEqual(self.n.check_design(design,hulls,modules), [], f'{filename}: {self.n.first(design,"name")}')

    def test_custom_production_preserves_orders_and_progress(self):
        checker = getattr(self.n, 'validate_custom_production', None)
        self.assertIsNotNone(checker, 'Starting shipyard orders are not validated')
        self.assertEqual(checker(), [])

    def test_custom_startup_prepares_designs_without_dlc_gate(self):
        import json
        init = self.n.first(self.n.first(self.n.parse(self.n.read(ROOT/'common/scripted_effects/PN_naval_initialization.txt')), 'PN_initialize_navy'), 'if')
        data=json.loads(self.n.read(ROOT/'docs/naval/PN_naval_conversion.json'))
        for tag in ('GRE','LAT','SOV','SWE','TUR','UKR'):
            country=self.n.first(init,tag)
            self.assertTrue(any(str(k).startswith(f'PN_{tag}_naval_design_') for k,v in country),tag)
        effects=self.n.parse(self.n.read(ROOT/'common/scripted_effects/PN_naval_starting_variants.txt'))
        for effect,body in effects:
            self.assertTrue(list(self.n.walk(body,'has_country_flag')), effect)

    def test_designer_layouts_cover_every_hull_module_slot(self):
        self.assertEqual(self.n.validate_designer_layouts(), [])

    def test_carrier_wings_keep_engine_supported_ai_deployment(self):
        units=self.n.first(self.n.parse(self.n.read(ROOT/'common/units/air.txt')),'sub_units')
        for key in ('cv_fighter','cv_cas','cv_nav_bomber'):
            unit=self.n.first(units,key)
            self.assertGreater(int(self.n.first(unit,'land_air_wing_size')),0,key)
            self.assertGreater(int(self.n.first(unit,'carrier_air_wing_size')),0,key)
            self.assertGreater(int(self.n.first(unit,'submarine_carrier_air_wing_size')),0,key)


if __name__ == '__main__':
    unittest.main()
