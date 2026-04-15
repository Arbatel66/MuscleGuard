from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from models.User import User
from services.sync_service import HeartRateSyncService, UserHeartRateState
from sqlalchemy.ext.asyncio import AsyncSession
from services.sets_service import SetsService

# todo:算法需要改进
# 1.考虑重量的情况下
# 2.记录1pm的情况下
# 3.再考虑1分钟心率恢复速度


@dataclass
class HeartRateMetrics:
    peak_bpm: int = 0
    last_hr: int = 0
    rec_score: int = 0
    hist_score: int = 0


class FatigueAnalyzer:
    def __init__(self, hr_service: UserHeartRateState, user: Optional[User] = None):
        self.hr_service = hr_service
        self.user = user
        self.metrics = self._initialize_metrics()

    def _initialize_metrics(self) -> HeartRateMetrics:
        """从 SyncService 中提取并清洗原始数据"""
        samples = self.hr_service.current_sample
        if not samples:
            return HeartRateMetrics()

        valid_hrs = [s.hr for s in samples if s.hr > 0]
        if not valid_hrs:
            return HeartRateMetrics()

        peak = max(valid_hrs)
        last_hr = self.hr_service.last_value

        return HeartRateMetrics(
            peak_bpm=peak,
            last_hr=last_hr,
        )

    def run_full_analysis(self, current_set, history_sets) -> int:
        """
        确定性流程的总开关：点击"完成"后自动跑这里
        score 语义：越高越疲劳（0=完全恢复，100=极度疲劳）
        """
        # 1. 心率恢复分（10/40/70）：恢复越差分越高
        self.metrics.rec_score = self._compute_recovery_60s_score()

        # 2. 历史对比分（0-30）：比历史心率效率高则分越高
        self.metrics.hist_score = self.compute_history_exercise_peak_score(current_set, history_sets)

        score = self.metrics.rec_score + self.metrics.hist_score

        return score

    def _compute_recovery_60s_score(self) -> int:
        """
        基于一分钟心率恢复率(HRR%)计算疲劳分
        score 越高 = 恢复越差 = 越疲劳

        恢复率 >= 18%: score=3 -> 100-90=10  （恢复优秀，低疲劳）
        恢复率 >= 12%: score=2 -> 100-60=40  （恢复良好，中疲劳）
        恢复率 <  12%: score=1 -> 100-30=70  （恢复差，  高疲劳）
        """
        if not self.metrics.peak_bpm or self.metrics.peak_bpm == 0:
            return 0
        hrr = self.metrics.peak_bpm - self.metrics.last_hr
        recovery_rate = hrr / self.metrics.peak_bpm
        thresholds = (0.12, 0.18)
        score = 1 + sum(recovery_rate >= t for t in thresholds)
        return 100 - score * 30

    @staticmethod
    def compute_history_exercise_peak_score(current_set, history_sets) -> int:
        """
        对比历史同动作数据，评估当前心率表现
        返回 0-30 疲劳附加分（越高越疲劳）
        当前 HR效率 比历史平均高出 >= 30% 时满分30
        """
        if not history_sets or not current_set:
            return 0

        def hr_efficiency(weight, reps, peak_hr):
            """每单位相对强度消耗的心率，越高说明同等强度下心率越高（越疲劳）"""
            if reps <= 0 or weight <= 0:
                return None
            one_rm = weight * (1 + reps / 30)
            pct_1rm = (weight / one_rm) * 100
            return peak_hr / pct_1rm if pct_1rm > 0 else None

        history_efficiencies = [
            e for h in history_sets
            if (e := hr_efficiency(h.weight, h.reps, h.peak_hr)) is not None
        ]
        if not history_efficiencies:
            return 0

        avg_history_efficiency = sum(history_efficiencies) / len(history_efficiencies)

        cur_efficiency = hr_efficiency(
            current_set.weight, current_set.reps, current_set.peak_hr
        )
        if cur_efficiency is None:
            return 0

        delta = (cur_efficiency - avg_history_efficiency) / avg_history_efficiency
        extra_score = int(min(max(delta / 0.30, 0), 1) * 30)
        return extra_score

    # def idea_score_critic(hrm:HeartRateMetrics, user: Optional[User] = None):
    #     if user and user.age:
    #         idea_peak = int(208 - user.age * 0.7)
    #         thresholds = (0.5*idea_peak, 0.7*idea_peak)
    #         score = 3 - sum(hrm.peak_bpm >= t for t in thresholds)

    def generate_fatigue_context(self) -> Dict[str, Any]:
        """打包返回心率相关的信息"""
        hrr = self.metrics.peak_bpm - self.metrics.last_hr
        recovery_rate = hrr / self.metrics.peak_bpm if self.metrics.peak_bpm > 0 else 0
        recovery_quality = "优秀" if recovery_rate >= 0.18 else "良好" if recovery_rate >= 0.12 else "一般"

        return {
            "physiological_metrics": {
                "peak_bpm": self.metrics.peak_bpm,
                "last_hr": self.metrics.last_hr,
                "recovery_score": self.metrics.rec_score,
                "history_related_score": self.metrics.hist_score,
                "recovery_rate": f"{recovery_rate:.1%}",
                "recovery_quality": recovery_quality,
                "fatigue_score": self.metrics.rec_score + self.metrics.hist_score,  # 越高越疲劳，最高100
            },
        }

    @staticmethod
    async def analysis_performance(session: AsyncSession, exercise_id: int, limit: int = None):
        """根据exercise_id获取该用户该动作的所有信息（供 LLM Tool 调用）"""
        all_recent_sets = await SetsService.get_sets_by_exercise_id(session, exercise_id)
        current_set = all_recent_sets[0] if all_recent_sets else None
        previous_sets = all_recent_sets[1:]

        all_history_sets = await SetsService.get_history_set_by_exercise_id(session, exercise_id, limit)

        return {
            "current_performance": {
                "weight_kg": current_set.weight if current_set else None,
                "reps": current_set.reps if current_set else None,
                "heart_rate_peak": current_set.peak_hr if current_set else None,
            },
            "recent_sets_summary": [
                {"w": s.weight, "r": s.reps, "hr": s.peak_hr, "time": s.created_at}
                for s in previous_sets
            ],
            "history_sets_summary": [
                {"w": h.weight, "r": h.reps, "hr": h.peak_hr, "time": h.created_at}
                for h in all_history_sets
            ],
        }
