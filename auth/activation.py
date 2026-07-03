import os
import json
import hashlib
import base64
import platform
import getpass
import threading
import time
import datetime
import requests
from typing import Tuple, Optional, Callable

SERVER_URL = 'https://license.manhal-almasriiii199119.workers.dev/activate'

# Runtime license files must live in the writable app config directory, not in
# the installation/source directory. This prevents repeated activation on
# Windows builds installed under Program Files and keeps PyInstaller one-file
# runs from writing inside the temporary extraction folder.
try:
    from app_config import get_config_dir, get_install_dir
except Exception:  # pragma: no cover - fallback for very early/import-only cases
    get_config_dir = None
    get_install_dir = None


def _license_path(filename: str) -> str:
    if get_config_dir is not None:
        return str(get_config_dir() / filename)
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)


def _legacy_license_path(filename: str) -> str:
    if get_install_dir is not None:
        return str(get_install_dir() / filename)
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)


LICENSE_FILE = _license_path('license.dat')
NETWORK_LICENSE_FILE = _license_path('network_license.dat')
LEGACY_LICENSE_FILE = _legacy_license_path('license.dat')
LEGACY_NETWORK_LICENSE_FILE = _legacy_license_path('network_license.dat')


def _read_text_first_existing(*paths: str) -> tuple[Optional[str], Optional[str]]:
    for path in paths:
        try:
            if path and os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read().strip(), path
        except Exception:
            continue
    return None, None


def _write_license(path: str, encrypted: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(encrypted)


def _migrate_legacy_license(source_path: Optional[str], target_path: str, encrypted: str) -> None:
    if not source_path or os.path.abspath(source_path) == os.path.abspath(target_path):
        return
    try:
        _write_license(target_path, encrypted)
    except Exception:
        # Migration must not invalidate an otherwise readable license.
        pass

def get_device_id() -> str:
    try:
        username = getpass.getuser()
    except:
        username = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
    info = platform.node() + platform.processor() + username + platform.system() + platform.machine()
    return hashlib.sha256(info.encode()).hexdigest()

def _derive_key(device_id: str, salt: bytes = b'hawaa_salt_2025') -> bytes:
    return hashlib.pbkdf2_hmac('sha256', device_id.encode(), salt, 100000, dklen=32)

def _xor_encrypt_decrypt(data: bytes, key: bytes) -> bytes:
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])

def _encrypt_license(data: dict, device_id: str) -> str:
    key = _derive_key(device_id)
    plaintext = json.dumps(data).encode()
    encrypted = _xor_encrypt_decrypt(plaintext, key)
    return base64.b64encode(encrypted).decode()

def _decrypt_license(encrypted: str, device_id: str) -> Optional[dict]:
    try:
        key = _derive_key(device_id)
        enc_bytes = base64.b64decode(encrypted)
        plaintext = _xor_encrypt_decrypt(enc_bytes, key)
        return json.loads(plaintext.decode())
    except:
        return None


_NO_EXPIRY_VALUES = {
    '', 'none', 'null', 'nil', 'false', '0',
    'never', 'lifetime', 'permanent', 'perpetual', 'unlimited', 'no_expiry', 'no-expiry',
    'no expiration', 'does not expire', 'غير محدود', 'مدى الحياة', 'دائم', 'لا ينتهي',
}


def _parse_expiration(expiration):
    """Return (kind, datetime).

    kind is one of:
    - ``missing``: server did not send an expiration; treated as no expiry.
    - ``never``: explicit lifetime/unlimited license; treated as no expiry.
    - ``date``: parsed UTC-naive datetime.
    - ``invalid``: non-empty value that could not be parsed.
    """
    if expiration is None:
        return 'missing', None

    if isinstance(expiration, (int, float)):
        try:
            value = float(expiration)
            if value <= 0:
                return 'never', None
            # Support both Unix seconds and milliseconds.
            if value > 100_000_000_000:
                value = value / 1000
            return 'date', datetime.datetime.utcfromtimestamp(value)
        except Exception:
            return 'invalid', None

    value = str(expiration).strip()
    normalized = value.lower().strip()
    if normalized in _NO_EXPIRY_VALUES:
        return 'never', None

    # Numeric strings from license services are common.
    try:
        if normalized.replace('.', '', 1).isdigit():
            num = float(normalized)
            if num <= 0:
                return 'never', None
            if num > 100_000_000_000:
                num = num / 1000
            return 'date', datetime.datetime.utcfromtimestamp(num)
    except Exception:
        pass

    candidates = [
        value.replace('Z', '+00:00'),
        value.replace('/', '-'),
        value.replace('.', '-'),
    ]
    formats = [
        '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y', '%d.%m.%Y',
        '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
    ]
    for candidate in candidates:
        try:
            if len(candidate) == 10 and candidate[4] == '-':
                return 'date', datetime.datetime.fromisoformat(candidate).replace(hour=23, minute=59, second=59)
            parsed = datetime.datetime.fromisoformat(candidate)
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            return 'date', parsed
        except Exception:
            pass
        for fmt in formats:
            try:
                parsed = datetime.datetime.strptime(candidate, fmt)
                if fmt in {'%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y', '%d.%m.%Y'}:
                    parsed = parsed.replace(hour=23, minute=59, second=59)
                return 'date', parsed
            except Exception:
                continue
    return 'invalid', None


def _expiration_error(data: dict) -> Optional[str]:
    expiration = data.get('expiration') if data else None
    kind, parsed = _parse_expiration(expiration)
    if kind == 'invalid':
        return f'تاريخ انتهاء الترخيص غير مفهوم: {expiration}'
    if kind == 'date' and parsed and datetime.datetime.utcnow() > parsed:
        return f'انتهى الترخيص بتاريخ {expiration}'
    return None

