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

    try:
        result = subprocess.run(
            ['sc', 'query', 'type=', 'service'],
            capture_output=True, text=True, encoding='cp866', errors='replace'
        )
        services = result.stdout.lower()
        keywords = ['kav', 'kes', 'symantec', 'mcafee', 'trend', 'eset', 'cisco', 'mdatp', 'snort', 'suricata', 'ossec', 'wazuh']
        for kw in keywords:
            if kw in services:
                return True
    except:
        pass

    return False

def get_ids_ips_last_update():
    """Возвращает количество дней с момента последнего обновления сигнатур или -1."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', '(Get-MpComputerStatus).AntivirusSignatureAge'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
    except:
        pass
    return -1


# ============================================================================
# СОВ.1 — ОБНАРУЖЕНИЕ ВТОРЖЕНИЙ
# ============================================================================

class SOV1Checker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.1", "Обнаружение вторжений (IDS/IPS)", "high", is_manual=False)
        self.required_levels = [1, 2]
        self.detailed_description = r"""
📌 ЧТО ПРОВЕРЯЕТСЯ:
Проверяется наличие установленной системы обнаружения вторжений (IDS - Intrusion Detection System) и/или предотвращения вторжений (IPS - Intrusion Prevention System).

✅ ПОЧЕМУ ЭТО ВАЖНО:
- IDS/IPS обнаруживает и может блокировать сетевые атаки в реальном времени
- Выявляет сканирование портов, попытки эксплуатации уязвимостей
- Обязательное требование для УЗ-1 и УЗ-2 (высокие уровни защищённости)

📋 НОРМАТИВНОЕ ТРЕБОВАНИЕ (Приказ ФСТЭК №21 п. VII, мера 1):
Должны применяться средства обнаружения вторжений (IDS/IPS) для выявления компьютерных атак.

🛠️ КАКИЕ БЫВАЮТ РЕШЕНИЯ:

Бесплатные / Open Source:
- Snort — классическая IDS/IPS от Cisco (бесплатная)
- Suricata — современная многопоточная IDS/IPS
- OSSEC / Wazuh — хостовая IDS (HIDS)

Коммерческие (сертифицированные ФСТЭК):
- Kaspersky Endpoint Security (с модулем IDS)
- Positive Technologies MaxPatrol
- Bi.Zone (Solar)
- Symantec Endpoint Protection

🛠️ КАК НАСТРОИТЬ (на примере Snort для Windows):
1. Скачайте Snort с официального сайта
2. Установите WinPcap или Npcap
3. Настройте правила обнаружения в файле snort.conf
4. Запустите Snort в режиме IDS/IPS

📊 ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Для УЗ-1 используйте сертифицированное ФСТЭК решение
- Настройте оповещения о критических атаках
- Регулярно анализируйте логи IDS/IPS
- Интегрируйте с SIEM-системой
"""
    
    def check(self) -> dict:
        if is_ids_ips_installed():
            return self._get_result(
                True,
                "Система обнаружения вторжений установлена",
                "✅ Обнаружена установленная система обнаружения вторжений."
            )
        else:
            return self._get_result(
                False,
                "IDS/IPS не обнаружена",
                "❌ Система обнаружения вторжений не обнаружена. Для УЗ-1 и УЗ-2 рекомендуется установить IDS/IPS (Snort, Suricata, Kaspersky Endpoint Security)."
            )


# ============================================================================
# СОВ.2 — ОБНОВЛЕНИЕ БАЗЫ РЕШАЮЩИХ ПРАВИЛ
# ============================================================================

class SOV2Checker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.2", "Обновление базы решающих правил (сигнатур)", "high", is_manual=False)
        self.required_levels = [1, 2]
        self.detailed_description = r"""
📌 ЧТО ПРОВЕРЯЕТСЯ:
Проверяется, как давно обновлялись сигнатуры (правила) системы обнаружения вторжений.

✅ ПОЧЕМУ ЭТО ВАЖНО:
- Новые атаки появляются ежедневно, сигнатуры должны обновляться
- Устаревшие правила не распознают современные угрозы
- Обязательное требование для УЗ-1 и УЗ-2

📋 НОРМАТИВНОЕ ТРЕБОВАНИЕ (Приказ ФСТЭК №21 п. VII, мера 2):
Базы решающих правил систем обнаружения вторжений должны регулярно обновляться (рекомендуется не реже 1 раза в сутки).

🛠️ КАК НАСТРОИТЬ:

Для Snort/Suricata:
1. Получите подписку на обновления правил (Snort Subscriber Rules)
2. Настройте автоматическую загрузку с помощью PulledPork или аналогичного инструмента
3. Настройте cron-задачу для ежедневного обновления

Для коммерческих решений:
1. Откройте консоль управления
2. Включите автоматическое обновление сигнатур
3. Настройте проверку обновлений каждый час

📊 ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Настройте уведомления о неудачных обновлениях
- Ведите журнал обновлений сигнатур
- Тестируйте новые правила на тестовом стенде перед применением
"""
    
    def check(self) -> dict:
        days = get_ids_ips_last_update()
        if days == -1:
            return self._get_result(
                False,
                "Не удалось определить дату обновления",
                "⚠️ Не удалось автоматически определить актуальность сигнатур. Проверьте обновления вручную."
            )
        elif days <= 7:
            return self._get_result(
                True,
                f"Последнее обновление правил: {days} дн. назад",
                f"✅ Базы решающих правил обновлены (актуальность: {days} дней)."
            )
        else:
            return self._get_result(
                False,
                f"Последнее обновление правил: {days} дн. назад",
                f"❌ Базы решающих правил устарели ({days} дней). Выполните обновление через систему управления IDS/IPS."
            )


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ (опционально, на случай если автоматика не сработала)
# ============================================================================

class SOV1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.1", "Обнаружение вторщений (ручная проверка)", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = "Используется ли в организации система обнаружения вторжений (IDS/IPS)? Установлено ли соответствующее программное обеспечение?"
        self.detailed_description = r"""
📌 РУЧНАЯ ПРОВЕРКА:
Если автоматическая проверка не обнаружила IDS/IPS, необходимо подтвердить наличие системы вручную.

🛠️ КАК ПРОВЕРИТЬ:
1. Откройте список установленных программ
2. Найдите в списке IDS/IPS-решения (Kaspersky, Snort, Suricata и др.)
3. Проверьте, запущены ли соответствующие службы
4. Убедитесь, что система активна и получает обновления
"""
    
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


class SOV2ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("СОВ.2", "Обновление базы решающих правил (ручная проверка)", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = "Регулярно ли обновляются базы решающих правил системы обнаружения вторжений (сигнатуры)?"
        self.detailed_description = r"""
📌 РУЧНАЯ ПРОВЕРКА:
Если автоматическая проверка не смогла определить дату обновления, необходимо подтвердить регулярность обновлений вручную.

🛠️ КАК ПРОВЕРИТЬ:
1. Откройте консоль управления IDS/IPS
2. Найдите раздел с информацией об обновлениях
3. Проверьте дату последнего обновления сигнатур
4. Убедитесь, что настроено автоматическое обновление
"""
    
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
        # Ручные проверки можно добавить при необходимости:
        # SOV1ManualChecker(),
        # SOV2ManualChecker(),
    ]