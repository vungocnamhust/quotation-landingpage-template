import unittest

from core.kernel.ids import generate_id


class KernelIdsTests(unittest.TestCase):
    def test_generated_id_has_expected_prefix_and_length(self):
        generated = generate_id("sup")
        prefix, _, body = generated.partition("_")
        self.assertEqual(prefix, "sup")
        self.assertEqual(len(body), 16)
        int(body, 16)  # body is valid hex

    def test_successive_ids_sort_increasing(self):
        first = generate_id("sup")
        second = generate_id("sup")
        self.assertLess(first, second)

    def test_many_generated_ids_are_unique(self):
        ids = {generate_id("sup") for _ in range(500)}
        self.assertEqual(len(ids), 500)

    def test_missing_prefix_raises(self):
        with self.assertRaises(ValueError):
            generate_id("")


if __name__ == "__main__":
    unittest.main()
