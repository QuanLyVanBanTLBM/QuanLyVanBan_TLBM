"""Verify adoption decisions in addition to the fresh database catalog test."""
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock
from django.test import SimpleTestCase
from django.test import TestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from tools import records_release_bootstrap as bootstrap_verifier

migration = importlib.import_module('records.migrations.0005_canonical_fk_indexes')


class PostgresIndexAdoptionTests(SimpleTestCase):
    def run_adoption(self, mode):
        names = [('records_hoso', 'nguoi_lap_id', 'old_hoso', 'idx_hoso_nguoi_lap'),
                 ('records_loaivanban', 'ho_so_id', 'old_type', 'idx_loaivanban_hoso')]
        connection = MagicMock(vendor='postgresql')
        editor = MagicMock(connection=connection)
        editor.quote_name.side_effect = lambda name: '"' + name + '"'
        editor._create_index_name.side_effect = [row[2] for row in names]
        apps = MagicMock()
        apps.get_model.side_effect = [SimpleNamespace(_meta=SimpleNamespace(db_table=table, get_field=lambda name, col=column: SimpleNamespace(column=col))) for table, column, _, _ in names]
        catalog, plain = [], []
        for _, column, old, canonical in names:
            choices = {'generated': [old], 'adopted': [canonical], 'duplicate': [old, canonical], 'unknown': [canonical, 'unknown_index']}[mode]
            catalog.append({name: {'index': True, 'unique': False, 'columns': [column]} for name in choices})
            plain.append([(name,) for name in choices])
        connection.introspection.get_constraints.side_effect = catalog
        connection.cursor.return_value.__enter__.return_value.fetchall.side_effect = plain
        migration.canonicalize_fk_indexes(apps, editor)
        return editor

    def test_generated_fk_indexes_are_renamed_without_table_rebuild(self):
        editor = self.run_adoption('generated')
        self.assertEqual([call.args[0] for call in editor.execute.call_args_list], [
            'ALTER INDEX "old_hoso" RENAME TO "idx_hoso_nguoi_lap"',
            'ALTER INDEX "old_type" RENAME TO "idx_loaivanban_hoso"'])
        editor.add_index.assert_not_called()

    def test_adopted_canonical_indexes_issue_no_schema_sql(self):
        editor = self.run_adoption('adopted')
        editor.execute.assert_not_called()
        editor.add_index.assert_not_called()

    def test_only_known_duplicate_generated_fk_indexes_are_removed(self):
        editor = self.run_adoption('duplicate')
        self.assertEqual([call.args[0] for call in editor.execute.call_args_list], ['DROP INDEX "old_hoso"', 'DROP INDEX "old_type"'])

    def test_unknown_matching_index_stops_instead_of_dropping_it(self):
        with self.assertRaisesRegex(RuntimeError, 'unexpected'):
            self.run_adoption('unknown')


class BootstrapReadinessPlanningTests(TestCase):
    def test_ready_database_does_not_plan_backwards_to_old_core_target(self):
        targets = bootstrap_verifier.final_migration_targets(bootstrap_verifier)
        self.assertEqual(len(targets), len({app for app, name in targets}))
        self.assertEqual(dict(targets)['records'], '0006_align_release_schema')
        self.assertEqual(MigrationExecutor(connection).migration_plan(targets), [])

    def test_missing_final_migration_is_still_reported_as_forward_pending(self):
        MigrationRecorder(connection).record_unapplied('records', '0006_align_release_schema')
        targets = bootstrap_verifier.final_migration_targets(bootstrap_verifier)
        plan = MigrationExecutor(connection).migration_plan(targets)
        self.assertEqual([(migration.app_label, migration.name, backwards)
                          for migration, backwards in plan],
                         [('records', '0006_align_release_schema', False)])
