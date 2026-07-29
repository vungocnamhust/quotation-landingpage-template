import unittest

from db.base import Base


class DatabaseSchemaMetadataTests(unittest.TestCase):
    def test_expected_tables_are_registered_in_metadata(self):
        expected_tables = {
            "quotations",
            "quotation_requests",
            "quotation_documents",
            "quotation_document_revisions",
            "quotation_publications",
            "media_assets",
            "media_selections",
        }

        self.assertTrue(expected_tables.issubset(Base.metadata.tables.keys()))

    def test_current_document_table_uses_single_current_row_per_language(self):
        table = Base.metadata.tables["quotation_documents"]
        unique_constraint_names = {constraint.name for constraint in table.constraints if constraint.name}

        self.assertIn("uq_quotation_documents_quotation_lang", unique_constraint_names)

    def test_media_selection_table_keeps_slot_uniqueness_contract(self):
        table = Base.metadata.tables["media_selections"]
        index_names = {index.name for index in table.indexes if index.unique}

        self.assertIn("uq_media_selections_shared_slot_order", index_names)
        self.assertIn("uq_media_selections_lang_slot_order", index_names)


if __name__ == "__main__":
    unittest.main()
