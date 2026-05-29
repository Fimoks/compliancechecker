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

def is_user_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def is_applocker_enabled():
    """Проверяет, включён ли AppLocker (служба Application Identity и наличие правил)."""
    try:
        # Проверяем, запущена ли служба AppIDSvc
        result = subprocess.run(
            ['sc', 'query', 'AppIDSvc'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'RUNNING' not in result.stdout:
            return False
        # Проверяем наличие правил AppLocker в реестре
        key_path = r"SOFTWARE\Policies\Microsoft\Windows\SrpV2\Exe"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        # Если ключ существует и содержит хотя бы одно правило, считаем AppLocker включённым
        # Для простоты проверяем только существование ключа и наличие подразделов
        try:
            winreg.EnumKey(key, 0)
            return True
        except OSError:
            return False
    except:
        return False


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# ОПС.2 — Управление установкой компонентов ПО (только УЗ-2 и УЗ-1)
class OPS2Checker(BaseChecker):
    def __init__(self):
        super().__init__("ОПС.2", "Управление установкой программного обеспечения", "high", is_manual=False)
        # По таблице: обязательна для УЗ-2 и УЗ-1
        self.required_levels = [1, 2]
    
    def check(self) -> dict:
        # Проверяем, не является ли текущий пользователь администратором
        # Если пользователь администратор, он может устанавливать ПО — это нарушение
        if is_user_admin():
            return self._get_result(
                False,
                "Текущий пользователь имеет права администратора",
                "Пользователь может устанавливать ПО. Рекомендуется использовать учётную запись без прав администратора для повседневной работы."
            )
        else:
            return self._get_result(
                True,
                "Ограниченные права",
                "Пользователь не имеет прав администратора, установка ПО невозможна."
            )


# ОПС.3 — Установка только разрешённого ПО (только УЗ-1)
class OPS3Checker(BaseChecker):
    def __init__(self):
        super().__init__("ОПС.3", "Установка только разрешённого программного обеспечения", "critical", is_manual=False)
        # По таблице: обязательна только для УЗ-1
        self.required_levels = [1]
    
    def check(self) -> dict:
        # Проверяем, включён ли AppLocker или аналогичное средство ограничения ПО
        if is_applocker_enabled():
            return self._get_result(
                True,
                "AppLocker включён",
                "Программное обеспечение ограничено разрешённым списком."
            )
        else:
            return self._get_result(
                False,
                "AppLocker не настроен или отключён",
                "Рекомендуется настроить AppLocker или иное средство контроля запуска приложений."
            )


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ (для мер, не подлежащих автоматизации)
# ============================================================================

# ОПС.1 — Управление запуском ПО (не автоматизируется, но можно добавить как ручную)
class OPS1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ОПС.1", "Управление запуском компонентов ПО", "medium", is_manual=True)
        self.required_levels = []   # ни для одного уровня не обязательна, но можно оставить для справки
        self.question = ("Осуществляется ли контроль за запуском программного обеспечения "
                         "(например, ведение журнала запуска приложений)?")
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ОПС.4 — Управление временными файлами (не автоматизируется, ручная)
class OPS4ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ОПС.4", "Управление временными файлами", "low", is_manual=True)
        self.required_levels = []   # не обязательна
        self.question = ("Настроены ли политики управления временными файлами (запрет, перенаправление, автоматическая очистка)?")
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ОПС
# ============================================================================

def get_ops_checkers():
    """Возвращает список всех проверок категории ОПС в соответствии с приказом ФСТЭК №21."""
    return [
        OPS2Checker(),          # авто, УЗ-2 и УЗ-1
        OPS3Checker(),          # авто, только УЗ-1
        # Ручные (не обязательны, можно не включать в основной опросник)
        # OPS1ManualChecker(),
        # OPS4ManualChecker(),
    ]