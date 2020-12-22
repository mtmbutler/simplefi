import datetime
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple, Union

import pandas as pd
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, RedirectView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterMixin, FilterView
from django_tables2 import Column, Table
from django_tables2.views import SingleTableMixin, SingleTableView

from budget import forms, models, tables
from budget.utils import first_day_month_after, oys_qs, thirteen_months_ago

if TYPE_CHECKING:
    from django.db.models.query import QuerySet
    from django.forms import Form
    from django.http import FileResponse

    from budget.models import Budget


class Index(LoginRequiredMixin, SingleTableView):
    template_name = "budget/index.html"
    table_class = tables.SummaryTable

    def get_queryset(self) -> List[Dict[str, Union[str, int]]]:
        qs = oys_qs(user=self.request.user)
        return qs

    def get_table_kwargs(self) -> Dict[str, List[Tuple[str, "Column"]]]:
        fmt = "%b_%y"
        orig = thirteen_months_ago()
        first = datetime.date(year=orig.year, month=orig.month, day=1)
        now = timezone.now()
        last = datetime.date(year=now.year, month=now.month, day=1)

        # Add each month to the header
        cols = []
        cur = first
        while cur <= last:
            cols.append(cur.strftime(fmt))
            cur = first_day_month_after(cur)

        extra_cols = [(c, Column(attrs={"td": dict(align="right")})) for c in cols]
        return dict(extra_columns=extra_cols)


class AuthQuerySetMixin:
    """A mixin for generic display views for user data.

    Restricts the queryset to user-associated data only.
    """

    model = None
    request = None

    def get_queryset(self) -> "QuerySet":
        return self.model.objects.filter(user=self.request.user)


class AuthCreateFormMixin:
    """A mixin for generic create views for user data.

    Automatically assigns the logged-in user to the 'user' field of the
    model.
    """

    request = None

    def form_valid(self, form: "Form") -> bool:
        form.instance.user = self.request.user
        return super().form_valid(form)


class AuthForeignKeyMixin:
    """A mixin for generic edit views to protect other users' data.

    Restricts the queryset for all foreign key fields to user-
    associated data only.
    """

    model = None
    request = None

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if "form" in context and hasattr(context["form"], "fields"):
            fk_fields = [
                f
                for f in self.model._meta.get_fields()
                if isinstance(f, ForeignKey) and f.name in context["form"].fields
            ]
            for f in fk_fields:
                try:
                    qs = f.related_model.objects.filter(user=self.request.user)
                except FieldError:  # Not a user field
                    qs = f.related_model.objects.all()
                context["form"].fields[f.name].queryset = qs
        return context


class TransactionTableMixin(SingleTableMixin, FilterMixin):
    """A mixin for including a table of transactions in a view."""

    table_class = tables.TransactionTable
    table_pagination = dict(per_page=15)

    @abstractmethod
    def exclude_cols(self, *_, **__) -> Tuple[str, ...]:
        """Columns to exclude from the table."""

    @abstractmethod
    def get_filter_kwargs(self, *_, **__) -> Dict[str, Any]:
        """Arguments to pass to the QuerySet filter on Transactions."""

    def get_table_data(self, *args, **kwargs) -> "QuerySet":
        kwargs = self.get_filter_kwargs(*args, **kwargs)
        return models.Transaction.objects.filter(**kwargs)

    def get_table_kwargs(self, *args, **kwargs) -> Dict[str, Any]:
        d = super().get_table_kwargs()
        exclude_cols = self.exclude_cols(*args, **kwargs)
        if exclude_cols:
            d["exclude"] = exclude_cols
        return d


# -- ACCOUNTS --
class AccountList(LoginRequiredMixin, SingleTableView):
    model = models.Account
    table_class = tables.AccountTable
    template_name = "budget/account-list.html"

    def get_table_data(self) -> "QuerySet":
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class AccountView(LoginRequiredMixin, TransactionTableMixin, DetailView):
    model = models.Account
    template_name = "budget/account-detail.html"

    def exclude_cols(self) -> Tuple[str, ...]:  # pylint: disable=arguments-differ
        return tuple(["account"])

    def get_filter_kwargs(self) -> Dict[str, Any]:  # pylint: disable=arguments-differ
        return dict(user=self.request.user, upload__account=self.object)


