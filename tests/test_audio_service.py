# -*- coding: utf-8 -*-
from pathlib import Path


def _reset_database_singleton():
    from app_config import get_db_path
    import database.connection as dc
    dc.LOCAL_DB_PATH = get_db_path()
    dc.DB_PATH = dc.LOCAL_DB_PATH
    try:
        import database.migrations as mig
        mig.DB_PATH = dc.DB_PATH
    except Exception:
        pass
    if getattr(dc.DatabaseConnection, '_local_conn', None):
        dc.DatabaseConnection._local_conn.close()
    dc.DatabaseConnection._instance = None
    dc.DatabaseConnection._local_conn = None


def test_audio_manifest_and_wav_assets_exist(project_root: Path):
    sounds = project_root / 'resources' / 'sounds'
    assert (sounds / 'SOUND_MANIFEST.md').exists()
    required = ['success.wav', 'error.wav', 'warning.wav', 'backup_done.wav', 'export_done.wav', 'payment_due.wav']
    for name in required:
        data = (sounds / name).read_bytes()[:12]
        assert data[:4] == b'RIFF'
        assert data[8:12] == b'WAVE'


def test_audio_service_normalizes_and_persists_settings(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()
    from database.migrations import ensure_db
    from database import SettingsRepository
    from services.audio_service import AudioService

    ensure_db()
    service = AudioService(SettingsRepository())
    result = service.save_settings({
        'enabled': True,
        'volume': 150,
        'success_enabled': False,
        'error_enabled': True,
        'warning_enabled': True,
        'notification_enabled': False,
        'system_enabled': True,
        'security_enabled': True,
    })

    assert result['volume'] == 100
    assert result['success_enabled'] is False
    assert service.is_enabled_for('success') is False
    assert service.is_enabled_for('error') is True


def test_settings_service_audio_requires_admin(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()
    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.settings_service import SettingsService

    ensure_db()
    UserSession.login({'id': 2, 'username': 'viewer', 'role': 'viewer'})
    try:
        SettingsService().save_audio_settings({'enabled': False, 'volume': 0})
    except PermissionError:
        pass
    else:
        raise AssertionError('viewer was allowed to change audio settings')

    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})
    saved = SettingsService().save_audio_settings({'enabled': False, 'volume': 10})
    assert saved['enabled'] is False
    assert saved['volume'] == 10
