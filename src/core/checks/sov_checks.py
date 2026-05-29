import subprocess
import winreg
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_ids_ips_installed():
    """
    Проверяет наличие установленных систем обнаружения вторжений.
    Возвращает True, если обнаружен хотя бы один известный продукт.
    """
    # Список известных IDS/IPS (названия служб или продуктов)
    known_products = [
        "Kaspersky Endpoint Security",
        "Symantec Endpoint Protection",
        "McAfee Endpoint Security",
        "Trend Micro OfficeScan",
        "ESET Endpoint Security",
        "Cisco AMP",
        "Microsoft Defender ATP",
        "Snort",
        "Suricata",
        "OSSEC",
        "Wazuh"
    ]
    try:
        # Проверяем через список установленного ПО (WMI)
        result = subprocess.run(
            ['wmic', 'product', 'get', 'name'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        installed = result.stdout.lower()
        for product in known_products:
            if product.lower() in installed:
                return True
    except:
        pass

    # Проверяем через службы Windows
    try:
        result = subprocess.run(
            ['sc', 'query', 'type=', 'service'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        services = result.stdout.lower()
        # Ищем характерные имена служб для IDS/IPS
        keywords = ['kav', 'kes', 'symantec', 'mcafee', 'trend', 'eset', 'cisco', 'mdatp', 'snort', 'suricata', 'ossec', 'wazuh']
        for kw in keywords:
            if kw in services:
                return True
    except:
        pass

    return False

def get_ids_ips_last_update():
    """
    Попытка получить дату последнего обновления сигнатур.
    Для Windows Defender ATP можно получить через PowerShell.
    Возвращает количество дней с момента последнего обновления или -1.
    """
    try:
        # Для Microsoft Defender ATP (если установлен)
        result = subprocess.run(
            ['powershell', '-Command', '(Get-MpComputerStatus).AntivirusSignatureAge'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
    except:
        pass
    # Для других продуктов можно добавить аналогичные проверки
    return -1


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# СОВ.1 — Обнаружение вторжений (только УЗ-1 и УЗ-2)
class SOV1Checker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.1", "Обнаружение вторжений", "high", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        if is_ids_ips_installed():
            return self._get_result(
                True,
                "Обнаружена установленная система обнаружения вторжений",
                "Система обнаружения вторжений активна."
            )
        else:
            return self._get_result(
                False,
                "Не обнаружена IDS/IPS",
                "Рекомендуется установить систему обнаружения вторжений (например, Kaspersky Endpoint Security, Symantec Endpoint Protection или настроить Snort/Suricata)."
            )


# СОВ.2 — Обновление базы решающих правил (только УЗ-1 и УЗ-2)
class SOV2Checker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.2", "Обновление базы решающих правил", "high", is_manual=False)
        self.required_levels = [1, 2]

    def check(self) -> dict:
        days = get_ids_ips_last_update()
        if days == -1:
            # Не удалось определить автоматически – переводим в ручную
            # Делаем проверку ручной, так как автоматика не сработала
            return self._get_result(
                False,
                "Не удалось определить дату обновления",
                "Проверьте вручную, обновляются ли сигнатуры вашей системы обнаружения вторжений."
            )
        elif days <= 7:
            return self._get_result(
                True,
                f"Последнее обновление правил {days} дн. назад",
                "Базы решающих правил обновлены."
            )
        else:
            return self._get_result(
                False,
                f"Последнее обновление правил {days} дн. назад (рекомендуется не более 7)",
                "Обновите базы решающих правил системы обнаружения вторжений."
            )


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ (на случай, если автоматика не сработала – опционально)
# ============================================================================

class SOV1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.1", "Обнаружение вторжений (ручная проверка)", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = "Используется ли в организации система обнаружения вторжений (IDS/IPS)? Установлено ли соответствующее программное обеспечение?"
    def check(self) -> dict:
        return self._get_result(False, None, self.question)

class SOV2ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.2", "Обновление базы решающих правил (ручная проверка)", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = "Регулярно ли обновляются базы решающих правил системы обнаружения вторжений (сигнатуры)?"
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ СОВ
# ============================================================================

def get_sov_checkers():
    """Возвращает список проверок категории СОВ (Обнаружение вторжений)."""
    return [
        SOV1Checker(),
        SOV2Checker(),
        # Если хотите использовать ручные проверки вместо автоматических, закомментируйте авто и раскомментируйте ручные
        # SOV1ManualChecker(),
        # SOV2ManualChecker(),
    ]