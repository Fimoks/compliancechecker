# src/core/engine.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.checks.iaf_checks import get_iaf_checkers
from core.checks.upd_checks import get_upd_checkers


class ComplianceEngine:
    def __init__(self, security_level: int = 4):
        self.security_level = security_level
        self.all_checkers = []
        self._register_all_checkers()
    
    def _register_all_checkers(self):
        """Добавляем все категории проверок"""
        self.all_checkers.extend(get_iaf_checkers())   # ИАФ
        self.all_checkers.extend(get_upd_checkers())   # УПД
        
        # Для новых категорий — просто добавить сюда:
        # self.all_checkers.extend(get_xxx_checkers())
    
    def get_active_checkers(self):
        """Возвращает проверки, обязательные для текущего уровня УЗ"""
        active = []
        for checker in self.all_checkers:
            required = getattr(checker, 'required_levels', [1, 2, 3, 4])
            if self.security_level in required:
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
                    'id': getattr(checker, 'rule_id', 'UNKNOWN'),
                    'name': getattr(checker, 'name', 'Неизвестная проверка'),
                    'status': False,
                    'value': None,
                    'message': f"Ошибка: {str(e)}",
                })
        
        return results


# Для тестирования
if __name__ == "__main__":
    engine = ComplianceEngine(security_level=4)
    checkers = engine.get_active_checkers()
    print(f"Активных проверок для УЗ-4: {len(checkers)}")
    for c in checkers:
        print(f"  {c.rule_id}: {c.name}")