class AccountCreate(
    LoginRequiredMixin, AuthCreateFormMixin, AuthForeignKeyMixin, CreateView
):
    model = models.Account
    fields = ["name", "date_col_name", "amt_col_name", "desc_col_name"]
    template_name = "budget/account-add.html"


class AccountUpdate(
    LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin, UpdateView
):
    model = models.Account
    fields = ["name", "date_col_name", "amt_col_name", "desc_col_name"]
    template_name = "budget/account-update.html"


class AccountDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Account
    success_url = reverse_lazy("budget:account-list")
    template_name = "budget/account-delete.html"


# -- CSV BACKUPS --
class BackupList(LoginRequiredMixin, SingleTableView):
    model = models.CSVBackup
    table_class = tables.BackupTable
    template_name = "budget/backup-list.html"

    def get_table_data(self) -> "QuerySet":
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class BackupUpload(
    LoginRequiredMixin, AuthCreateFormMixin, AuthForeignKeyMixin, CreateView
):
    """Upload a CSV for restore."""

    model = models.CSVBackup
    fields = ["csv"]
    template_name = "budget/backup-add.html"


class BackupCreateNew(LoginRequiredMixin, View):
    """Create a new backup from current transaction data."""

    def post(self, *_, **__) -> "HttpResponseRedirect":
        backup = models.CSVBackup(user=self.request.user)
        backup.create_backup()
        return HttpResponseRedirect(reverse_lazy("budget:backup-list"))


class BackupPurgeAllConfirm(LoginRequiredMixin, TemplateView):
    """A splash page with a button to purge all transactions."""

    template_name = "budget/backup-purge-confirm.html"


class BackupPurgeAll(LoginRequiredMixin, View):
    """Purges all transactions."""

    def post(self, *_, **__) -> "HttpResponseRedirect":
        models.Transaction.objects.filter(user=self.request.user).delete()
        return HttpResponseRedirect(reverse_lazy("budget:backup-list"))


class BackupView(LoginRequiredMixin, DetailView):
    model = models.CSVBackup
    template_name = "budget/backup-detail.html"


class BackupDownload(LoginRequiredMixin, SingleObjectMixin, View):
    """Gets the file response for a backup."""

    def get(self, *_, **__) -> "FileResponse":
        return self.get_object(
            queryset=models.CSVBackup.objects.filter(user=self.request.user)
        ).file_response()


class BackupRestore(LoginRequiredMixin, SingleObjectMixin, View):
    """Restores transactions from a backup."""

    def post(self, *_, **__) -> "HttpResponseRedirect":
        obj = self.get_object(
            queryset=models.CSVBackup.objects.filter(user=self.request.user)
        )  # type: models.CSVBackup
        msg = obj.restore()
        if msg != obj.SUCCESS_CODE:
            messages.error(self.request, f"Restore failed: {msg}")

        return HttpResponseRedirect(reverse_lazy("budget:backup-list"))


class BackupDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.CSVBackup
    success_url = reverse_lazy("budget:backup-list")
    template_name = "budget/backup-delete.html"


# -- UPLOADS --
class UploadList(LoginRequiredMixin, SingleTableView):
    model = models.Upload
    table_class = tables.UploadTable
    template_name = "budget/upload-list.html"

    def get_table_data(self) -> "QuerySet":
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class UploadView(LoginRequiredMixin, TransactionTableMixin, DetailView):
    model = models.Upload
    template_name = "budget/upload-detail.html"

    def exclude_cols(self) -> Tuple[str, ...]:  # pylint: disable=arguments-differ
        return "account", "upload"

    def get_filter_kwargs(self) -> Dict[str, Any]:  # pylint: disable=arguments-differ
        return dict(user=self.request.user, upload=self.object)


class UploadCreate(LoginRequiredMixin, AuthForeignKeyMixin, CreateView):
    model = models.Upload
    fields = ["account", "csv"]
    template_name = "budget/upload-add.html"

    def form_valid(self, form: "Form") -> "HttpResponseRedirect":
        form.instance.user = self.request.user
        self.object = form.save()  # pylint: disable=attribute-defined-outside-init

        msg = self.object.parse_transactions()
        if msg == self.model.SUCCESS_CODE:
            # Add transactions after saving, before redirecting
            url = self.get_success_url()
        else:
            # This should redirect to a page showing the error mesage instead
            self.object.delete()
            messages.error(self.request, f"Upload failed: {msg}")
            url = reverse("budget:upload-list")

        return HttpResponseRedirect(url)


class UploadDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Upload
    template_name = "budget/upload-delete.html"

    def get_success_url(self) -> str:
        return reverse_lazy("budget:upload-list")


# -- CLASSES --
class BudgetUpdate(
    LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin, UpdateView
):
    model = models.Budget
    fields = ["value"]
    template_name = "budget/budget-update.html"


class ClassView(LoginRequiredMixin, DetailView, SingleTableMixin):
    model = models.TransactionClass
    template_name = "budget/class-detail.html"

    table_class = Table

    def get_category_linkify_func(
        self, class_id: int
    ) -> Callable[[Dict[str, Any]], Union[str, None]]:
        user = self.request.user

        def linkify(record: Dict[str, Any]) -> Union[str, None]:
            try:
                cat = models.Category.objects.get(
                    user=user, class_field_id=class_id, name=record["category"]
                )
                return cat.get_absolute_url()
            except models.Category.DoesNotExist:
                return None

        return linkify

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        fmt = "%b_%y"
        orig = thirteen_months_ago()
        first = datetime.date(year=orig.year, month=orig.month, day=1)
        now = timezone.now()
        last = datetime.date(year=now.year, month=now.month, day=1)

        # Add each month to the header
        cols = []
        cur = first
        while cur <= last:
            cols.append(cur.strftime(fmt))
            cur = first_day_month_after(cur)

        linkify_func = self.get_category_linkify_func(self.object.id)
        extra_cols = [("category", Column(accessor="category", linkify=linkify_func))]
        extra_cols.extend(
            [(c, Column(attrs={"td": dict(align="right")})) for c in cols]
        )
        qs = oys_qs(user=self.request.user, class_id=self.object.id)
        t = self.table_class(data=qs, extra_columns=extra_cols)
        context["table"] = t
        return context

    def budget(self) -> "Budget":
        return models.Budget.objects.filter(
            user=self.request.user, class_field=self.object
        ).first()

    def categories(self) -> Dict[str, int]:
        return {c.name: c.id for c in self.object.category_set.all()}


# -- CATEGORIES --
class CategoryView(LoginRequiredMixin, TransactionTableMixin, DetailView):
    model = models.Category
    template_name = "budget/category-detail.html"

    def exclude_cols(self) -> Tuple[str, ...]:  # pylint: disable=arguments-differ
        return "class_", "category"

    def get_filter_kwargs(self) -> Dict[str, Any]:  # pylint: disable=arguments-differ
        return dict(user=self.request.user, pattern__category=self.object)


class CategoryCreate(
    LoginRequiredMixin, AuthCreateFormMixin, AuthForeignKeyMixin, CreateView
):
    model = models.Category
    fields = ["name", "class_field"]
    template_name = "budget/category-add.html"


class CategoryUpdate(
    LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin, UpdateView
):
    model = models.Category
    fields = ["name", "class_field"]
    template_name = "budget/category-update.html"


class CategoryDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Category
    success_url = reverse_lazy("budget:index")
    template_name = "budget/category-delete.html"


# -- PATTERNS --
class PatternClassify(LoginRequiredMixin, RedirectView):
    pattern_name = "budget:pattern-list"

    def get_redirect_url(self, *args, **kwargs) -> str:
        # Classify
        for p in models.Pattern.objects.filter(user=self.request.user):
            p.match_transactions()
        return super().get_redirect_url(*args, **kwargs)


class PatternDeclassify(LoginRequiredMixin, RedirectView):
    pattern_name = "budget:pattern-list"

    def get_redirect_url(self, *args, **kwargs) -> str:
        # Delassify
        models.Transaction.objects.filter(user=self.request.user).update(pattern=None)
        return super().get_redirect_url(*args, **kwargs)


