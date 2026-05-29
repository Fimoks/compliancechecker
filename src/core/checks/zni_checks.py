import winreg
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

def is_usb_write_protected():
    """Проверяет, запрещена ли запись на USB-накопители (политика 'Deny write access')."""
    # Политика: HKLM\SOFTWARE\Policies\Microsoft\Windows\RemovableStorageDevices\{53f5630d-b6bf-11d0-94f2-00a0c91efb8b}
    # Ключ Deny_Write
    key_path = r"SOFTWARE\Policies\Microsoft\Windows\RemovableStorageDevices\{53f5630d-b6bf-11d0-94f2-00a0c91efb8b}"
    deny_write = get_registry_value(key_path, "Deny_Write")
    return deny_write == 1


# ============================================================================
# АВТОМАТИЧЕСКИЕ ПРОВЕРКИ
# ============================================================================

# ЗНИ.2 — Управление доступом к машинным носителям (только УЗ-2 и УЗ-1)
class ZNI2Checker(BaseChecker):
    def __init__(self):
        super().__init__("ЗНИ.2", "Управление доступом к машинным носителям", "high", is_manual=False)
        self.required_levels = [1, 2]   # обязательна для УЗ-1 и УЗ-2
    
    def check(self) -> dict:
        if is_usb_write_protected():
            return self._get_result(
                True,
                "Запись на USB запрещена",
                "Доступ к съёмным носителям ограничен (запрет записи)."
            )
        else:
            return self._get_result(
                False,
                "Запись на USB разрешена",
                "Рекомендуется настроить политику запрета записи на съёмные носители через групповые политики."
            )


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ
# ============================================================================

# ЗНИ.1 — Учёт машинных носителей (УЗ-2 и УЗ-1)
class ZNI1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ЗНИ.1", "Учёт машинных носителей персональных данных", "medium", is_manual=True)
        self.required_levels = [1, 2]
        self.question = "Ведётся ли учёт машинных носителей персональных данных (журнал учёта USB-накопителей, инвентаризация)?"
    
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ЗНИ.8 — Уничтожение или обезличивание данных (УЗ-3, УЗ-2, УЗ-1)
class ZNI8ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ЗНИ.8", "Уничтожение или обезличивание данных на носителях", "high", is_manual=True)
        self.required_levels = [1, 2, 3]
        self.question = (
            "Обеспечивается ли уничтожение (стирание) или обезличивание персональных данных на машинных носителях "
            "при передаче между пользователями, в сторонние организации для ремонта или утилизации?"
        )
    
    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ЗНИ
# ============================================================================

def get_zni_checkers():
    """Возвращает список всех проверок категории ЗНИ в соответствии с приказом ФСТЭК №21."""
    return [
        ZNI2Checker(),          # автоматическая
        ZNI1ManualChecker(),    # ручная
        ZNI8ManualChecker(),    # ручная
    ]