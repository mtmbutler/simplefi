import datetime

from .models import Statement


def test_statement_date():
    s = Statement(account=None, year=2000, month=1, balance=0.00)
    assert s.date == datetime.date(year=2000, month=1, day=1)
