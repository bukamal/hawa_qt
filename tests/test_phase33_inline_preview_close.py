from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_app_shell_centrally_wires_inline_closed_signal():
    source = (ROOT / 'ui' / 'shell' / 'app_shell.py').read_text(encoding='utf-8')
    assert "hasattr(widget, 'closed')" in source
    assert 'widget.closed.connect(self.close_inline)' in source


def test_print_preview_close_button_uses_request_close():
    source = (ROOT / 'ui' / 'components' / 'print_preview_panel.py').read_text(encoding='utf-8')
    assert 'self.close_btn.clicked.connect(self.request_close)' in source
    assert 'def request_close(self):' in source
    assert 'self.closed.emit()' in source
