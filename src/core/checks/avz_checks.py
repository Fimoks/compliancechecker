import subprocess
import winreg
import ctypes
from core.base_checker import BaseChecker

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def is_user_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def get_antivirus_status():
    """
    Определяет, установлен ли антивирус и активен ли он.
    Возвращает (installed: bool, active: bool, product_name: str)
    """
    # Способ 1: через WMI (наиболее надёжный)
    try:
        result = subprocess.run(
            ['wmic', '/namespace:\\\\root\\SecurityCenter2', 'path', 'AntivirusProduct', 'get', 'displayName,productState'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        output = result.stdout.strip()
        if 'displayName' in output and 'productState' in output:
            lines = output.split('\n')[1:]
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        product_name = ' '.join(parts[:-1])
                        product_state = parts[-1]
                        try:
                            state = int(product_state, 16)
                            if state != 0:
                                return True, True, product_name
                        except:
                            pass
    except:
        pass

    # Способ 2: через реестр Windows Defender
    try:
        key_path = r"SOFTWARE\Microsoft\Windows Defender\Status"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        realtime_protection, _ = winreg.QueryValueEx(key, "RealTimeProtectionEnabled")
        winreg.CloseKey(key)
        if realtime_protection == 1:
            return True, True, "Windows Defender"
    except:
        pass

    return False, False, None

def get_antivirus_last_update():
    """Возвращает количество дней с момента последнего обновления антивирусных баз (или -1, если не удалось)."""
    # Для Windows Defender можно проверить по реестру
    try:
        key_path = r"SOFTWARE\Microsoft\Windows Defender\Signature Updates"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
        last_updated_str, _ = winreg.QueryValueEx(key, "LastQuickScanTime")
        winreg.CloseKey(key)
        from datetime import datetime
        last_updated = datetime.strptime(last_updated_str[:14], "%Y%m%d%H%M%S")
        delta = datetime.now() - last_updated
        return delta.days
    except:
        pass

    # Альтернативный способ: через PowerShell
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
# АВЗ.1 — РЕАЛИЗАЦИЯ АНТИВИРУСНОЙ ЗАЩИТЫ
# ============================================================================

class AVZ1Checker(BaseChecker):
    def __init__(self):
        super().__init__("АВЗ.1", "Реализация антивирусной защиты", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
        self.detailed_description = r"""
📌 ЧТО ПРОВЕРЯЕТСЯ:
Проверяется, установлено ли антивирусное программное обеспечение и активно ли оно в реальном времени.

✅ ПОЧЕМУ ЭТО ВАЖНО:
- Антивирус — первая линия защиты от вредоносного ПО
- Защищает от вирусов, троянов, шифровальщиков
- Обязательное требование для всех уровней защищённости

📋 НОРМАТИВНОЕ ТРЕБОВАНИЕ (Приказ ФСТЭК №21 п. VI, мера 1):
На всех рабочих станциях и серверах должно быть установлено и активно антивирусное программное обеспечение.

🛠️ КАК ИСПРАВИТЬ:

Если антивирус не установлен:
1. Включите встроенный Windows Defender:
   - Настройки → Конфиденциальность и безопасность → Безопасность Windows
   - Включите 'Защита от вирусов и угроз'

2. Или установите стороннее антивирусное ПО:
   - Kaspersky, Dr.Web, ESET, Avast и др.

Если антивирус установлен, но не активен:
1. Откройте антивирусную программу
2. Включите защиту в реальном времени
3. Проверьте, не истекла ли лицензия

📊 ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Для УЗ-1 и УЗ-2 используйте сертифицированное ФСТЭК антивирусное ПО
- Не отключайте антивирус даже временно
- Настройте регулярное сканирование
"""
    
    def check(self) -> dict:
        installed, active, product_name = get_antivirus_status()
        if installed and active:
            return self._get_result(
                True,
                f"Антивирус {product_name if product_name else 'установлен'} активен",
                "✅ Антивирусная защита реализована."
            )
        elif installed and not active:
            return self._get_result(
                False,
                f"Антивирус {product_name if product_name else ''} установлен, но не активен",
                "⚠️ Антивирус установлен, но не активен. Включите защиту в реальном времени."
            )
        else:
            return self._get_result(
                False,
                "Антивирус не обнаружен",
                "❌ Антивирус не установлен. Включите Windows Defender или установите антивирусное ПО."
            )


# ============================================================================
# АВЗ.2 — ОБНОВЛЕНИЕ АНТИВИРУСНЫХ БАЗ
# ============================================================================

class AVZ2Checker(BaseChecker):
    def __init__(self):
        super().__init__("АВЗ.2", "Обновление антивирусных баз", "critical", is_manual=False)
        self.required_levels = [1, 2, 3, 4]
        self.detailed_description = r"""
📌 ЧТО ПРОВЕРЯЕТСЯ:
Проверяется, как давно обновлялись антивирусные базы (сигнатуры).

✅ ПОЧЕМУ ЭТО ВАЖНО:
- Устаревшие базы не распознают новые угрозы
- Злоумышленники ежедневно создают тысячи новых вирусов
- Обновления должны устанавливаться регулярно

📋 НОРМАТИВНОЕ ТРЕБОВАНИЕ (Приказ ФСТЭК №21 п. VI, мера 2):
Антивирусные базы должны регулярно обновляться (рекомендуется не реже 1 раза в сутки, допустимо не более 7 дней).

🛠️ КАК НАСТРОИТЬ:

Для Windows Defender:
1. Откройте Безопасность Windows
2. Перейдите в 'Защита от вирусов и угроз'
3. Нажмите 'Проверить наличие обновлений'
4. Настройте автоматическое обновление через Центр обновлений Windows

Для сторонних антивирусов:
1. Откройте настройки антивируса
2. Найдите раздел 'Обновления'
3. Включите автоматическое обновление
4. Настройте частоту проверки обновлений (рекомендуется 1 раз в час)

📊 ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:
- Настройте уведомления о неудачных обновлениях
- Периодически проверяйте статус обновлений вручную
- Используйте WSUS для централизованного управления обновлениями
"""
    
    def check(self) -> dict:
        days_since_update = get_antivirus_last_update()
        if days_since_update == -1:
            return self._get_result(
                False,
                "Не удалось определить дату обновления",
                "⚠️ Не удалось проверить актуальность антивирусных баз. Проверьте настройки вручную."
            )
        elif days_since_update <= 7:
            return self._get_result(
                True,
                f"Последнее обновление было {days_since_update} дн. назад",
                f"✅ Антивирусные базы обновлены (актуальность: {days_since_update} дней)."
            )
        else:
            return self._get_result(
                False,
                f"Последнее обновление было {days_since_update} дн. назад",
                f"❌ Антивирусные базы устарели ({days_since_update} дней). Выполните обновление через антивирусную программу."
            )


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ АВЗ
# ============================================================================

def get_avz_checkers():
    """Возвращает список проверок категории АВЗ (Антивирусная защита)."""
    return [
        AVZ1Checker(),
        AVZ2Checker(),
    ]