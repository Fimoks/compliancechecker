import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.checks.iaf_checks import (
    IAF1Checker, IAF2Checker, IAF3Checker, IAF4Checker,
    IAF5Checker, IAF6Checker
)

class ComplianceEngine:
    def __init__(self, security_level: int = 4):
        self.security_level = security_level
        self.all_checkers = []
        self._register_all_checkers()
    
    def _register_all_checkers(self):
        self.all_checkers.extend([
            IAF1Checker(),
            IAF2Checker(),
            IAF3Checker(),
            IAF4Checker(),
            IAF5Checker(),
            IAF6Checker(),
        ])
    
    def get_active_checkers(self):
        active = []
        for checker in self.all_checkers:
            if hasattr(checker, 'required_levels'):
                if self.security_level in checker.required_levels:
                    active.append(checker)
            else:
                active.append(checker)
        return active
    
    def run_all(self, progress_callback=None):
        checkers = self.get_active_checkers()
        results = []
        total = len(checkers)
        for i, checker in enumerate(checkers):
            if progress_callback:
                progress_callback(i + 1, total)
            try:
                result = checker.check()
                results.append(result)
            except Exception as e:
                results.append({
                    'id': checker.rule_id,
                    'name': checker.name,
                    'status': False,
                    'value': None,
                    'message': f"Ошибка: {str(e)}",
                })
        return results