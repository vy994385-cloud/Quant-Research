from datetime import date

from src.data.security import Security


def test_active_security():
    security = Security(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        exchange="NSE",
        isin="INE002A01018",
        security_type="EQUITY",
        sector="Energy",
        industry="Oil & Gas",
    )

    assert security.is_active


def test_inactive_security():
    security = Security(
        symbol="OLDSTOCK",
        company_name="Historical Company",
        exchange="NSE",
        isin="INE000000000",
        security_type="EQUITY",
        active_from=date(2000, 1, 1),
        active_to=date(2020, 12, 31),
    )

    assert not security.is_active
