import pytest

from app import create_app


@pytest.mark.parametrize('base', ['javascript:alert(1)', 'https://user:pass@example.test', 'https://example.test/path', 'https://example.test?redirect=bad', 'https://example.test#hash'])
def test_invalid_canonical_base(base):
    with pytest.raises(ValueError, match='PUBLIC_BASE_URL'):
        create_app({'TESTING':True, 'PUBLIC_BASE_URL':base})


@pytest.mark.parametrize('key', ['', None, 'change-me-in-production', 'development-only-change-me'])
def test_production_requires_secret(key):
    with pytest.raises(ValueError, match='SECRET_KEY'):
        create_app({'TESTING':True,'PRODUCTION':True,'SECRET_KEY':key,'PUBLIC_BASE_URL':'https://example.test'})


def test_production_requires_https():
    with pytest.raises(ValueError, match='HTTPS'):
        create_app({'TESTING':True,'PRODUCTION':True,'SECRET_KEY':'test-only-random-value','PUBLIC_BASE_URL':'http://example.test'})


def test_valid_production_config():
    app = create_app({'TESTING':True,'PRODUCTION':True,'SECRET_KEY':'test-only-random-value','PUBLIC_BASE_URL':'https://example.test/'})
    assert app.config['PUBLIC_BASE_URL'] == 'https://example.test'
    assert not app.debug
