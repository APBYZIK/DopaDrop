import json
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event

from app import create_app
from app.extensions import db
from app.services.tracking_service import TrackingService


@pytest.mark.parametrize('elapsed,index', [(-1,0),(0,0),(29,0),(30,1),(89,1),(90,2),(179,2),(180,3),(299,3),(300,4),(86400,4)])
def test_boundaries(app, client, fixed_clock, items, elapsed, index):
    created = fixed_clock.now
    response = client.post('/api/orders', json={'items':items, 'idempotency_key':str(uuid4())}).json
    token = response['order']['public_token']
    fixed_clock.now += timedelta(seconds=elapsed)
    writes = []
    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(('UPDATE', 'INSERT', 'DELETE')): writes.append(statement)
    with app.app_context():
        engine = db.engine
        event.listen(engine, 'before_cursor_execute', record)
        try:
            first = client.get(f'/api/orders/{token}/tracking')
            second = app.test_client().get(f'/api/orders/{token}/tracking')
            assert first.json == second.json
            state = first.json['tracking']
            assert state['current_stage_index'] == index
            assert state['current_stage_id'] == ['accepted','packing','courier','multiverse','delivered'][index]
            assert state['elapsed_seconds'] == max(0, elapsed)
            assert state['is_final'] is (index == 4)
            expected = None if index == 4 else (created + timedelta(seconds=[0,30,90,180,300][index+1])).isoformat().replace('+00:00','Z')
            assert state['next_stage_at'] == expected
            assert [s['state'] for s in state['stages']] == ['complete'] * index + ['current'] + ['pending'] * (4-index)
            assert first.headers['Cache-Control'] == 'no-store'
            assert writes == []
        finally: event.remove(engine, 'before_cursor_execute', record)


def test_progress_survives_app_restart(app, client, fixed_clock, items):
    response = client.post('/api/orders', json={'items':items, 'idempotency_key':str(uuid4())}).json
    token = response['order']['public_token']
    assert client.get(f'/api/orders/{token}/tracking').json['tracking']['current_stage_id'] == 'accepted'
    fixed_clock.now += timedelta(seconds=180)
    restarted = create_app({'TESTING':True, 'CLOCK':fixed_clock, 'SQLALCHEMY_DATABASE_URI':app.config['SQLALCHEMY_DATABASE_URI']})
    assert restarted.test_client().get(f'/api/orders/{token}/tracking').json['tracking']['current_stage_id'] == 'multiverse'


@pytest.mark.parametrize('fault', ['json','duplicate','offset','first','count','version','text'])
def test_bad_scenario(app, tmp_path, fixed_clock, fault):
    data = json.loads(app.config['TRACKING_SCENARIOS_PATH'].read_text(encoding='utf-8'))
    scenario = data['scenarios'][0]
    if fault == 'duplicate': scenario['stages'][1]['id'] = 'accepted'
    if fault == 'offset': scenario['stages'][1]['start_after_seconds'] = 0
    if fault == 'first': scenario['stages'][0]['start_after_seconds'] = 1
    if fault == 'count': scenario['stages'].pop()
    if fault == 'version': scenario['version'] = True
    if fault == 'text': scenario['stages'][0]['title'] = ''
    path = tmp_path / 'scenarios.json'
    path.write_text('{' if fault == 'json' else json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='Ошибка сценариев'): TrackingService(path, fixed_clock)
