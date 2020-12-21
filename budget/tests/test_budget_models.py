import datetime
import math
import os
from typing import TYPE_CHECKING, Type

import pandas as pd
from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from model_mommy import mommy

from budget.tests.utils import login

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.test import Client

    from budget import models


DAYS_PER_YEAR = 365


class TestBackups:
    def test_backup_create_no_transactions(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0
        bak = mommy.make(bak_model, csv=None)
        assert bak_model.objects.count() == 1

        # Create the backup
        bak.create_backup()

        try:
            with open(bak.csv.path) as f:
                lines = list(f.readlines())

            # No transactions, so should just be header
            assert len(lines) == 1
            assert lines[0] == "Account,Class,Category,Date,Amount,Description\n"

        finally:
            # Cleanup
            os.remove(bak.csv.path)

    def test_backup_two_transactions(self, client: "Client", django_user_model: "User"):
        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        tr_model = apps.get_model(
            "budget.Transaction"
        )  # type: Type[models.Transaction]
        for model in (bak_model, tr_model):
            assert model.objects.count() == 0

        # Make transactions and create a backup
        mommy.make(tr_model, user=user, amount=5.54)
        mommy.make(tr_model, user=user, amount=3.99)
        bak = mommy.make(bak_model, user=user, csv=None)
        bak.create_backup()

        try:
            df = pd.read_csv(bak.csv.path)

            # Should have 6 cols and 2 rows, and check amount sum
            assert df.shape == (2, 6)
            assert df.columns.tolist() == [
                "Account",
                "Class",
                "Category",
                "Date",
                "Amount",
                "Description",
            ]
            assert math.isclose(df["Amount"].sum(), 9.53, rel_tol=1e-9, abs_tol=0.0)

        finally:
            # Cleanup
            os.remove(bak.csv.path)

    def test_backup_restore_clean(self, client: "Client", django_user_model: "User"):
        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        tr_model = apps.get_model(
            "budget.Transaction"
        )  # type: Type[models.Transaction]
        acc_model = apps.get_model("budget.Account")  # type: Type[models.Account]
        ul_model = apps.get_model("budget.Upload")  # type: Type[models.Upload]
        for model in (bak_model, tr_model, acc_model, ul_model):
            assert model.objects.count() == 0

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                Account=["Checking", "Checking"],
                Class=["", ""],
                Category=["", ""],
                Date=["2018-11-10", "2018-11-11"],
                Amount=[5.54, 3.99],
                Description=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        try:
            # Create the backup object and restore
            bak = mommy.make(bak_model, user=user, csv=temp_path)
            with transaction.atomic():
                msg = bak.restore()

            # There should now be two transactions attached to one
            # upload and one account, and msg should be a success code
            assert tr_model.objects.count() == 2
            assert (
                float(tr_model.objects.aggregate(Sum("amount"))["amount__sum"]) == 9.53
            )
            assert acc_model.objects.count() == 1
            assert acc_model.objects.first().name == "Checking"
            assert acc_model.objects.first().num_transactions == 2
            assert ul_model.objects.count() == 1
            assert ul_model.objects.first().account.name == "Checking"
            assert ul_model.objects.first().num_transactions == 2
            assert msg == "success"

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_restore_wrong_header(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        tr_model = apps.get_model(
            "budget.Transaction"
        )  # type: Type[models.Transaction]
        acc_model = apps.get_model("budget.Account")  # type: Type[models.Account]
        ul_model = apps.get_model("budget.Upload")  # type: Type[models.Upload]
        for model in (bak_model, tr_model, acc_model, ul_model):
            assert model.objects.count() == 0

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                Account=["Checking", "Checking"],
                Class=["", ""],
                Category=["", ""],
                Date=["2018-11-10", "2018-11-11"],
                Bad_amt_col_name=[5.54, 3.99],
                Description=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        try:
            # Create the backup object and restore
            bak = mommy.make(bak_model, user=user, csv=temp_path)
            with transaction.atomic():
                msg = bak.restore()

            # It should have failed because of the incorrect header
            assert tr_model.objects.count() == 0
            assert acc_model.objects.count() == 0
            assert ul_model.objects.count() == 0
            assert "columns expected but not found" in msg

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_restore_bad_date_format(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        tr_model = apps.get_model(
            "budget.Transaction"
        )  # type: Type[models.Transaction]
        acc_model = apps.get_model("budget.Account")  # type: Type[models.Account]
        ul_model = apps.get_model("budget.Upload")  # type: Type[models.Upload]
        for model in (bak_model, tr_model, acc_model, ul_model):
            assert model.objects.count() == 0

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                Account=["Checking", "Checking"],
                Class=["", ""],
                Category=["", ""],
                Date=["2018-11-100", "2018-11-11"],
                Amount=[5.54, 3.99],
                Description=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        try:
            # Create the backup object and restore
            bak = mommy.make(bak_model, user=user, csv=temp_path)
            with transaction.atomic():
                msg = bak.restore()

            # It should have failed because of the incorrect date format
            assert tr_model.objects.count() == 0
            assert acc_model.objects.count() == 0
            assert ul_model.objects.count() == 0
            assert "invalid date format" in msg

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_restore_str_in_value_col(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        tr_model = apps.get_model(
            "budget.Transaction"
        )  # type: Type[models.Transaction]
        acc_model = apps.get_model("budget.Account")  # type: Type[models.Account]
        ul_model = apps.get_model("budget.Upload")  # type: Type[models.Upload]
        for model in (bak_model, tr_model, acc_model, ul_model):
            assert model.objects.count() == 0

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                Account=["Checking", "Checking"],
                Class=["", ""],
                Category=["", ""],
                Date=["2018-11-10", "2018-11-11"],
                Amount=["five dollars", 3.99],
                Description=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        try:
            # Create the backup object and restore
            bak = mommy.make(bak_model, user=user, csv=temp_path)
            with transaction.atomic():
                msg = bak.restore()

            # It should have failed because of the incorrect date format
            assert tr_model.objects.count() == 0
            assert acc_model.objects.count() == 0
            assert ul_model.objects.count() == 0
            assert "Validation error" in msg

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_file_response(self, client: "Client", django_user_model: "User"):
        # Setup
        login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0

        # Make a fake file
        s = "foo bar baz spam ham eggs"
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.txt")
        with open(temp_path, "w") as f:
            f.write(s)

        try:
            bak = mommy.make(bak_model, csv=temp_path)
            assert bak_model.objects.count() == 1
            r = bak.file_response()
            text = "".join(line.decode("UTF-8") for line in r.streaming_content)
            assert text == s

        finally:
            # Cleanup
            os.remove(temp_path)

    def test_backup_empty_file_response(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        login(client, django_user_model)
        bak_model = apps.get_model("budget.CSVBackup")  # type: Type[models.CSVBackup]
        assert bak_model.objects.count() == 0

        bak = mommy.make(bak_model, csv=None)
        assert bak_model.objects.count() == 1
        r = bak.file_response()
        text = "".join(line.decode("UTF-8") for line in r.streaming_content)
        assert text == "No CSV associated with selected backup."


class TestUploads:
    def test_upload_parse_transactions_clean(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model("budget.Account")
        Upload = apps.get_model("budget.Upload")
        acc = mommy.make(
            Account,
            user=user,
            date_col_name="date",
            amt_col_name="amt",
            desc_col_name="desc",
        )

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                date=["2018-11-10", "2018-11-11"],
                amt=[5.54, 3.99],
                desc=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        result = ul.parse_transactions()
        assert result == "success"
        assert ul.num_transactions == 2
        assert acc.num_transactions == 2

        # Cleanup
        os.remove(temp_path)

    def test_upload_parse_transactions_wrong_header(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model("budget.Account")
        Upload = apps.get_model("budget.Upload")
        acc = mommy.make(
            Account,
            user=user,
            date_col_name="date",
            amt_col_name="amt",
            desc_col_name="desc",
        )

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                date=["2018-11-10", "2018-11-11"],
                bad_amt_col_name=[5.54, 3.99],
                desc=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        result = ul.parse_transactions()
        assert "Not all specified columns" in result
        assert acc.num_transactions == 0

        # Cleanup
        os.remove(temp_path)

    def test_upload_parse_transactions_bad_date_format(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model("budget.Account")
        Upload = apps.get_model("budget.Upload")
        acc = mommy.make(
            Account,
            user=user,
            date_col_name="date",
            amt_col_name="amt",
            desc_col_name="desc",
        )

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                date=["2018-11-100", "2018-11-11"],
                amt=[5.54, 3.99],
                desc=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        with transaction.atomic():
            result = ul.parse_transactions()
        assert "invalid date format" in result
        assert acc.num_transactions == 0

        # Cleanup
        os.remove(temp_path)

    def test_upload_parse_transactions_str_in_value_col(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        Account = apps.get_model("budget.Account")
        Upload = apps.get_model("budget.Upload")
        acc = mommy.make(
            Account,
            user=user,
            date_col_name="date",
            amt_col_name="amt",
            desc_col_name="desc",
        )

        # Make a fake csv
        df = pd.DataFrame(
            dict(
                date=["2018-11-10", "2018-11-11"],
                amt=["five dollars", 3.99],
                desc=["Eggs", "Spam"],
            )
        )
        temp_path = os.path.join(settings.MEDIA_ROOT, "temp.csv")
        df.to_csv(temp_path)

        # Create the upload and try to parse the CSV
        ul = mommy.make(Upload, account=acc, user=user, csv=temp_path)
        with transaction.atomic():
            result = ul.parse_transactions()
        assert "Validation error" in result
        assert acc.num_transactions == 0

        # Cleanup
        os.remove(temp_path)


class TestPatterns:
    def test_pattern_match_transactions(
        self, client: "Client", django_user_model: "User"
    ):
        # Setup
        user = login(client, django_user_model)
        Pattern = apps.get_model("budget.Pattern")
        Transaction = apps.get_model("budget.Transaction")
        assert Pattern.objects.count() == 0
        assert Transaction.objects.count() == 0

        # Create the pattern and transactions
        p = mommy.make(Pattern, user=user, pattern=r".*wal[- ]?mart.*")
        shared_kwargs = dict(_model=Transaction, user=user, pattern=None)
        mommy.make(**shared_kwargs, id=1, description="WalMart")  # Yes
        mommy.make(**shared_kwargs, id=2, description="Wal Mart")  # Yes
        mommy.make(**shared_kwargs, id=3, description="WallMart")  # No
        mommy.make(**shared_kwargs, id=4, description="Target")  # No
        mommy.make(**shared_kwargs, id=5, description="Debit - Wal-Mart")  # Yes

        # Validate matches
        p.match_transactions()
        assert [t.id for t in p.transaction_set.all()] == [1, 2, 5]


class TestManagers:
    def test_thirteen_months_manager(self, client: "Client", django_user_model: "User"):
        model = "budget.Transaction"
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
