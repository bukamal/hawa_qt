# -*- coding: utf-8 -*-
from pathlib import Path


def test_export_service_writes_html_csv_and_xlsx(tmp_path):
    from services.export_service import export_service

    headers = ['الشركة', 'الوارد', 'الصادر']
    rows = [['شركة أ', '1.00 $', '0.00 $'], ['الإجمالي', '1.00 $', '0.00 $']]

    html_path = export_service.write_html(tmp_path / 'report', '<html><body>ok</body></html>')
    csv_path = export_service.write_csv(tmp_path / 'report', headers, rows)
    xlsx_path = export_service.write_xlsx(tmp_path / 'report', 'تقرير', headers, rows, subtitle='اختبار')

    assert html_path.suffix == '.html'
    assert csv_path.suffix == '.csv'
    assert xlsx_path.suffix == '.xlsx'
    assert html_path.read_text(encoding='utf-8').startswith('<html>')
    assert csv_path.read_bytes().startswith(b'\xef\xbb\xbf')
    assert xlsx_path.stat().st_size > 1000


def test_export_service_safe_filename_removes_windows_invalid_chars():
    from services.export_service import export_service

    name = export_service.safe_filename('كشف: شركة/اختبار*؟', 'xlsx')

    assert name.endswith('.xlsx')
    assert ':' not in name
    assert '/' not in name
    assert '*' not in name
