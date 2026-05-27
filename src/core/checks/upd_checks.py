# src/core/checks/upd_checks.py

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

def get_local_users():
    try:
        result = subprocess.run(['net', 'user'], capture_output=True, text=True, encoding='cp866', errors='replace')
        users = []
        for line in result.stdout.split('\n'):
            if line.strip() and not line.startswith('-') and not line.startswith('Команда'):
                for word in line.split():
                    if word and word[0].isalnum() and len(word) > 1:
                        users.append(word.lower())
        return list(set(users))
    except:
        return []

def get_admin_users():
    try:
        result = subprocess.run(
            ['net', 'localgroup', 'Администраторы'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        admins = []
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('Алиас'):
                if line not in ['Администраторы', 'comment', 'Члены группы', '---']:
                    admins.append(line.lower())
        return admins
    except:
        return []


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# УПД.1 — АВТОМАТИЧЕСКАЯ
class UPD1Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.1", "Управление учетными записями пользователей", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        users = get_local_users()
        guest_status = get_registry_value(
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList",
            "Guest"
        )
        guest_disabled = (guest_status == 0 or guest_status is None)
        
        if not guest_disabled:
            return self._get_result(False, users, "Гостевая учётная запись активна. Отключите Guest")
        
        return self._get_result(True, users, f"Учётных записей: {len(users)}, гостевая отключена")


# УПД.2 — АВТОМАТИЧЕСКАЯ
class UPD2Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.2", "Методы разграничения доступа", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(['net', 'share'], capture_output=True, text=True, encoding='cp866', errors='replace')
            shares = []
            for line in result.stdout.split('\n'):
                if 'C:' in line or 'D:' in line:
                    shares.append(line.strip())
            
            if shares:
                return self._get_result(True, shares, f"Обнаружены общие папки. Проверьте права доступа вручную")
            else:
                return self._get_result(True, "Нет общих папок", "Общих папок не обнаружено, доступ ограничен")
        except Exception as e:
            return self._get_result(False, str(e), f"Ошибка проверки: {e}")


# УПД.3 — АВТОМАТИЧЕСКАЯ
class UPD3Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.3", "Управление информационными потоками", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(
                ['netsh', 'advfirewall', 'show', 'allprofiles'],
                capture_output=True, text=True, encoding='cp866', errors='replace'
            )
            if 'Включен' in result.stdout or 'ON' in result.stdout.upper():
                return self._get_result(True, "OK", "Межсетевой экран включён")
            else:
                return self._get_result(False, "Выключен", "Межсетевой экран выключен. Рекомендуется включить")
        except:
            return self._get_result(False, "Ошибка", "Не удалось проверить статус файрвола")


# УПД.4 — АВТОМАТИЧЕСКАЯ
class UPD4Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.4", "Разделение полномочий (ролей)", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        admins = get_admin_users()
        system_accounts = ['administrator']
        real_admins = [a for a in admins if a not in system_accounts]
        
        if len(real_admins) > 3:
            return self._get_result(False, real_admins, f"Слишком много администраторов: {len(real_admins)}. Рекомендуется не более 3")
        elif len(real_admins) > 0:
            return self._get_result(True, real_admins, f"Администраторы: {', '.join(real_admins)}. Разделение ролей соблюдается")
        else:
            return self._get_result(True, "OK", "Администраторы отсутствуют")


# УПД.5 — АВТОМАТИЧЕСКАЯ
class UPD5Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.5", "Минимально необходимые права", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                return self._get_result(False, "Текущий пользователь - администратор", 
                    "Пользователь имеет права администратора. Для повседневной работы используйте обычную учётную запись")
            else:
                return self._get_result(True, "OK", "Пользователь не имеет прав администратора")
        except:
            return self._get_result(False, "Ошибка", "Не удалось проверить права пользователя")


# УПД.6 — АВТОМАТИЧЕСКАЯ
class UPD6Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.6", "Ограничение неуспешных попыток входа", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(['net', 'accounts'], capture_output=True, text=True, encoding='cp866', errors='replace')
            threshold = None
            duration = None
            
            for line in result.stdout.split('\n'):
                if 'пороговое значение блокировки' in line.lower() or 'lockout threshold' in line.lower():
                    import re
                    nums = re.findall(r'\d+', line)
                    if nums:
                        threshold = int(nums[0])
                if 'длительность блокировки' in line.lower() or 'lockout duration' in line.lower():
                    import re
                    nums = re.findall(r'\d+', line)
                    if nums:
                        duration = int(nums[0])
            
            if threshold and threshold <= 5 and duration and duration > 0:
                return self._get_result(True, f"Порог: {threshold}, Длительность: {duration} мин", 
                    f"Блокировка после {threshold} попыток на {duration} минут")
            elif threshold:
                return self._get_result(False, f"Порог: {threshold}", 
                    f"Блокировка после {threshold} попыток, но не настроена длительность")
            else:
                return self._get_result(False, "Не настроена", 
                    "Блокировка при неудачных попытках не настроена. Настройте политику блокировки")
        except Exception as e:
            return self._get_result(False, str(e), f"Ошибка проверки: {e}")


