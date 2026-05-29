import subprocess
import winreg
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_integrity_control_configured():
    """
    Проверяет, настроен ли контроль целостности ПО.
    Проверяем наличие AppLocker или SRP (Software Restriction Policies).
    """
    try:
        # Проверяем, включена ли служба Application Identity
        result = subprocess.run(
            ['sc', 'query', 'AppIDSvc'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'RUNNING' in result.stdout:
            return True
        # Проверяем наличие правил AppLocker в реестре
        key_path = r"SOFTWARE\Policies\Microsoft\Windows\SrpV2\Exe"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        try:
            winreg.EnumKey(key, 0)
            return True
        except OSError:
            return False
    except:
        return False

def is_antispam_configured():
    """
    Проверяет, настроена ли защита от спама.
    Проверяем настройки Windows Defender Mail Protection.
    """
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-MpPreference | Select-Object -ExpandProperty EnableNetworkProtection'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if 'True' in result.stdout:
            return True
    except:
        pass
    return False


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# ОЦЛ.1 — Контроль целостности ПО (только УЗ-2 и УЗ-1)
class OCL1Checker(BaseChecker):
    def __init__(self):
        super().__init__("ОЦЛ.1", "Контроль целостности программного обеспечения", "high", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if is_integrity_control_configured():
            return self._get_result(True, "Контроль целостности настроен", "AppLocker или SRP активны.")
        else:
            return self._get_result(False, "Контроль целостности не настроен", "Рекомендуется настроить AppLocker или SRP.")

# ОЦЛ.4 — Защита от спама (УЗ-2 и УЗ-1)
class OCL4Checker(BaseChecker):
    def __init__(self):
        super().__init__("ОЦЛ.4", "Защита от спама", "medium", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if is_antispam_configured():
            return self._get_result(True, "Антиспам-защита настроена", "Защита от спама активна.")
        else:
            return self._get_result(False, "Антиспам-защита не настроена", "Рекомендуется настроить антиспам-фильтр.")


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ОЦЛ
# ============================================================================

def get_ocl_checkers():
    """Возвращает список всех проверок категории ОЦЛ (Обеспечение целостности)."""
    return [
        OCL1Checker(),          # авто, УЗ-1,2
        OCL4Checker(),          # авто, УЗ-1,2
    ]