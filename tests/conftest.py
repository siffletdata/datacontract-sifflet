import pytest

import datacontract_sifflet  # noqa: F401  # registers the exporter before tests call export("sifflet")


@pytest.fixture(autouse=True)
def change_test_dir(request, monkeypatch):
    monkeypatch.chdir(request.fspath.dirname)
