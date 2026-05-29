import subprocess
import winreg
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_backup_configured():
    """
    Проверяет, настроено ли резервное копирование.
    Проверяем службы резервного копирования Windows (Windows Backup, Volume Shadow Copy).
    """
    try:
        # Проверяем, запущена ли служба Volume Shadow Copy
        result = subprocess.run(
            ['sc', 'query', 'VSS'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'RUNNING' in result.stdout:
            return True
        # Проверяем настройки Windows Backup через реестр
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsBackup"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, "LastBackupTime")
            return True
        except:
            return False
    except:
        return False

def is_hardware_monitoring_configured():
    """
    Проверяет, настроен ли контроль безотказного функционирования ТС.
    Упрощённо: проверяем, включён ли мониторинг событий системы.
    """
    try:
        # Проверяем, включён ли аудит системных событий
        result = subprocess.run(
            ['auditpol', '/get', '/category:"System"'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'Success' in result.stdout or 'Failure' in result.stdout:
            return True
    except:
        pass
    return False


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# ОДТ.3 — Контроль безотказного функционирования ТС (только УЗ-1)
class ODT3Checker(BaseChecker):
    def __init__(self):
        super().__init__("ОДТ.3", "Контроль безотказного функционирования технических средств", "high", is_manual=False)
        self.required_levels = [1]

    def check(self) -> dict:
        if is_hardware_monitoring_configured():
            return self._get_result(True, "Мониторинг ТС настроен", "Контроль функционирования активен.")
        else:
            return self._get_result(False, "Мониторинг ТС не настроен", "Рекомендуется настроить мониторинг оборудования.")

# ОДТ.4 — Периодическое резервное копирование (УЗ-2 и УЗ-1)
class ODT4Checker(BaseChecker):
    def __init__(self):
        super().__init__("ОДТ.4", "Периодическое резервное копирование", "critical", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if is_backup_configured():
            return self._get_result(True, "Резервное копирование настроено", "Бэкапы создаются.")
        else:
            return self._get_result(False, "Резервное копирование не настроено", "Настройте резервное копирование персональных данных.")


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ
# ============================================================================

# ОДТ.1 — Использование отказоустойчивых ТС (ручная)
class ODT1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ОДТ.1", "Использование отказоустойчивых технических средств", "high", is_manual=True)
        self.required_levels = []   # не обязательна
        self.question = ("Используются ли отказоустойчивые технические средства (резервные блоки питания, RAID-массивы, "
                         "кластеризация) для обеспечения доступности персональных данных?")
    def check(self) -> dict:
        return self._get_result(False, None, self.question)

# ОДТ.2 — Резервирование ТС, ПО, каналов (ручная)
class ODT2ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ОДТ.2", "Резервирование технических средств и каналов", "high", is_manual=True)
        self.required_levels = []   # не обязательна
        self.question = ("Обеспечено ли резервирование технических средств, программного обеспечения, каналов передачи информации?")
    def check(self) -> dict:
        return self._get_result(False, None, self.question)

# ОДТ.5 — Восстановление ПДн с резервных носителей (ручная)
class ODT5ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ОДТ.5", "Восстановление ПДн с резервных носителей", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Обеспечена ли возможность восстановления персональных данных с резервных копий в течение "
                         "установленного временного интервала? Проводились ли тесты восстановления?")
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ОДТ
# ============================================================================

def get_odt_checkers():
    """Возвращает список всех проверок категории ОДТ (Обеспечение доступности)."""
    return [
        ODT3Checker(),          # авто, только УЗ-1
        ODT4Checker(),          # авто, УЗ-1,2
        ODT5ManualChecker(),    # ручная, УЗ-1,2
        # ODT1ManualChecker(),  # не обязательна
        # ODT2ManualChecker(),  # не обязательна
    ]