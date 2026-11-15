from datetime import datetime, timezone

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def fixed_clock():
    class Clock:
        now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)

        def __call__(self):
            return self.now
    return Clock()


@pytest.fixture
def app(tmp_path, fixed_clock):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{(tmp_path / "test.db").as_posix()}',
                      'CLOCK': fixed_clock, 'PUBLIC_BASE_URL': 'https://example.test'})
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def items():
    return [{'product_id': 'invisible-socks', 'quantity': 2}, {'product_id': 'tomorrow-planner', 'quantity': 1}]
