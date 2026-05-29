import subprocess
import winreg
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_tls_enabled():
    """
    Проверяет, включены ли современные версии TLS (1.2, 1.3) и отключены ли устаревшие (SSL, TLS 1.0).
    """
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\WinHttp"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        tls12_enabled = True  # по умолчанию в новых Windows включено
        # Проверяем отключение SSL 2.0/3.0
        ssl_disabled = True
        try:
            ssl_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\SecureProtocols"
            ssl_val = get_registry_value(ssl_key, "SecureProtocols")
            if ssl_val and (ssl_val & 0x00000008) == 0:  # бит SSL 2.0
                ssl_disabled = False
        except:
            pass
        return tls12_enabled and ssl_disabled
    except:
        return False

def is_network_segmentation_configured():
    """
    Проверяет, настроено ли сегментирование сети (наличие нескольких сетевых интерфейсов, VLAN).
    Упрощённо: проверяем, есть ли активный файрвол.
    """
    try:
        result = subprocess.run(
            ['netsh', 'advfirewall', 'show', 'allprofiles'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'Включен' in result.stdout or 'ON' in result.stdout.upper():
            return True
    except:
        pass
    return False

def is_wireless_encrypted():
    """
    Проверяет, используется ли шифрование беспроводных сетей.
    """
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if 'WPA2' in result.stdout or 'WPA3' in result.stdout:
            return True
        elif 'WEP' in result.stdout:
            return False
    except:
        pass
    return False

def are_config_files_protected():
    """
    Проверяет, защищены ли файлы конфигурации от изменения.
    Упрощённо: проверяем, не является ли пользователь администратором.
    """
    try:
        from core.checks.iaf_checks import is_user_admin
        return not is_user_admin()
    except:
        return False

def is_rdp_secured():
    """
    Проверяет, используется ли RDP с шифрованием (TLS).
    """
    try:
        result = subprocess.run(
            ['reg', 'query', 'HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp', '/v', 'SecurityLayer'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        if '0x2' in result.stdout:  # 2 – TLS
            return True
    except:
        pass
    return False


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# ЗИС.3 — Защита ПДн при передаче по каналам связи (все уровни)
class ZIS3Checker(BaseChecker):
    def __init__(self):
        super().__init__("ЗИС.3", "Защита при передаче по каналам связи", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]

    def check(self) -> dict:
        if is_tls_enabled():
            return self._get_result(True, "TLS включён", "Передача данных защищена.")
        else:
            return self._get_result(False, "TLS не настроен", "Включите TLS 1.2/1.3 и отключите SSL.")

# ЗИС.11 — Обеспечение подлинности сетевых соединений (УЗ-2,1)
class ZIS11Checker(BaseChecker):
    def __init__(self):
        super().__init__("ЗИС.11", "Подлинность сетевых соединений", "high", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if is_rdp_secured():
            return self._get_result(True, "RDP защищён (TLS)", "Подлинность сетевых соединений обеспечена.")
        else:
            return self._get_result(False, "RDP без TLS", "Настройте TLS для RDP-подключений.")

# ЗИС.15 — Защита архивных файлов и настроек (УЗ-2,1)
class ZIS15Checker(BaseChecker):
    def __init__(self):
        super().__init__("ЗИС.15", "Защита архивных файлов и настроек", "medium", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if are_config_files_protected():
            return self._get_result(True, "Файлы настроек защищены", "Пользователь не имеет прав на изменение.")
        else:
            return self._get_result(False, "Файлы настроек не защищены", "Ограничьте права на запись для конфигурационных файлов.")

# ЗИС.17 — Сегментирование информационной системы (УЗ-2,1)
class ZIS17Checker(BaseChecker):
    def __init__(self):
        super().__init__("ЗИС.17", "Сегментирование информационной системы", "high", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if is_network_segmentation_configured():
            return self._get_result(True, "Файрвол активен", "Сегментация сети настроена.")
        else:
            return self._get_result(False, "Файрвол отключён", "Включите межсетевой экран для сегментации трафика.")

# ЗИС.20 — Защита беспроводных соединений (УЗ-3,2,1)
class ZIS20Checker(BaseChecker):
    def __init__(self):
        super().__init__("ЗИС.20", "Защита беспроводных соединений", "medium", is_manual=False)
        self.required_levels = [1, 2, 3]

    def check(self) -> dict:
        if is_wireless_encrypted():
            return self._get_result(True, "Wi-Fi защищён (WPA2/WPA3)", "Беспроводные соединения шифруются.")
        else:
            return self._get_result(False, "Wi-Fi не защищён", "Настройте шифрование WPA2/WPA3 для беспроводной сети.")


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ (опросник)
# ============================================================================

# ЗИС.1 — Разделение функций управления (только УЗ-1)
class ZIS1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ЗИС.1", "Разделение функций управления", "high", is_manual=True)
        self.required_levels = [1]
        self.question = ("Разделены ли функции по управлению информационной системой, управлению системой защиты персональных данных, "
                         "обработке персональных данных и иные функции (разные учётные записи, роли, администраторы)? ")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ЗИС
# ============================================================================

def get_zis_checkers():
    """Возвращает список всех проверок категории ЗИС (Защита ИС и связи)."""
    return [
        ZIS3Checker(),          # авто, все уровни
        ZIS11Checker(),         # авто, УЗ-2,1
        ZIS15Checker(),         # авто, УЗ-2,1
        ZIS17Checker(),         # авто, УЗ-2,1
        ZIS20Checker(),         # авто, УЗ-3,2,1
        ZIS1ManualChecker(),    # ручная, только УЗ-1
    ]