import datetime
from abc import abstractmethod
from typing import Any, Dict, List, Tuple, Union, TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_filters.views import FilterView, FilterMixin
from django_tables2 import Column
from django_tables2.export.views import ExportMixin
from django_tables2.views import SingleTableMixin, SingleTableView

from budget import forms, models, tables
from budget.utils import (
    oys_qs, thirteen_months_ago, first_day_month_after)

if TYPE_CHECKING:
    from django.db.models.query import QuerySet
    from django.forms import Form

    from budget.models import Budget


class Index(LoginRequiredMixin, SingleTableView):
    template_name = 'budget/index.html'
    table_class = tables.SummaryTable

    def get_queryset(self) -> List[Dict[str, Union[str, int]]]:
        qs = oys_qs(user=self.request.user)
        return qs

    def get_table_kwargs(self) -> Dict[str, List[Tuple[str, 'Column']]]:
        fmt = '%b_%y'
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

        extra_cols = [
            (c, Column(attrs={'td': dict(align='right')})) for c in cols]
        return dict(extra_columns=extra_cols)


class AuthQuerySetMixin:
    """A mixin for generic display views for user data.

    Restricts the queryset to user-associated data only.
    """
    model = None
    request = None

    def get_queryset(self) -> 'QuerySet':
        return self.model.objects.filter(user=self.request.user)


class AuthCreateFormMixin:
    """A mixin for generic create views for user data.

    Automatically assigns the logged-in user to the 'user' field of the
    model.
    """
    request = None

    def form_valid(self, form: 'Form') -> bool:
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
        if 'form' in context and hasattr(context['form'], 'fields'):
            fk_fields = [
                f for f in self.model._meta.get_fields()
                if isinstance(f, ForeignKey)
                and f.name in context['form'].fields
            ]
            for f in fk_fields:
                try:
                    qs = f.related_model.objects.filter(user=self.request.user)
                except FieldError:  # Not a user field
                    qs = f.related_model.objects.all()
                context['form'].fields[f.name].queryset = qs
        return context


class TransactionTableMixin(SingleTableMixin, FilterMixin):
    """A mixin for including a table of transactions in a view."""
    table_class = tables.TransactionTable
    filterset_class = tables.TransactionFilter
    table_pagination = dict(per_page=15)

    @abstractmethod
    def exclude_cols(self, *_, **__) -> Tuple[str, ...]:
        """Columns to exclude from the table."""
        return tuple()

    @abstractmethod
    def get_filter_kwargs(self, *_, **__) -> Dict[str, Any]:
        """Arguments to pass to the QuerySet filter on Transactions."""
        return dict()

    def get_table_data(self, *args, **kwargs) -> 'QuerySet':
        kwargs = self.get_filter_kwargs(*args, **kwargs)
        if kwargs:
            return models.Transaction.objects.filter(**kwargs)
        return models.Transaction.objects.all()

    def get_table_kwargs(self, *args, **kwargs) -> Dict[str, Any]:
        d = super().get_table_kwargs()
        exclude_cols = self.exclude_cols(*args, **kwargs)
        if exclude_cols:
            d['exclude'] = exclude_cols
        return d


# -- ACCOUNTS --
class AccountList(LoginRequiredMixin, SingleTableView, ExportMixin):
    model = models.Account
    table_class = tables.AccountTable
    template_name = 'budget/account-list.html'

    def get_table_data(self) -> 'QuerySet':
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class AccountView(LoginRequiredMixin, TransactionTableMixin,
                  generic.DetailView):
    model = models.Account
    template_name = 'budget/account-detail.html'

    def exclude_cols(self) -> Tuple[str, ...]:
        return tuple(['account'])

    def get_filter_kwargs(self) -> Dict[str, Any]:
        return dict(
            user=self.request.user,
            upload__account=self.object)


class AccountCreate(LoginRequiredMixin, AuthCreateFormMixin,
                    AuthForeignKeyMixin, CreateView):
    model = models.Account
    fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']
    template_name = 'budget/account-add.html'


class AccountUpdate(LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin,
                    UpdateView):
    model = models.Account
    fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']
    template_name = 'budget/account-update.html'


class AccountDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Account
    success_url = reverse_lazy('budget:account-list')
    template_name = 'budget/account-delete.html'


# -- UPLOADS --
class UploadList(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = models.Upload
    table_class = tables.UploadTable
    template_name = 'budget/upload-list.html'
    filterset_class = tables.UploadFilter

    def get_table_data(self) -> 'QuerySet':
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class UploadView(LoginRequiredMixin, TransactionTableMixin,
                 generic.DetailView):
    model = models.Upload
    template_name = 'budget/upload-detail.html'

    def exclude_cols(self) -> Tuple[str, ...]:
        return 'account', 'upload'

    def get_filter_kwargs(self) -> Dict[str, Any]:
        return dict(
            user=self.request.user,
            upload=self.object)


class UploadCreate(LoginRequiredMixin, AuthForeignKeyMixin, CreateView):
    model = models.Upload
    fields = ['account', 'csv']
    template_name = 'budget/upload-add.html'

    def form_valid(self, form: 'Form') -> Union['HttpResponseRedirect', str]:
        form.instance.user = self.request.user
        self.object = form.save()

        if self.object.parse_transactions():
            # Add transactions after saving, before redirecting
            return HttpResponseRedirect(self.get_success_url())
        else:
            self.object.delete()
            return reverse('budget:upload-list')


class UploadDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Upload
    template_name = 'budget/upload-delete.html'

    def get_success_url(self) -> str:
        return reverse_lazy('budget:upload-list')


# -- CLASSES --
class BudgetUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                   AuthForeignKeyMixin, generic.UpdateView):
    model = models.Budget
    fields = ['value']
    template_name = 'budget/budget-update.html'


