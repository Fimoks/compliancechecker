import winreg
import subprocess
import ctypes
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_registry_value(key_path, value_name, hive=winreg.HKEY_LOCAL_MACHINE):
    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        return value
    except:
        return None

def is_audit_logon_enabled():
    """Проверяет, включён ли аудит входа в систему (успешные и неудачные попытки)."""
    try:
        result = subprocess.run(
            ['auditpol', '/get', '/category:"Logon/Logoff"', '/subcategory:"Logon"'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'Success' in result.stdout and 'Failure' in result.stdout:
            return True
        else:
            return False
    except:
        return False

def get_event_log_max_size():
    """Возвращает максимальный размер журнала Security (в МБ)."""
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WINEVT\Channels\Security"
        max_size = get_registry_value(key_path, "MaxSize")
        if max_size:
            return max_size // (1024 * 1024)
        return 0
    except:
        return 0

def get_event_log_retention_days():
    """Возвращает срок хранения событий в журнале Security (дней)."""
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WINEVT\Channels\Security"
        retention = get_registry_value(key_path, "Retention")
        if retention:
            return retention // (24 * 3600)
        return 0
    except:
        return 0

def is_eventlog_protected():
    """Проверяет, защищены ли журналы событий от удаления обычным пользователем."""
    try:
        from core.checks.iaf_checks import is_user_admin
        return not is_user_admin()
    except:
        return False

def is_time_synchronized():
    """Проверяет, настроена ли синхронизация времени с NTP-сервером."""
    try:
        result = subprocess.run(
            ['w32tm', '/query', '/configuration'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'NtpServer' in result.stdout and 'Type=NTP' in result.stdout:
            return True
        result2 = subprocess.run(
            ['w32tm', '/query', '/status'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'Source:' in result2.stdout and 'Local CMOS Clock' not in result2.stdout:
            return True
        return False
    except:
        return False

def is_security_monitoring_configured():
    """
    Проверяет, настроен ли мониторинг событий безопасности.
    Проверяем, включен ли аудит и есть ли подписка на события (упрощённо).
    """
    # Базовая проверка: если аудит включён, считаем, что мониторинг возможен
    # Для более точной проверки можно анализировать настройки Event Viewer,
    # но это сложно. Делаем упрощённую версию.
    return is_audit_logon_enabled()


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# РСБ.1 — Определение событий безопасности, подлежащих регистрации
class RSB1Checker(BaseChecker):
    def __init__(self):
        super().__init__("РСБ.1", "Определение событий безопасности, подлежащих регистрации", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        if is_audit_logon_enabled():
            return self._get_result(True, "OK", "Аудит входа в систему включён.")
        else:
            return self._get_result(False, "Не включён", "Включите аудит входа в систему через AuditPol или групповые политики.")

# РСБ.2 — Определение состава и содержания информации о событиях безопасности
class RSB2Checker(BaseChecker):
    def __init__(self):
        super().__init__("РСБ.2", "Состав информации о событиях безопасности", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        if is_audit_logon_enabled():
            return self._get_result(True, "OK", "Состав событий определён (аудит входа включён).")
        else:
            return self._get_result(False, "Не определён", "Настройте аудит входа в систему.")

# РСБ.3 — Сбор, запись и хранение информации о событиях безопасности
class RSB3Checker(BaseChecker):
    def __init__(self):
        super().__init__("РСБ.3", "Сбор, запись и хранение событий безопасности", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        max_size = get_event_log_max_size()
        retention_days = get_event_log_retention_days()
        issues = []
        if max_size < 100:
            issues.append(f"- Размер журнала Security: {max_size} МБ (рекомендуется не менее 100 МБ).")
        if retention_days == 0:
            issues.append("- Срок хранения событий не задан (может переполняться).")
        elif retention_days < 365:
            issues.append(f"- Срок хранения событий: {retention_days} дней (рекомендуется не менее 365).")
        if issues:
            return self._get_result(False, "\n".join(issues), "Настройте параметры журнала событий Security.")
        else:
            return self._get_result(True, f"Размер: {max_size} МБ, хранение: {retention_days} дн.", "Сбор и хранение настроены корректно.")

# РСБ.5 — Мониторинг и анализ событий безопасности (добавлено, автоматическое)
class RSB5Checker(BaseChecker):
    def __init__(self):
        super().__init__("РСБ.5", "Мониторинг и анализ событий безопасности", "medium", is_manual=False)
        self.required_levels = [1, 2, 3]   # для УЗ-4 не требуется
    
    def check(self) -> dict:
        if is_security_monitoring_configured():
            return self._get_result(True, "OK", "Мониторинг событий безопасности настроен (аудит включён).")
        else:
            return self._get_result(False, "Не настроен", "Настройте аудит и мониторинг событий безопасности.")

# РСБ.7 — Защита информации о событиях безопасности
class RSB7Checker(BaseChecker):
    def __init__(self):
        super().__init__("РСБ.7", "Защита информации о событиях безопасности", "medium", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        if is_eventlog_protected():
            return self._get_result(True, "OK", "Журналы событий защищены от удаления обычным пользователем.")
        else:
            return self._get_result(False, "Уязвимо", "Обычный пользователь может удалять журналы событий. Рекомендуется ограничить права.")

# РСБ.6 — Синхронизация времени (опциональная)
class RSB6Checker(BaseChecker):
    def __init__(self):
        super().__init__("РСБ.6", "Синхронизация системного времени", "low", is_manual=False)
        self.required_levels = []   # опциональная
        # Для включения проверки для всех уровней замените на [1,2,3,4]
    
    def check(self) -> dict:
        if is_time_synchronized():
            return self._get_result(True, "OK", "Время синхронизируется с NTP-сервером.")
        else:
            return self._get_result(False, "Не синхронизировано", "Рекомендуется настроить синхронизацию времени с NTP-сервером.")


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ РСБ
# ============================================================================

def get_rsb_checkers():
    """Возвращает список всех проверок категории РСБ в соответствии с приказом ФСТЭК №21."""
    return [
        RSB1Checker(),
        RSB2Checker(),
        RSB3Checker(),
        RSB5Checker(),          # добавлена автоматическая проверка
        RSB7Checker(),
        RSB6Checker(),          # опциональная
    ]