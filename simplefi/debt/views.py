import csv
import datetime
import os
import tempfile
from typing import Any, List, Callable, Dict, Mapping, Tuple, Union, TYPE_CHECKING

import pandas as pd
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.http import FileResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_tables2 import Column
from django_tables2.views import SingleTableView

from debt import forms, models, tables
from debt.utils import debt_summary, get_debt_budget

if TYPE_CHECKING:
    from django.db.models import Model
    from django.db.models.query import QuerySet
    from django.http import HttpRequest


class Index(LoginRequiredMixin, generic.TemplateView):
    template_name = 'debt/index.html'


class AuthQuerySetMixin:
    """A mixin for generic display views for user data.

    Restricts the queryset to user-associated data only.
    """
    model = None    # type: Union[Model, None]
    request = None  # type: Union[HttpRequest, None]

    def get_queryset(self) -> 'QuerySet':
        return self.model.objects.filter(user=self.request.user)


class AuthCreateFormMixin:
    """A mixin for generic create views for user data.

    Automatically assigns the logged-in user to the 'user' field of the
    model.
    """
    request = None  # type: Union[HttpRequest, None]

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AuthForeignKeyMixin:
    """A mixin for generic edit views to protect other users' data.

    Restricts the queryset for all foreign key fields to user-
    associated data only.
    """
    model = None  # type: Union[Model, None]
    request = None  # type: Union[HttpRequest, None]

    def get_context_data(self, **kwargs) -> Dict:
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


# -- ACCOUNTS --
class AccountList(LoginRequiredMixin, SingleTableView):
    model = models.CreditLine
    table_class = tables.CreditLineTable
    template_name = 'debt/account-list.html'

    def get_table_data(self) -> 'QuerySet':
        qs = super().get_table_data()
        return qs.filter(user=self.request.user)


class AccountView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.CreditLine
    template_name = 'debt/account-detail.html'


class AccountCreate(LoginRequiredMixin, AuthCreateFormMixin,
                    AuthForeignKeyMixin, CreateView):
    model = models.CreditLine
    fields = ['name', 'holder', 'statement_date', 'date_opened',
              'annual_fee', 'interest_rate', 'credit_line',
              'min_pay_pct', 'min_pay_dlr', 'priority']
    template_name = 'debt/account-add.html'


class AccountUpdate(LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin,
                    UpdateView):
    model = models.CreditLine
    fields = ['name', 'holder', 'statement_date', 'date_opened',
              'annual_fee', 'interest_rate', 'credit_line',
              'min_pay_pct', 'min_pay_dlr', 'priority']
    template_name = 'debt/account-update.html'


class AccountDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.CreditLine
    success_url = reverse_lazy('debt:account-list')
    template_name = 'debt/account-delete.html'


# -- STATEMENTS --
class StatementCreate(LoginRequiredMixin, AuthCreateFormMixin,
                      AuthForeignKeyMixin, CreateView):
    model = models.Statement
    fields = ['account', 'month', 'year', 'balance']
    template_name = 'debt/statement-add.html'


class StatementUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                      AuthForeignKeyMixin, UpdateView):
    model = models.Statement
    fields = ['account', 'month', 'year', 'balance']
    template_name = 'debt/statement-update.html'


class StatementDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Statement
    success_url = reverse_lazy('debt:account-list')
    template_name = 'debt/statement-delete.html'


