import json
from datetime import timedelta, timezone
from pathlib import Path

from app.models.dto import TrackingStage, TrackingState


class TrackingService:
    def __init__(self, scenarios_path, clock):
        self.clock = clock
        self.scenarios = {}
        try:
            data = json.loads(Path(scenarios_path).read_text(encoding='utf-8'))
            if type(data['schema_version']) is not int or data['schema_version'] != 1:
                raise ValueError('неподдерживаемая версия')
            seen = set()
            for scenario in data['scenarios']:
                sid, version = scenario['id'], scenario['version']
                if not isinstance(sid, str) or not sid or sid in seen or type(version) is not int or version < 1:
                    raise ValueError('неверный ID или версия сценария')
                seen.add(sid)
                stages = tuple(TrackingStage(**s) for s in scenario['stages'])
                if len(stages) < 2 or (sid == 'default-v1' and (len(stages) != 5 or version != 1)):
                    raise ValueError('неверное число этапов или версия default-v1')
                offsets = [s.start_after_seconds for s in stages]
                if any(type(n) is not int for n in offsets) or offsets[0] != 0 or any(a >= b for a, b in zip(offsets, offsets[1:])):
                    raise ValueError('этапы должны начинаться с 0 и строго возрастать')
                if len({s.id for s in stages}) != len(stages) or any(not isinstance(t, str) or not t.strip() for s in stages for t in (s.id, s.title, s.description, s.emoji)):
                    raise ValueError('неверные поля этапов')
                self.scenarios[(sid, version)] = stages
            if ('default-v1', 1) not in self.scenarios:
                raise ValueError('нет default-v1')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValueError(f'Ошибка сценариев трекинга: {exc}') from exc

    def get_state(self, order):
        created = order.created_at.astimezone(timezone.utc)
        elapsed = max(0, int((self.clock().astimezone(timezone.utc) - created).total_seconds()))
        stages = self.scenarios[(order.tracking_scenario_id, order.tracking_version)]
        index = max(i for i, s in enumerate(stages) if s.start_after_seconds <= elapsed)
        final = index == len(stages) - 1
        next_at = None if final else created + timedelta(seconds=stages[index + 1].start_after_seconds)
        return TrackingState(index, stages[index], stages, elapsed, next_at, final)