class ClassView(LoginRequiredMixin, generic.DetailView, SingleTableMixin):
    model = models.TransactionClass
    template_name = 'budget/class-detail.html'

    table_class = tables.ClassSummaryTable

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        fmt = '%b_%y'
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

        extra_cols = [
            (c, Column(attrs={'td': dict(align='right')})) for c in cols]
        qs = oys_qs(user=self.request.user,
                    class_id=self.object.id)
        t = self.table_class(
            data=qs,
            extra_columns=extra_cols)
        context['table'] = t
        return context

    def budget(self) -> 'Budget':
        return models.Budget.objects.filter(
            user=self.request.user, class_field=self.object).first()

    def categories(self) -> Dict[str, int]:
        return {
            c.name: c.id
            for c in self.object.category_set.all()}


# -- CATEGORIES --
class CategoryView(LoginRequiredMixin, TransactionTableMixin,
                   generic.DetailView):
    model = models.Category
    template_name = 'budget/category-detail.html'

    def exclude_cols(self) -> Tuple[str, ...]:
        return 'class_', 'category'

    def get_filter_kwargs(self) -> Dict[str, Any]:
        return dict(
            user=self.request.user,
            pattern__category=self.object)


class CategoryCreate(LoginRequiredMixin, AuthCreateFormMixin,
                     AuthForeignKeyMixin, CreateView):
    model = models.Category
    fields = ['name', 'class_field']
    template_name = 'budget/category-add.html'


class CategoryUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                     AuthForeignKeyMixin, UpdateView):
    model = models.Category
    fields = ['name', 'class_field']
    template_name = 'budget/category-update.html'


class CategoryDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Category
    success_url = reverse_lazy('budget:index')
    template_name = 'budget/category-delete.html'


# -- PATTERNS --
class PatternClassify(LoginRequiredMixin, generic.RedirectView):
    pattern_name = 'budget:pattern-list'

    def get_redirect_url(self, *args, **kwargs) -> str:
        # Classify
        for p in models.Pattern.objects.filter(user=self.request.user):
            p.match_transactions()
        return super().get_redirect_url(*args, **kwargs)


class PatternDeclassify(LoginRequiredMixin, generic.RedirectView):
    pattern_name = 'budget:pattern-list'

    def get_redirect_url(self, *args, **kwargs) -> str:
        # Delassify
        models.Transaction.objects.filter(user=self.request.user).update(
            pattern=None)
        return super().get_redirect_url(*args, **kwargs)


class PatternList(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = models.Pattern
    table_class = tables.PatternTable
    template_name = 'budget/pattern-list.html'
    filterset_class = tables.PatternFilter

    def get_table_data(self) -> 'QuerySet':
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        li = models.Transaction.objects.filter(
            user=self.request.user, pattern=None)
        context['unmatched_transaction_list'] = li
        context['num_unmatched_transactions'] = len(li)
        return context


class PatternView(LoginRequiredMixin, TransactionTableMixin,
                  generic.DetailView):
    model = models.Pattern
    template_name = 'budget/pattern-detail.html'

    def exclude_cols(self) -> Tuple[str, ...]:
        return 'class_', 'category', 'pattern'

    def get_filter_kwargs(self) -> Dict[str, Any]:
        return dict(
            user=self.request.user,
            pattern=self.object)


class PatternCreate(LoginRequiredMixin, AuthCreateFormMixin,
                    AuthForeignKeyMixin, CreateView):
    model = models.Pattern
    template_name = 'budget/pattern-add.html'

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super(PatternCreate, self).get_context_data(**kwargs)
        li = models.Transaction.objects.filter(
            user=self.request.user, pattern=None).order_by('description')
        context['unmatched_transaction_list'] = li
        context['num_unmatched_transactions'] = len(li)
        return context

    def get_form_class(self):
        return forms.PatternForm

    def get_success_url(self) -> str:
        return reverse('budget:pattern-add')


class PatternUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                    AuthForeignKeyMixin, UpdateView):
    model = models.Pattern
    template_name = 'budget/pattern-update.html'

    def get_form_class(self):
        return forms.PatternForm


class PatternDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Pattern
    success_url = reverse_lazy('budget:pattern-list')
    template_name = 'budget/pattern-delete.html'


# -- TRANSACTIONS --
class TransactionList(LoginRequiredMixin, SingleTableMixin, FilterView):
    model = models.Transaction
    template_name = 'budget/transaction-list.html'
    table_class = tables.TransactionTable
    filterset_class = tables.TransactionFilter

    def get_table_data(self) -> 'QuerySet':
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class TransactionView(LoginRequiredMixin, AuthQuerySetMixin,
                      generic.DetailView):
    model = models.Transaction
    template_name = 'budget/transaction-detail.html'


class TransactionDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Transaction
    template_name = 'budget/transaction-delete.html'

    def get_success_url(self) -> str:
        return reverse_lazy('budget:transaction-list')
