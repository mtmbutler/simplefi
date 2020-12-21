import datetime
from typing import TYPE_CHECKING, Type

from model_mommy import mommy

from budget.tests.utils import login
from debt.utils import get_debt_budget

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client

    from budget.models import Budget, TransactionClass


def test_debt_budget_valid(client: "Client", django_user_model: "User"):
    user = login(client, django_user_model)
    tclass = mommy.make(
        "budget.TransactionClass", name="debt"
    )  # type: Type[TransactionClass]
    budget = mommy.make(
        "budget.Budget", class_field=tclass, user=user, value=100
    )  # type: Type[Budget]

    assert get_debt_budget(user).pk == budget.pk


def test_deb_budget_invalid(client: "Client", django_user_model: "User"):
    user = login(client, django_user_model)

    assert get_debt_budget(user) is None