class StatementBulkDownload(LoginRequiredMixin, generic.View):
    def get(self, *_, **__):
        timestamp = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
        path = os.path.join(tempfile.mkdtemp(), f'statements_{timestamp}.csv')
        fieldnames = ['Account', 'Date', 'Balance']
        qs = models.Statement.objects.filter(user=self.request.user).all()
        with open(path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for statement in qs:
                writer.writerow(dict(
                    Account=statement.account.name,
                    Date=statement.date.strftime('%Y-%m-%d'),
                    Balance=statement.balance))
        return FileResponse(open(path, 'rb'), as_attachment=True)


class StatementBulkUpdate(LoginRequiredMixin, generic.FormView):
    form_class = forms.StatementBulkUpdateForm
    success_url = reverse_lazy('debt:debt-summary')
    template_name = 'debt/statement-bulk-update.html'

    def form_valid(
        self,
        form: 'forms.StatementBulkUpdateForm'
    ) -> 'HttpResponseRedirect':
        # Read the CSV into a DataFrame
        print(self.request.FILES)
        path = self.request.FILES['csv']
        try:
            df = pd.read_csv(path, usecols=['Account', 'Date', 'Balance'],
                             infer_datetime_format=True, parse_dates=['Date'])
        except ValueError as e:
            messages.error(self.request, f"Restore failed: {e}")
            return self.form_invalid(form)

        # Validate the accounts - Use get_or_create to see if there's
        # already an account for each provided name, and raise a warning
        # if there isn't.
        acc_objs = {}  # type: Dict[str, models.CreditLine]
        for acc_name in df.Account.unique():
            acc, created = models.CreditLine.objects.get_or_create(
                user=self.request.user, name=acc_name)
            if created:
                messages.warning(self.request, f"Unknown credit line: {acc_name}")
                acc.delete()
            else:
                acc_objs[acc_name] = acc

        # Add columns for year and month
        # Todo: probably some exceptions to catch here
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month

        # Iterate through the data
        counts = dict(
            unknown_acc=0,
            existing_not_overwritten=0,
            new_stmnts=0)
        for __, row in df.iterrows():
            if row['Account'] not in acc_objs:
                counts['unknown_acc'] += 1
                continue
            stmt, created = models.Statement.objects.get_or_create(
                user=self.request.user, account=acc_objs[row['Account']],
                year=row['Year'], month=row['Month'],
                defaults={'balance': row['Balance']}
            )
            if not created:
                counts['existing_not_overwritten'] += 1
            else:
                counts['new_stmnts'] += 1

        # Add processing info to messages
        for k, v in counts.items():
            if not v:
                continue
            messages.info(self.request, f"{k}: {v}")

        return super().form_valid(form)


class StatementBulkDeleteConfirm(LoginRequiredMixin, generic.TemplateView):
    template_name = 'debt/statement-bulk-delete.html'


class StatementBulkDelete(LoginRequiredMixin, generic.View):
    def post(self, *_, **__):
        models.Statement.objects.filter(user=self.request.user).all().delete()
        return HttpResponseRedirect(reverse_lazy('debt:debt-summary'))


class DebtSummary(LoginRequiredMixin, SingleTableView):
    template_name = 'debt/debt_summary.html'
    table_class = tables.SummaryTable
    table_pagination = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['debt_budget'] = get_debt_budget(self.request.user)
        return context

    def get_queryset(self) -> List[Dict[str, str]]:
        return debt_summary(self.request)

    def get_table_kwargs(self) -> Dict[str, List[Tuple[str, Column]]]:
        credit_lines = models.CreditLine.objects.filter(
            user=self.request.user
        ).order_by('priority')
        extra_cols = []  # type: List[Tuple[str, Column]]

        def get_linkify_func(
            col_name: str
        ) -> Callable[[Mapping[str, Any]], str]:
            """Returns a function to linkify each column.

            This takes advantage of closures to generate a separate
            linkify function for each column. See django-tables2 docs
            for more information on what these callables look like.
            """
            def linkify_func(record: Mapping[str, Any]) -> str:
                return tables.linkify_statement(col_name, record['month'])
            return linkify_func

        for cl in credit_lines:
            extra_cols.append(
                (cl.name, Column(
                    attrs={'td': dict(align='right')},
                    orderable=False,
                    linkify=get_linkify_func(cl.name)))
            )
        extra_cols.append(
            ('Total', Column(
                attrs={'td': dict(align='right')},
                orderable=False))
        )

        return {'extra_columns': extra_cols}