class PatternList(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = models.Pattern
    table_class = tables.PatternTable
    template_name = "budget/pattern-list.html"
    filterset_class = tables.PatternFilter

    def get_table_data(self) -> "QuerySet":
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        li = models.Transaction.objects.filter(user=self.request.user, pattern=None)
        context["unmatched_transaction_list"] = li
        context["num_unmatched_transactions"] = len(li)
        return context


class PatternView(LoginRequiredMixin, TransactionTableMixin, DetailView):
    model = models.Pattern
    template_name = "budget/pattern-detail.html"

    def exclude_cols(self) -> Tuple[str, ...]:  # pylint: disable=arguments-differ
        return "class_", "category", "pattern"

    def get_filter_kwargs(self) -> Dict[str, Any]:  # pylint: disable=arguments-differ
        return dict(user=self.request.user, pattern=self.object)


class PatternCreate(
    LoginRequiredMixin, AuthCreateFormMixin, AuthForeignKeyMixin, CreateView
):
    model = models.Pattern
    template_name = "budget/pattern-add.html"

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        li = models.Transaction.objects.filter(
            user=self.request.user, pattern=None
        ).order_by("description")
        context["unmatched_transaction_list"] = li
        context["num_unmatched_transactions"] = len(li)
        return context

    def get_form_class(self):
        return forms.PatternForm

    def get_success_url(self) -> str:
        return reverse("budget:pattern-add")


class PatternUpdate(
    LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin, UpdateView
):
    model = models.Pattern
    template_name = "budget/pattern-update.html"

    def get_form_class(self):
        return forms.PatternForm


class PatternDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Pattern
    success_url = reverse_lazy("budget:pattern-list")
    template_name = "budget/pattern-delete.html"


class PatternBulkUpdate(LoginRequiredMixin, FormView):
    form_class = forms.PatternBulkUpdateForm
    success_url = reverse_lazy("budget:pattern-list")
    template_name = "budget/pattern-bulk-update.html"

    def form_valid(  # pylint: disable=too-many-locals
        self, form: "forms.PatternBulkUpdateForm",
    ) -> "HttpResponseRedirect":
        # Read the CSV into a DataFrame
        path = self.request.FILES["csv"]
        try:
            df = pd.read_csv(path, usecols=["Pattern", "Category", "Class"], dtype=str)
        except ValueError as e:
            messages.error(self.request, f"Restore failed: {e}")
            return self.form_invalid(form)

        # Keep track of some things for transparency
        counts = {
            "Unknown Transaction Classes": 0,
            "New Categories Added": 0,
            "Existing Patterns Not Overwritten": 0,
            "New Patterns Added": 0,
        }

        # Validate the classes, raising warnings as needed
        cls_objs = {}  # type: Dict[str, models.TransactionClass]
        for cls in df.Class.unique():
            try:
                cls_objs[cls] = models.TransactionClass.objects.get(name=cls.lower())
            except models.TransactionClass.DoesNotExist:
                counts["Unknown Transaction Classes"] += 1
                messages.warning(self.request, f"Unknown transaction class: {cls}")

        # Create the categories as needed
        cat_objs = {}  # type: Dict[str, models.Category]
        gb = df.groupby(["Class", "Category"]).count().reset_index()
        for __, row in gb.iterrows():
            if row.Class not in cls_objs:
                continue
            cat_objs[row.Category], created = models.Category.objects.get_or_create(
                user=self.request.user,
                name=row.Category,
                class_field=cls_objs[row.Class],
            )
            if created:
                counts["New Categories Added"] += 1

        # Iterate through the data
        for __, row in df.iterrows():
            if row.Category not in cat_objs:
                continue
            _, created = models.Pattern.objects.get_or_create(
                user=self.request.user,
                pattern=row.Pattern,
                defaults={"category": cat_objs[row.Category]},
            )
            if created:
                counts["New Patterns Added"] += 1
            else:
                counts["Existing Patterns Not Overwritten"] += 1

        # Add processing info to messages
        for k, v in counts.items():
            if not v:
                continue
            messages.info(self.request, f"{k}: {v}")

        return super().form_valid(form)


# -- TRANSACTIONS --
class TransactionList(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = models.Transaction
    template_name = "budget/transaction-list.html"
    table_class = tables.TransactionTable
    filterset_class = tables.TransactionFilter

    def get_table_data(self) -> "QuerySet":
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class TransactionView(LoginRequiredMixin, AuthQuerySetMixin, DetailView):
    model = models.Transaction
    template_name = "budget/transaction-detail.html"


class TransactionDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Transaction
    template_name = "budget/transaction-delete.html"

    def get_success_url(self) -> str:
        return reverse_lazy("budget:transaction-list")