# УПД.10 — АВТОМАТИЧЕСКАЯ
class UPD10Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.10", "Блокировка при бездействии", "high", is_manual=False)
        self.required_levels = [2, 3, 4]
    
    def check(self) -> dict:
        try:
            timeout = get_registry_value(
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "InactivityTimeoutSecs"
            )
            
            if timeout and timeout <= 900:
                return self._get_result(True, f"{timeout} сек", f"Блокировка через {timeout//60} минут")
            elif timeout:
                return self._get_result(False, f"{timeout} сек", f"Таймаут {timeout//60} мин (рекомендуется ≤15)")
            else:
                return self._get_result(False, "Не настроена", 
                    "Автоблокировка экрана не настроена. Настройте таймаут блокировки (≤15 минут)")
        except:
            return self._get_result(False, "Ошибка", "Не удалось проверить настройки блокировки")


# УПД.13 — АВТОМАТИЧЕСКАЯ
class UPD13Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.13", "Защищенный удаленный доступ", "high", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(
                ['reg', 'query', 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server', '/v', 'fDenyTSConnections'],
                capture_output=True, text=True, encoding='cp866', errors='replace'
            )
            
            if '0x0' in result.stdout:
                return self._get_result(False, "RDP включён", 
                    "RDP доступен. Убедитесь, что используется VPN и шифрование TLS")
            else:
                return self._get_result(True, "RDP отключён", "Удалённый доступ через RDP отключён")
        except:
            return self._get_result(True, "OK", "Не удалось проверить RDP, но рекомендуется использовать VPN")


# УПД.14 — АВТОМАТИЧЕСКАЯ
class UPD14Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.14", "Контроль беспроводного доступа", "medium", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True, text=True, encoding='cp866', errors='replace'
            )
            
            if 'Нет беспроводного интерфейса' in result.stdout or 'There is no wireless interface' in result.stdout:
                return self._get_result(True, "Wi-Fi отключён", "Беспроводные интерфейсы не обнаружены")
            else:
                if 'WPA2' in result.stdout or 'WPA3' in result.stdout:
                    return self._get_result(True, "Wi-Fi с WPA2/WPA3", "Беспроводная сеть защищена")
                elif 'WEP' in result.stdout:
                    return self._get_result(False, "Wi-Fi с WEP", "Используется устаревший стандарт WEP. Настройте WPA2/WPA3")
                else:
                    return self._get_result(False, "Незащищённый Wi-Fi", "Wi-Fi может быть без защиты. Проверьте настройки")
        except:
            return self._get_result(True, "OK", "Не удалось проверить беспроводные сети")


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ
# ============================================================================

# УПД.7 — РУЧНАЯ
class UPD7Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.7", "Предупреждение пользователя при входе", "medium", is_manual=True)
        self.required_levels = [1, 2, 3, 4]
        self.question = "Отображается ли баннер с предупреждением при входе в систему?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.8 — РУЧНАЯ
class UPD8Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.8", "Оповещение о предыдущем входе", "medium", is_manual=True)
        self.required_levels = [1, 2, 3, 4]
        self.question = "Показывается ли сообщение о последнем успешном входе в систему?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.9 — РУЧНАЯ
class UPD9Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.9", "Ограничение числа параллельных сеансов", "medium", is_manual=True)
        self.required_levels = [1, 2, 3, 4]
        self.question = "Ограничено ли количество одновременных сеансов для каждого пользователя?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.11 — РУЧНАЯ
class UPD11Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.11", "Действия до аутентификации", "low", is_manual=True)
        self.required_levels = [2, 3, 4]
        self.question = "Разрешены ли какие-либо действия до входа в систему (гостевой доступ и т.п.)?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.12 — РУЧНАЯ
class UPD12Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.12", "Поддержка атрибутов безопасности", "low", is_manual=True)
        self.required_levels = [1, 2, 3, 4]
        self.question = "Используются ли мандатные метки безопасности (только для спецОС)?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.15 — РУЧНАЯ
class UPD15Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.15", "Контроль мобильных устройств", "medium", is_manual=True)
        self.required_levels = [1, 2, 3, 4]
        self.question = "Контролируется ли использование мобильных устройств (MDM/MAM)?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.16 — РУЧНАЯ
class UPD16Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.16", "Взаимодействие с внешними системами", "medium", is_manual=True)
        self.required_levels = [1, 2, 3, 4]
        self.question = "Контролируется ли взаимодействие с внешними информационными системами?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# УПД.17 — РУЧНАЯ
class UPD17Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.17", "Доверенная загрузка", "high", is_manual=True)
        self.required_levels = [1, 2, 3, 4]  # ← ИСПРАВЛЕНО
        self.question = "Включена ли доверенная загрузка (Secure Boot, TPM)?"

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ УПД
# ============================================================================

def get_upd_checkers():
    """Возвращает список всех проверок категории УПД"""
    return [
        # Автоматические проверки
        UPD1Checker(),
        UPD2Checker(),
        UPD3Checker(),
        UPD4Checker(),
        UPD5Checker(),
        UPD6Checker(),
        UPD10Checker(),
        UPD13Checker(),
        UPD14Checker(),
        # Ручные проверки
        UPD7Checker(),
        UPD8Checker(),
        UPD9Checker(),
        UPD11Checker(),
        UPD12Checker(),
        UPD15Checker(),
        UPD16Checker(),
        UPD17Checker(),
    ]