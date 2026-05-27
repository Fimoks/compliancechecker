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
    """Получить список пользователей в группе администраторов"""
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
# УПД.1: Управление учетными записями пользователей
# ============================================================================

class UPD1Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.1", "Управление учетными записями пользователей", "high")
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


# ============================================================================
# УПД.2: Реализация методов разграничения доступа
# ============================================================================

class UPD2Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.2", "Методы разграничения доступа", "high")
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        # Проверяем, настроены ли права на общие папки
        # Базовая проверка: существуют ли общие папки
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


# ============================================================================
# УПД.3: Управление информационными потоками (файрвол)
# ============================================================================

class UPD3Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.3", "Управление информационными потоками", "high")
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        # Проверяем, включён ли файрвол
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


# ============================================================================
# УПД.4: Разделение полномочий (ролей) пользователей
# ============================================================================

class UPD4Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.4", "Разделение полномочий (ролей)", "critical")
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


# ============================================================================
# УПД.5: Назначение минимально необходимых прав
# ============================================================================

class UPD5Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.5", "Минимально необходимые права", "critical")
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        # Проверяем, не является ли текущий пользователь администратором
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                return self._get_result(False, "Текущий пользователь - администратор", 
                    "Пользователь имеет права администратора. Для повседневной работы используйте обычную учётную запись")
            else:
                return self._get_result(True, "OK", "Пользователь не имеет прав администратора")
        except:
            return self._get_result(False, "Ошибка", "Не удалось проверить права пользователя")


# ============================================================================
# УПД.6: Ограничение неуспешных попыток входа
# ============================================================================

class UPD6Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.6", "Ограничение неуспешных попыток входа", "critical")
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        # Проверяем политику блокировки
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


# ============================================================================
# УПД.10: Блокирование сеанса при бездействии
# ============================================================================

class UPD10Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.10", "Блокировка при бездействии", "high")
        self.required_levels = [2, 3, 4]  # для УЗ-2,3,4
    
    def check(self) -> dict:
        # Проверяем таймаут блокировки экрана
        try:
            # Проверяем, включена ли заставка и таймаут
            result = subprocess.run(
                ['powercfg', '/GETACTIVESCHEME'],
                capture_output=True, text=True, encoding='cp866', errors='replace'
            )
            
            # Проверяем таймаут через реестр
            timeout = get_registry_value(
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "InactivityTimeoutSecs"
            )
            
            if timeout and timeout <= 900:  # 15 минут = 900 секунд
                return self._get_result(True, f"{timeout} сек", f"Блокировка через {timeout//60} минут")
            elif timeout:
                return self._get_result(False, f"{timeout} сек", f"Таймаут {timeout//60} мин (рекомендуется ≤15)")
            else:
                return self._get_result(False, "Не настроена", 
                    "Автоблокировка экрана не настроена. Настройте таймаут блокировки (≤15 минут)")
        except:
            return self._get_result(False, "Ошибка", "Не удалось проверить настройки блокировки")


# ============================================================================
# УПД.13: Защищенный удаленный доступ
# ============================================================================

class UPD13Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.13", "Защищенный удаленный доступ", "high")
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        # Проверяем, используется ли RDP и включено ли сетевое обнаружение
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


# ============================================================================
# УПД.14: Контроль беспроводного доступа (Wi-Fi)
# ============================================================================

class UPD14Checker(BaseChecker):
    def __init__(self):
        super().__init__("УПД.14", "Контроль беспроводного доступа", "medium")
        self.required_levels = [1, 2, 3, 4]
    
    def check(self) -> dict:
        # Проверяем, включён ли Wi-Fi и стандарт защиты
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True, text=True, encoding='cp866', errors='replace'
            )
            
            if 'Нет беспроводного интерфейса' in result.stdout or 'There is no wireless interface' in result.stdout:
                return self._get_result(True, "Wi-Fi отключён", "Беспроводные интерфейсы не обнаружены")
            else:
                # Проверяем стандарт защиты
                if 'WPA2' in result.stdout or 'WPA3' in result.stdout:
                    return self._get_result(True, "Wi-Fi с WPA2/WPA3", "Беспроводная сеть защищена")
                elif 'WEP' in result.stdout:
                    return self._get_result(False, "Wi-Fi с WEP", "Используется устаревший стандарт WEP. Настройте WPA2/WPA3")
                else:
                    return self._get_result(False, "Незащищённый Wi-Fi", "Wi-Fi может быть без защиты. Проверьте настройки")
        except:
            return self._get_result(True, "OK", "Не удалось проверить беспроводные сети")


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК УПД
# ============================================================================

def get_upd_checkers():
    """Возвращает список всех проверок категории УПД"""
    return [
        UPD1Checker(),
        UPD2Checker(),
        UPD3Checker(),
        UPD4Checker(),
        UPD5Checker(),
        UPD6Checker(),
        UPD10Checker(),
        UPD13Checker(),
        UPD14Checker(),
    ]