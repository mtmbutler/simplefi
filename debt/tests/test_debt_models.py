from datetime import date
from typing import TYPE_CHECKING

from django.apps import apps
from model_mommy import mommy

from debt.tests.utils import login

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client


class TestMethods:
    def test_account_balance(self, client: "Client", django_user_model: "User"):
        # Balance should be the balance of the latest statement, or the
        # credit limit if there are no statements.

        # Setup
        user = login(client, django_user_model)
        CreditLine = apps.get_model("debt.CreditLine")
        Statement = apps.get_model("debt.Statement")
        assert CreditLine.objects.count() == 0
        assert Statement.objects.count() == 0

        # Create the object and validate balance w/ no statements
        cl = 100
        obj = mommy.make(CreditLine, user=user, credit_line=cl)
        assert obj.balance == cl

        # Create a statement and validate balance again
        bal = 200
        __ = mommy.make(Statement, account=obj, balance=bal)
        assert obj.balance == bal

    def test_account_available_credit(
        self, client: "Client", django_user_model: "User"
    ):
        # Available credit should be credit line less balance.

        # Setup
        user = login(client, django_user_model)
        CreditLine = apps.get_model("debt.CreditLine")
        Statement = apps.get_model("debt.Statement")
        assert CreditLine.objects.count() == 0
        assert Statement.objects.count() == 0

        # Create the objects
        cl = 1000
        bal = 200
        obj = mommy.make(CreditLine, user=user, credit_line=cl)
        __ = mommy.make(Statement, account=obj, balance=bal)

        assert obj.available_credit == cl - bal

    def test_account_earliest_statement_date(
        self, client: "Client", django_user_model: "User"
    ):
        # The date of the earliest statement.

        # Setup
        user = login(client, django_user_model)
        CreditLine = apps.get_model("debt.CreditLine")
        Statement = apps.get_model("debt.Statement")
        assert CreditLine.objects.count() == 0
        assert Statement.objects.count() == 0

        # Create the objects
        year = 2018
        month = 11
        later_month = 12
        day = 10
        obj = mommy.make(CreditLine, user=user, statement_date=day)
        __ = mommy.make(Statement, account=obj, year=year, month=month)

        # Make a later statement to make sure we correctly identify the
        # earliest one
        __ = mommy.make(Statement, account=obj, year=year, month=later_month)

        assert obj.earliest_statement_date == date(year, month, day)

    def test_account_min_pay(self, client: "Client", django_user_model: "User"):
        # Minimum pay for a credit line is usually on a % basis, with a
        # certain floor amount (so, e.g., if you have a $10 balance,
        # usually your minimum pay will be $10 instead of some % of it,
        # since the balance is so low)

        # Setup
        user = login(client, django_user_model)
        CreditLine = apps.get_model("debt.CreditLine")
        assert CreditLine.objects.count() == 0
        obj = mommy.make(CreditLine, user=user, min_pay_dlr=30, min_pay_pct=10)

        # Scenario 1: the balance is high enough for the % to apply
        assert obj.min_pay(500) == 50

        # Scenario 2: the balance is too low for the % to apply
        assert obj.min_pay(100) == 30

        # Scenario 3: the balance is lower than the dollar floor
        assert obj.min_pay(15) == 15

    def test_account_forecast_next(self, client: "Client", django_user_model: "User"):
        # This should return the predicted next month's balance, if only
        # the minimum payment is applied.

        # Setup
        user = login(client, django_user_model)
        CreditLine = apps.get_model("debt.CreditLine")
        assert CreditLine.objects.count() == 0

        # Set attributes
        rate = 24  # 2% per month
        bal = 100
        min_pay = 30
        expected = 72  # 100 + 2% - 30
        obj = mommy.make(CreditLine, user=user, min_pay_dlr=min_pay, interest_rate=rate)

        # Calculate
        assert obj.forecast_next(bal) == expected

    def test_statement_date(self, client: "Client", django_user_model: "User"):
        # This should use the parent credit line's day field.

        # Setup
        user = login(client, django_user_model)
        CreditLine = apps.get_model("debt.CreditLine")
        Statement = apps.get_model("debt.Statement")
        assert CreditLine.objects.count() == 0
        assert Statement.objects.count() == 0

        # Set attributes
        year = 2018
        month = 11
        day = 10
        cl = mommy.make(CreditLine, user=user, statement_date=day)
        stmnt = mommy.make(Statement, account=cl, year=year, month=month)

        assert stmnt.date == date(year, month, day)

    def test_calc_balance_stmnt_exists(
        self, client: "Client", django_user_model: "User"
    ):
        user = login(client, django_user_model)
        acc = mommy.make("debt.CreditLine", user=user)
        mommy.make(
            "debt.Statement", user=user, account=acc, month=11, year=2018, balance=400
        )
        assert acc.calc_balance(11, 2018, 400) == (400, None)

    def test_calc_balance_later_stmnts(
        self, client: "Client", django_user_model: "User"
    ):
        user = login(client, django_user_model)
        acc = mommy.make("debt.CreditLine", user=user)
        mommy.make(
            "debt.Statement", user=user, account=acc, month=11, year=2018, balance=400
        )
        assert acc.calc_balance(10, 2018, 400) == (400, None)

    def test_calc_balance_forecast(self, client: "Client", django_user_model: "User"):
        user = login(client, django_user_model)
        acc = mommy.make("debt.CreditLine", user=user, min_pay_dlr=30, interest_rate=12)
        mommy.make(
            "debt.Statement", user=user, account=acc, month=11, year=2018, balance=400
        )
        expected = 374  # ($400 + 1% monthly interest) - $30
        assert acc.calc_balance(12, 2018, 400) == (expected, 30)
