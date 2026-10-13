import pytest
from backend.services.cloud import CloudService

@pytest.fixture(autouse=True)
def keep_unit_tests_off_aws(monkeypatch):
    import backend.main as main
    original=main.load_config
    def demo_config():
        c,z,m=original();c['cloud_mode']='LOCAL_DEMO';return c,z,m
    monkeypatch.setattr(main,'load_config',demo_config)
    monkeypatch.setattr(CloudService,'check_credit_budget',lambda self:None)
