from types import SimpleNamespace

from django.apps import apps


class TestMethods:
    def test_account_balance(self):
        pass

    def test_account_available_credit(self):
        pass

    def test_account_earliest_statement_date(self):
        pass

    def test_account_min_pay(self):
        pass

    def test_account_forecast_next(self):
        pass

    def test_statement_date(self):
        pass
        # TODO: Should be failing, but internal errors instead
        # day, month, year = 14, 1, 2000
        # fake_account = SimpleNamespace(statement_date=day)
        # s = apps.get_model('debt.Statement')(
        #     account=fake_account, year=year, month=month, balance=0.00)
        # date = s.date
        # print(date)
        # assert (date.day, date.month, date.year) == (15, month, year)
