# src/core/engine.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.checks.iaf_checks import get_iaf_checkers
from core.checks.upd_checks import get_upd_checkers


class ComplianceEngine:
    def __init__(self, security_level: int = 4, include_manual: bool = False):
        self.security_level = security_level
        self.include_manual = include_manual
        self.all_checkers = []
        self._register_all_checkers()
    
    def _register_all_checkers(self):
        # Получаем ВСЕ проверки из категорий
        all_checkers = []
        all_checkers.extend(get_iaf_checkers())
        all_checkers.extend(get_upd_checkers())
        
        # Фильтруем по типу (ручные/авто) и по уровню
        for checker in all_checkers:
            # Проверяем по уровню защищённости
            required = getattr(checker, 'required_levels', [1, 2, 3, 4])
            if self.security_level not in required:
                continue
            
            # Проверяем по типу (ручная/авто)
            is_manual = getattr(checker, 'is_manual', False)
            if is_manual and not self.include_manual:
                continue  # Пропускаем ручные, если они не включены
            
            self.all_checkers.append(checker)
    
    def get_active_checkers(self):
        return self.all_checkers
    
    def run_all(self, progress_callback=None):
        checkers = self.get_active_checkers()
        results = []
        total = len(checkers)
        
        for i, checker in enumerate(checkers):
            if progress_callback:
                progress_callback(i + 1, total)
            
            try:
                # Для ручных проверок check() возвращает вопрос
                results.append(checker.check())
            except Exception as e:
                results.append({
                    'id': getattr(checker, 'rule_id', 'UNKNOWN'),
                    'name': getattr(checker, 'name', 'Неизвестная проверка'),
                    'status': False,
                    'value': None,
                    'message': f"Ошибка: {str(e)}",
                    'is_manual': getattr(checker, 'is_manual', False)
                })
        
        return results