from abc import ABC, abstractmethod

class BaseChecker(ABC):
    def __init__(self, rule_id: str, name: str, severity: str = "medium"):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity

    @abstractmethod
    def check(self) -> dict:
        pass

    def _get_result(self, status: bool, value: any, message: str = "") -> dict:
        return {
            'id': self.rule_id,
            'name': self.name,
            'status': status,
            'value': value,
            'message': message or ("OK" if status else "Требование не выполнено"),
            'severity': self.severity
        }