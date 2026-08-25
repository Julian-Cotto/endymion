from app.core.config import Settings, get_settings


def test_settings_host_sets():
    s = Settings(
        allowed_frontend_hosts=" a.com , b.com ",
        allowed_api_hosts="api.example.com",
    )
    assert s.frontend_hosts_set() == {"a.com", "b.com"}
    assert s.api_hosts_set() == {"api.example.com"}


def test_settings_audience_sets():
    s = Settings(
        shell_read_audiences=" aud1 , aud2 ",
        pipeline_write_audiences="pipe1",
    )
    assert s.shell_audiences_set() == {"aud1", "aud2"}
    assert s.pipeline_audiences_set() == {"pipe1"}


def test_get_settings_cached():
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
    get_settings.cache_clear()
