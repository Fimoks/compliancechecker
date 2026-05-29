from core.base_checker import BaseChecker

# ============================================================================
# ПОЯСНЕНИЕ
# ============================================================================
# Меры категории ИНЦ (Выявление инцидентов и реагирование на них) являются
# организационными и не могут быть проверены программно на уровне рабочей
# станции. Они вынесены в ручной опросник.
# ============================================================================


# ============================================================================
# РУЧНЫЕ ПРОВЕРКИ (опросник)
# ============================================================================

# ИНЦ.1 — Определение ответственных лиц (УЗ-2,1)
class INC1ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ИНЦ.1", "Определение лиц, ответственных за выявление инцидентов", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Назначены ли ответственные лица за выявление компьютерных инцидентов и реагирование на них? "
                         "Определены ли их обязанности и полномочия?")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ИНЦ.2 — Обнаружение, идентификация и регистрация инцидентов (УЗ-2,1)
class INC2ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ИНЦ.2", "Обнаружение, идентификация и регистрация инцидентов", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Осуществляется ли обнаружение, идентификация и регистрация компьютерных инцидентов? "
                         "Ведётся ли журнал инцидентов?")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ИНЦ.3 — Информирование об инцидентах (УЗ-2,1)
class INC3ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ИНЦ.3", "Информирование об инцидентах", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Обеспечено ли своевременное информирование ответственных лиц о возникновении инцидентов "
                         "со стороны пользователей и администраторов? Определены ли каналы и регламент оповещения?")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ИНЦ.4 — Анализ инцидентов (УЗ-2,1)
class INC4ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ИНЦ.4", "Анализ инцидентов", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Проводится ли анализ компьютерных инцидентов (определение источников, причин возникновения, "
                         "оценка последствий)?")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ИНЦ.5 — Устранение последствий инцидентов (УЗ-2,1)
class INC5ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ИНЦ.5", "Устранение последствий инцидентов", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Принимаются ли меры по устранению последствий компьютерных инцидентов? "
                         "Разработаны ли процедуры восстановления?")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ИНЦ.6 — Предотвращение повторного возникновения инцидентов (УЗ-2,1)
class INC6ManualChecker(BaseChecker):
    def __init__(self):
        super().__init__("ИНЦ.6", "Предотвращение повторного возникновения инцидентов", "high", is_manual=True)
        self.required_levels = [1, 2]
        self.question = ("Планируются ли и принимаются ли меры по предотвращению повторного возникновения инцидентов? "
                         "Вносятся ли изменения в политики и процедуры по результатам анализа инцидентов?")

    def check(self) -> dict:
        return self._get_result(False, None, self.question)


# ============================================================================
# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ВСЕХ ПРОВЕРОК КАТЕГОРИИ ИНЦ
# ============================================================================

def get_inc_checkers():
    """Возвращает список всех проверок категории ИНЦ (Выявление инцидентов и реагирование)."""
    return [
        INC1ManualChecker(),
        INC2ManualChecker(),
        INC3ManualChecker(),
        INC4ManualChecker(),
        INC5ManualChecker(),
        INC6ManualChecker(),
    ]