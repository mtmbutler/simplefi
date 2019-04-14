import datetime

from django.apps import apps
from model_mommy import mommy

from budget.tests.utils import login


DAYS_PER_YEAR = 365


class TestMethods:
    def test_upload_parse_transactions(self):
        pass

    def test_pattern_match_transactions(self):
        pass


class TestManagers:
    def test_thirteen_months_manager(self, client, django_user_model):
        model = 'budget.Transaction'
        today = datetime.date.today()
        two_years_ago = today - datetime.timedelta(days=2 * DAYS_PER_YEAR)
        user = login(client, django_user_model)

        # Make objects
        old_trans = mommy.make(model, date=two_years_ago, user=user)
        new_trans = mommy.make(model, date=today, user=user)
        old_trans.save()
        new_trans.save()

        # Test
        Transaction = apps.get_model(model)
        qs = Transaction.objects.in_last_thirteen_months(user)
        assert new_trans in qs and old_trans not in qs