def activate(license_key: str) -> Tuple[bool, str]:
    device_id = get_device_id()
    try:
        resp = requests.post(SERVER_URL, json={'licenseCode': license_key, 'fingerprint': device_id}, timeout=15)
        if resp.status_code != 200:
            return False, resp.text or "فشل التفعيل"
        result = resp.json()
        data = {
            'key': license_key,
            'device': device_id,
            'expiration': result.get('expirationDate'),
            'activated_at': __import__('datetime').datetime.now().isoformat()
        }
        _write_license(LICENSE_FILE, _encrypt_license(data, device_id))
        return True, ""
    except Exception as e:
        return False, str(e)

def check_activation() -> Tuple[bool, str]:
    encrypted, source_path = _read_text_first_existing(LICENSE_FILE, LEGACY_LICENSE_FILE)
    if not encrypted:
        return False, "لم يتم التفعيل"
    try:
        device_id = get_device_id()
        data = _decrypt_license(encrypted, device_id)
        if not data or data.get('device') != device_id:
            return False, "ترخيص غير صالح"
        expiration_error = _expiration_error(data)
        if expiration_error:
            return False, expiration_error
        _migrate_legacy_license(source_path, LICENSE_FILE, encrypted)
        return True, ""
    except Exception as e:
        return False, str(e)

def activate_network(license_key: str) -> Tuple[bool, str]:
    device_id = get_device_id()
    try:
        resp = requests.post(SERVER_URL, json={'licenseCode': license_key, 'fingerprint': device_id, 'feature': 'network'}, timeout=15)
        if resp.status_code != 200:
            return False, resp.text or "فشل تفعيل الشبكة"
        result = resp.json()
        data = {
            'key': license_key,
            'device': device_id,
            'expiration': result.get('expirationDate'),
            'activated_at': __import__('datetime').datetime.now().isoformat()
        }
        _write_license(NETWORK_LICENSE_FILE, _encrypt_license(data, device_id))
        return True, ""
    except Exception as e:
        return False, str(e)

def check_network_activation() -> Tuple[bool, str]:
    encrypted, source_path = _read_text_first_existing(NETWORK_LICENSE_FILE, LEGACY_NETWORK_LICENSE_FILE)
    if not encrypted:
        return False, "ميزة الشبكة غير مفعلة"
    try:
        device_id = get_device_id()
        data = _decrypt_license(encrypted, device_id)
        if not data or data.get('device') != device_id:
            return False, "ترخيص الشبكة غير صالح"
        expiration_error = _expiration_error(data)
        if expiration_error:
            return False, expiration_error
        _migrate_legacy_license(source_path, NETWORK_LICENSE_FILE, encrypted)
        return True, ""
    except Exception as e:
        return False, str(e)

_license_checker_thread = None
_license_checker_stop = False
_on_invalid = None

def start_license_checker(interval_hours: int = 24, on_invalid: Callable = None):
    global _license_checker_thread, _license_checker_stop, _on_invalid
    _license_checker_stop = False
    _on_invalid = on_invalid
    def loop():
        while not _license_checker_stop:
            time.sleep(interval_hours * 3600)
            valid, _ = check_activation()
            if not valid and _on_invalid:
                _on_invalid()
    _license_checker_thread = threading.Thread(target=loop, daemon=True)
    _license_checker_thread.start()

def stop_license_checker():
    global _license_checker_stop
    _license_checker_stop = True

def get_license_file_paths() -> dict:
    """Return writable and legacy license paths for diagnostics/UI."""
    return {
        'program': LICENSE_FILE,
        'network': NETWORK_LICENSE_FILE,
        'legacy_program': LEGACY_LICENSE_FILE,
        'legacy_network': LEGACY_NETWORK_LICENSE_FILE,
    }


def describe_license_state(network: bool = False) -> dict:
    """Return a UI-friendly license status without raising exceptions."""
    path = NETWORK_LICENSE_FILE if network else LICENSE_FILE
    legacy = LEGACY_NETWORK_LICENSE_FILE if network else LEGACY_LICENSE_FILE
    encrypted, source_path = _read_text_first_existing(path, legacy)
    label = 'network' if network else 'program'
    if not encrypted:
        return {
            'kind': label,
            'valid': False,
            'message': 'لم يتم العثور على ملف ترخيص محفوظ',
            'source_path': '',
            'target_path': path,
            'expiration': '',
        }
    try:
        device_id = get_device_id()
        data = _decrypt_license(encrypted, device_id)
        if not data:
            return {
                'kind': label,
                'valid': False,
                'message': 'ملف الترخيص موجود لكنه غير قابل للقراءة على هذا الجهاز',
                'source_path': source_path or '',
                'target_path': path,
                'expiration': '',
            }
        if data.get('device') != device_id:
            return {
                'kind': label,
                'valid': False,
                'message': 'الترخيص مربوط بجهاز مختلف',
                'source_path': source_path or '',
                'target_path': path,
                'expiration': data.get('expiration', ''),
            }
        error = _expiration_error(data)
        if error:
            return {
                'kind': label,
                'valid': False,
                'message': error,
                'source_path': source_path or '',
                'target_path': path,
                'expiration': data.get('expiration', ''),
            }
        return {
            'kind': label,
            'valid': True,
            'message': 'الترخيص صالح',
            'source_path': source_path or '',
            'target_path': path,
            'expiration': data.get('expiration', '') or 'لا ينتهي',
            'activated_at': data.get('activated_at', ''),
        }
    except Exception as exc:
        return {
            'kind': label,
            'valid': False,
            'message': str(exc),
            'source_path': source_path or '',
            'target_path': path,
            'expiration': '',
        }
