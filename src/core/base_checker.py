from abc import ABC, abstractmethod

class BaseChecker(ABC):
    def __init__(self, rule_id: str, name: str, severity: str = "medium", is_manual: bool = False):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.is_manual = is_manual
        self.required_levels = [1, 2, 3, 4]
        self.question = None  # для ручных проверок (будет переопределён)

    @abstractmethod
    def check(self) -> dict:
        """Для ручных проверок можно вернуть заглушку с вопросом"""
        pass

    def _get_result(self, status: bool, value: any, message: str = "") -> dict:
        return {
            'id': self.rule_id,
            'name': self.name,
            'status': status,
            'value': value,
            'message': message or ("OK" if status else "Требование не выполнено"),
            'severity': self.severity,
            'is_manual': self.is_manual,
            'question': self.question if self.is_manual else None
        }