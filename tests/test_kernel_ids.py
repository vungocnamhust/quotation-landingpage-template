import multiprocessing
import unittest
from concurrent.futures import ProcessPoolExecutor

from core.kernel.ids import generate_id


def _generate_ids_with_frozen_clock(frozen_ns: int, count: int) -> list[str]:
    """Runs in a fresh subprocess (spawn context): re-imports core.kernel.ids from
    scratch, so its counter gets a fresh, independently-random starting offset."""
    from unittest.mock import patch

    from core.kernel.ids import generate_id as _generate_id

    with patch("time.time_ns", return_value=frozen_ns):
        return [_generate_id("sup") for _ in range(count)]


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

    def test_cross_process_ids_with_frozen_clock_do_not_collide(self):
        """Track 1 audit H7: two processes forced onto the exact same millisecond
        used to produce byte-for-byte identical ids (deterministic counter reset to
        0 in every process). With a randomly-seeded per-process counter, they must
        not collide, while each process's own ids stay unique and still sortable."""
        frozen_ns = 1_700_000_000_123_000_000
        count = 200
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=2, mp_context=ctx) as executor:
            futures = [
                executor.submit(_generate_ids_with_frozen_clock, frozen_ns, count) for _ in range(2)
            ]
            ids_a, ids_b = (future.result() for future in futures)

        self.assertEqual(len(set(ids_a)), count)
        self.assertEqual(len(set(ids_b)), count)
        self.assertEqual(set(ids_a) & set(ids_b), set())
        # Still sortable: ids generated later (real clock) exceed anything frozen here.
        self.assertLess(max(ids_a), generate_id("sup"))


if __name__ == "__main__":
    unittest.main()
