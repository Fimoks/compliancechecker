import subprocess
import winreg
import ctypes
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_user_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def get_antivirus_status():
    """
    Определяет, установлен ли антивирус и активен ли он.
    Возвращает (installed: bool, active: bool, product_name: str)
    """
    # Способ 1: через WMI (наиболее надёжный)
    try:
        result = subprocess.run(
            ['wmic', '/namespace:\\\\root\\SecurityCenter2', 'path', 'AntivirusProduct', 'get', 'displayName,productState'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        output = result.stdout.strip()
        if 'displayName' in output and 'productState' in output:
            lines = output.split('\n')[1:]  # пропускаем заголовок
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        product_name = ' '.join(parts[:-1])
                        product_state = parts[-1]
                        # productState – шестнадцатеричное число; обычно 16 (0x10) – включён, 0x00 – выключен
                        # Упрощённо: проверяем, что state не 0
                        try:
                            state = int(product_state, 16)
                            if state != 0:
                                return True, True, product_name
                        except:
                            pass
    except:
        pass

    # Способ 2: через реестр (более простой, но менее надёжный)
    try:
        key_path = r"SOFTWARE\Microsoft\Windows Defender\Status"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        realtime_protection, _ = winreg.QueryValueEx(key, "RealTimeProtectionEnabled")
        winreg.CloseKey(key)
        if realtime_protection == 1:
            return True, True, "Windows Defender"
    except:
        pass

    return False, False, None

def get_antivirus_last_update():
    """Возвращает количество дней с момента последнего обновления антивирусных баз (или -1, если не удалось)."""
    # Для Windows Defender можно проверить по реестру
    try:
        key_path = r"SOFTWARE\Microsoft\Windows Defender\Signature Updates"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        last_updated_str, _ = winreg.QueryValueEx(key, "LastQuickScanTime")
        winreg.CloseKey(key)
        # last_updated_str имеет формат "YYYYMMDDHHMMSS.SSS"
        from datetime import datetime, timedelta
        last_updated = datetime.strptime(last_updated_str[:14], "%Y%m%d%H%M%S")
        delta = datetime.now() - last_updated
        return delta.days
    except:
        pass

    # Альтернативный способ: через PowerShell (Get-MpComputerStatus)
    try:
        result = subprocess.run(
            ['powershell', '-Command', '(Get-MpComputerStatus).AntivirusSignatureAge'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
    except:
        pass

    return -1


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# АВЗ.1 — Реализация антивирусной защиты (все уровни)
class AVZ1Checker(BaseChecker):
    def __init__(self):
        super().__init__("АВЗ.1", "Реализация антивирусной защиты", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]

    def check(self) -> dict:
        installed, active, product_name = get_antivirus_status()
        if installed and active:
            return self._get_result(
                True,
                f"Антивирус {product_name if product_name else 'установлен'} активен",
                "Антивирусная защита реализована."
            )
        elif installed and not active:
            return self._get_result(
                False,
                f"Антивирус {product_name if product_name else ''} установлен, но не активен",
                "Активируйте антивирусную защиту."
            )
        else:
            return self._get_result(
                False,
                "Антивирус не обнаружен",
                "Установите антивирусное программное обеспечение (рекомендуется включить Windows Defender или использовать сертифицированное СЗИ)."
            )


# АВЗ.2 — Обновление антивирусных баз (все уровни)
class AVZ2Checker(BaseChecker):
    def __init__(self):
        super().__init__("АВЗ.2", "Обновление антивирусных баз", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]

    def check(self) -> dict:
        days_since_update = get_antivirus_last_update()
        if days_since_update == -1:
            return self._get_result(
                False,
                "Не удалось определить дату обновления",
                "Проверьте настройки антивируса вручную."
            )
        elif days_since_update <= 7:
            return self._get_result(
                True,
                f"Последнее обновление было {days_since_update} дн. назад",
                "Антивирусные базы обновлены."
            )
        else:
            return self._get_result(
                False,
                f"Последнее обновление было {days_since_update} дн. назад (рекомендуется не более 7)",
                "Выполните обновление антивирусных баз."
            )


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ АВЗ
# ============================================================================

def get_avz_checkers():
    """Возвращает список проверок категории АВЗ (Антивирусная защита)."""
    return [
        AVZ1Checker(),
        AVZ2Checker(),
    ]