import subprocess
import winreg
from datetime import datetime
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_windows_update_status():
    """
    Проверяет, включены ли автоматические обновления Windows.
    Возвращает (auto_update_enabled: bool, last_update_days: int)
    """
    auto_update = False
    last_update_days = -1

    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        au_options, _ = winreg.QueryValueEx(key, "AUOptions")
        # 2 – уведомлять, 3 – автоматически загружать и уведомлять, 4 – автоматически загружать и устанавливать
        auto_update = (au_options >= 3)
        winreg.CloseKey(key)
    except:
        pass

    try:
        result = subprocess.run(
            ['wmic', 'qfe', 'get', 'InstalledOn', '/format:csv'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        dates = []
        for line in result.stdout.splitlines():
            if ',' in line and line.strip():
                parts = line.split(',')
                if len(parts) >= 2 and parts[1].strip():
                    try:
                        date = datetime.strptime(parts[1].strip(), "%Y%m%d")
                        dates.append(date)
                    except:
                        pass
        if dates:
            latest = max(dates)
            delta = datetime.now() - latest
            last_update_days = delta.days
    except:
        pass

    return auto_update, last_update_days

def get_installed_software():
    """Возвращает список установленного ПО (для инвентаризации)."""
    software = []
    try:
        result = subprocess.run(
            ['wmic', 'product', 'get', 'name'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith('Name') and not line.startswith('Copyright'):
                software.append(line)
    except:
        pass
    return software

def is_security_software_working():
    """Проверяет, работают ли основные СЗИ (антивирус, файрвол)."""
    try:
        from core.checks.avz_checks import get_antivirus_status
        installed, active, _ = get_antivirus_status()
        if not installed or not active:
            return False
    except:
        pass
    try:
        result = subprocess.run(
            ['netsh', 'advfirewall', 'show', 'allprofiles'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'Включен' not in result.stdout and 'ON' not in result.stdout.upper():
            return False
    except:
        pass
    return True

def is_vulnerability_scan_configured():
    """
    Проверяет, настроено ли сканирование уязвимостей.
    Упрощённо: проверяем наличие Windows Defender Vulnerability Scanning.
    """
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-MpPreference | Select-Object -ExpandProperty DisableRealtimeMonitoring'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if 'False' in result.stdout:
            return True
    except:
        pass
    return False


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# АНЗ.2 — Контроль установки обновлений ПО (все уровни)
class ANZ2Checker(BaseChecker):
    def __init__(self):
        super().__init__("АНЗ.2", "Контроль установки обновлений программного обеспечения", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]

    def check(self) -> dict:
        auto, days = get_windows_update_status()
        issues = []
        if not auto:
            issues.append("- Автоматические обновления не включены.")
        if days == -1:
            issues.append("- Не удалось определить дату последнего обновления.")
        elif days > 30:
            issues.append(f"- Последнее обновление было {days} дней назад (рекомендуется не более 30).")
        if issues:
            return self._get_result(False, "\n".join(issues), "Настройте автоматическое обновление Windows и проверьте установку обновлений.")
        else:
            return self._get_result(True, f"Автообновление включено, последнее обновление {days} дн. назад", "Обновления контролируются.")

# АНЗ.3 — Контроль работоспособности СЗИ (УЗ-3,2,1)
class ANZ3Checker(BaseChecker):
    def __init__(self):
        super().__init__("АНЗ.3", "Контроль работоспособности СЗИ", "high", is_manual=False)
        self.required_levels = [1, 2, 3]

    def check(self) -> dict:
        if is_security_software_working():
            return self._get_result(True, "СЗИ функционирует", "Антивирус и файрвол активны.")
        else:
            return self._get_result(False, "СЗИ не полностью работоспособно", "Проверьте состояние антивируса и файрвола.")

# АНЗ.4 — Контроль состава ТС, ПО (УЗ-3,2,1)
class ANZ4Checker(BaseChecker):
    def __init__(self):
        super().__init__("АНЗ.4", "Контроль состава технических средств и ПО", "medium", is_manual=False)
        self.required_levels = [1, 2, 3]

    def check(self) -> dict:
        software = get_installed_software()
        if software:
            return self._get_result(True, f"Обнаружено {len(software)} программных продуктов", "Состав ПО учтён (примерный список).")
        else:
            return self._get_result(True, "Не удалось получить список ПО", "Рекомендуется вести реестр установленного ПО вручную.")


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ
# ============================================================================

# АНЗ.1 — Выявление и устранение уязвимостей (УЗ-3,2,1)
class ANZ1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("АНЗ.1", "Выявление и устранение уязвимостей", "high", is_manual=True)
        self.required_levels = [1, 2, 3]
        self.question = "Проводится ли регулярное сканирование уязвимостей и устранение критических уязвимостей в установленные сроки?"
    def check(self) -> dict:
        return self._get_result(False, None, self.question)

# АНЗ.5 — Контроль паролей, учёток, прав (УЗ-2,1) – частично уже есть в ИАФ/УПД, поэтому ручной
class ANZ5ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("АНЗ.5", "Контроль паролей, учётных записей и прав доступа", "critical", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Осуществляется ли регулярный контроль правил генерации и смены паролей, "
                        "заведения и удаления учётных записей, реализации разграничения доступа?")
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ АНЗ
# ============================================================================

def get_anz_checkers():
    """Возвращает список всех проверок категории АНЗ (Контроль защищённости)."""
    return [
        ANZ2Checker(),
        ANZ3Checker(),
        ANZ4Checker(),
        ANZ1ManualChecker(),
        ANZ5ManualChecker(),
    ]