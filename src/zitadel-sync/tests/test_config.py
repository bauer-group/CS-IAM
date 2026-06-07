from config import Settings


def _settings(**over):
    base = dict(
        azure_tenant_id="t",
        azure_client_id="c",
        azure_client_secret="s",
        zitadel_domain="id.bauer-group.com",
        zitadel_port=443,
        zitadel_insecure=False,
    )
    base.update(over)
    return Settings(**base)


def test_issuer_omits_default_https_port():
    s = _settings(zitadel_domain="id.bauer-group.com", zitadel_port=443, zitadel_insecure=False)
    assert s.issuer() == "https://id.bauer-group.com"


def test_issuer_includes_dev_port():
    s = _settings(zitadel_domain="zitadel.localhost", zitadel_port=8080, zitadel_insecure=True)
    assert s.issuer() == "http://zitadel.localhost:8080"


def test_issuer_omits_default_http_port():
    s = _settings(zitadel_domain="zitadel.localhost", zitadel_port=80, zitadel_insecure=True)
    assert s.issuer() == "http://zitadel.localhost"


def test_graph_configured_true_when_all_set():
    assert _settings().graph_configured() is True


def test_graph_configured_false_when_missing():
    assert _settings(azure_client_secret="").graph_configured() is False
