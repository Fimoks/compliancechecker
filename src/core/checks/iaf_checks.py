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


# ============================================================================
# ИАФ.1 — АВТОМАТИЧЕСКАЯ
# ============================================================================

class IAF1Checker(BaseChecker):
    def __init__(self):
        super().__init__("ИАФ.1", "Идентификация и аутентификация работников", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        results = []
        
        # Проверка автовхода
        auto_logon = get_registry_value(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "AutoAdminLogon")
        auto_logon_enabled = (auto_logon == "1")
        results.append(("✅" if not auto_logon_enabled else "❌", "Автовход", not auto_logon_enabled))
        
        # Проверка гостевой учётки
        guest_status = get_registry_value(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList", "Guest")
        guest_disabled = (guest_status == 0 or guest_status is None)
        results.append(("✅" if guest_disabled else "❌", "Гостевая учётка", guest_disabled))
        
        # Проверка прав администратора
        admin_ok = not is_user_admin()
        results.append(("⚠️" if not admin_ok else "✅", "Пользователь не админ", admin_ok))
        
        status = all(r[2] for r in results)
        return self._get_result(status, value="\n".join([f"{s} {t}" for s, t, _ in results]))


# ============================================================================
# ИАФ.2 — РУЧНАЯ (для всех уровней)
# ============================================================================

class IAF2Checker(BaseChecker):
    def __init__(self):
        super().__init__("ИАФ.2", "Идентификация и аутентификация устройств", "high", is_manual=True)
        self.required_levels = [1, 2, 3, 4]  # ← ИСПРАВЛЕНО: теперь для всех уровней
        self.question = "Настроена ли аутентификация устройств в вашей сети (802.1X)?"
    
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ИАФ.3 — АВТОМАТИЧЕСКАЯ
# ============================================================================

class IAF3Checker(BaseChecker):
    def __init__(self):
        super().__init__("ИАФ.3", "Управление идентификаторами", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(['net', 'user'], capture_output=True, text=True, encoding='cp866', errors='replace')
            users = []
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('-') and not line.startswith('Команда'):
                    for word in line.split():
                        if word and word[0].isalnum() and len(word) > 1:
                            users.append(word.lower())
            
            without = []
            for user in users:
                if user.lower() in ['guest', 'defaultaccount', 'wdagutilityaccount']:
                    continue
                check = subprocess.run(['net', 'user', user], capture_output=True, text=True, encoding='cp866', errors='replace')
                if 'Пароль не задан' in check.stdout:
                    without.append(user)
            
            if without:
                return self._get_result(False, without, f"Учётные записи без пароля: {', '.join(without)}")
            return self._get_result(True, "OK", "Все учётные записи защищены паролями")
        except Exception as e:
            return self._get_result(False, str(e), f"Ошибка проверки: {e}")


# ============================================================================
# ИАФ.4 — АВТОМАТИЧЕСКАЯ
# ============================================================================

class IAF4Checker(BaseChecker):
    def __init__(self):
        super().__init__("ИАФ.4", "Управление средствами аутентификации (парольная политика)", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        results = []
        min_len = get_registry_value(r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Network", "MinPasswordLength") or 0
        results.append(("✅" if min_len >= 8 else "❌", f"Минимальная длина пароля: {min_len} (требуется ≥8)", min_len >= 8))
        
        max_age = 999
        try:
            result = subprocess.run(['net', 'accounts'], capture_output=True, text=True, encoding='cp866', errors='replace')
            import re
            for line in result.stdout.split('\n'):
                if 'максимальный срок действия пароля' in line.lower():
                    nums = re.findall(r'\d+', line)
                    if nums:
                        max_age = int(nums[0])
        except:
            pass
        results.append(("✅" if max_age <= 90 else "❌", f"Максимальный срок пароля: {max_age} дней (требуется ≤90)", max_age <= 90))
        
        history = get_registry_value(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", "PasswordHistorySize") or 0
        results.append(("✅" if history >= 5 else "❌", f"История паролей: {history} (требуется ≥5)", history >= 5))
        
        status = all(r[2] for r in results)
        return self._get_result(status, value="\n".join([f"{s} {t}" for s, t, _ in results]))


# ============================================================================
# ИАФ.5 — АВТОМАТИЧЕСКАЯ
# ============================================================================

class IAF5Checker(BaseChecker):
    def __init__(self):
        super().__init__("ИАФ.5", "Защита обратной связи при вводе пароля", "medium", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        dont_display = get_registry_value(r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "dontdisplaylastusername")
        if dont_display == 1:
            return self._get_result(True, "OK", "Имя последнего пользователя не отображается")
        return self._get_result(True, "Предупреждение", "Рекомендуется скрыть имя последнего пользователя")


# ============================================================================
# ИАФ.6 — АВТОМАТИЧЕСКАЯ
# ============================================================================

class IAF6Checker(BaseChecker):
    def __init__(self):
        super().__init__("ИАФ.6", "Идентификация и аутентификация внешних пользователей", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(['net', 'user'], capture_output=True, text=True, encoding='cp866', errors='replace')
            users = []
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('-') and not line.startswith('Команда'):
                    for word in line.split():
                        if word and word[0].isalnum() and len(word) > 1:
                            users.append(word.lower())
            
            system_accounts = ['administrator', 'guest', 'defaultaccount', 'wdagutilityaccount']
            external = [u for u in users if u not in system_accounts]
            
            if len(external) > 5:
                return self._get_result(False, external, f"Обнаружено {len(external)} локальных учётных записей")
            return self._get_result(True, external, f"Локальных учётных записей: {len(external)}")
        except:
            return self._get_result(False, "Ошибка", "Не удалось проверить учётные записи")


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ИАФ
# ============================================================================

def get_iaf_checkers():
    return [
        IAF1Checker(),  # авто
        IAF2Checker(),  # ручная (теперь для всех уровней)
        IAF3Checker(),  # авто
        IAF4Checker(),  # авто
        IAF5Checker(),  # авто
        IAF6Checker(),  # авто
    ]