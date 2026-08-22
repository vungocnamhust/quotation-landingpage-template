import os
import unittest
from unittest.mock import patch

from services.publication_runtime import render_react_pdf_bytes


class _FakeLocator:
    def __init__(self, state: str):
        self.state = state

    def get_attribute(self, name: str) -> str | None:
        if name == "data-map-render-state":
            return self.state
        return None


class _FakePage:
    def __init__(self, map_state: str):
        self.map_state = map_state
        self.calls: list[str] = []
        self.waited_for_terminal_map_state = False

    def goto(self, *_args: object, **_kwargs: object) -> None:
        self.calls.append("goto")

    def wait_for_selector(self, selector: str, **_kwargs: object) -> None:
        self.calls.append(f"selector:{selector}")

    def wait_for_function(self, _expression: str, **_kwargs: object) -> None:
        self.calls.append("map-terminal-state")
        self.waited_for_terminal_map_state = True

    def locator(self, selector: str) -> _FakeLocator:
        self.calls.append(f"locator:{selector}")
        return _FakeLocator(self.map_state)

    def pdf(self, **_kwargs: object) -> bytes:
        if not self.waited_for_terminal_map_state:
            raise AssertionError("PDF was requested before map readiness completed")
        self.calls.append("pdf")
        return b"pdf-bytes"


class _FakeBrowser:
    def __init__(self, page: _FakePage):
        self.page = page
        self.closed = False

    def new_page(self) -> _FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, browser: _FakeBrowser):
        self.browser = browser

    def launch(self) -> _FakeBrowser:
        return self.browser


class _FakePlaywright:
    def __init__(self, browser: _FakeBrowser):
        self.chromium = _FakeChromium(browser)

    def __enter__(self) -> "_FakePlaywright":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class PublicationRuntimeTests(unittest.TestCase):
    def _render_with_map_state(self, map_state: str) -> tuple[bytes | None, _FakePage, _FakeBrowser]:
        page = _FakePage(map_state)
        browser = _FakeBrowser(page)
        with patch("playwright.sync_api.sync_playwright", return_value=_FakePlaywright(browser)), patch.dict(
            os.environ, {"QUOTE_GENERATOR_INTERNAL_URL": "http://quote-generator:8115"}, clear=False
        ):
            try:
                return render_react_pdf_bytes(hostname="ignored", release_id="release-1"), page, browser
            except RuntimeError:
                return None, page, browser

    def test_pdf_waits_for_a_delayed_map_terminal_state_before_printing(self) -> None:
        result, page, browser = self._render_with_map_state("ready")

        self.assertEqual(result, b"pdf-bytes")
        self.assertIn('selector:[data-map-render-state]', page.calls)
        self.assertLess(page.calls.index("map-terminal-state"), page.calls.index("pdf"))
        self.assertTrue(browser.closed)

    def test_pdf_rejects_a_failed_tile_render_instead_of_printing_a_blank_map(self) -> None:
        result, page, browser = self._render_with_map_state("failed")

        self.assertIsNone(result)
        self.assertNotIn("pdf", page.calls)
        self.assertTrue(browser.closed)


if __name__ == "__main__":
    unittest.main()
