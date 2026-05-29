import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.checks.iaf_checks import get_iaf_checkers
from core.checks.upd_checks import get_upd_checkers
from core.checks.ops_checks import get_ops_checkers
from core.checks.zni_checks import get_zni_checkers
from core.checks.rsb_checks import get_rsb_checkers
from core.checks.avz_checks import get_avz_checkers
from core.checks.sov_checks import get_sov_checkers
from core.checks.anz_checks import get_anz_checkers
from core.checks.ocl_checks import get_ocl_checkers
from core.checks.odt_checks import get_odt_checkers
from core.checks.zsv_checks import get_zsv_checkers
from core.checks.zts_checks import get_zts_checkers
from core.checks.zis_checks import get_zis_checkers
from core.checks.inc_checks import get_inc_checkers
from core.checks.ukf_checks import get_ukf_checkers


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
        all_checkers.extend(get_ops_checkers())
        all_checkers.extend(get_zni_checkers())
        all_checkers.extend(get_rsb_checkers())
        all_checkers.extend(get_avz_checkers())
        all_checkers.extend(get_sov_checkers())
        all_checkers.extend(get_anz_checkers())
        all_checkers.extend(get_ocl_checkers())
        all_checkers.extend(get_odt_checkers())
        all_checkers.extend(get_zsv_checkers())
        all_checkers.extend(get_zts_checkers())
        all_checkers.extend(get_zis_checkers())
        all_checkers.extend(get_inc_checkers())
        all_checkers.extend(get_ukf_checkers())
        
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