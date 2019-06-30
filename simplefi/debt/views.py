import calendar
from typing import List, Dict, Tuple

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_tables2 import Column
from django_tables2.views import SingleTableView

from debt import models, tables
from debt.utils import debt_summary


class Index(LoginRequiredMixin, generic.TemplateView):
    template_name = 'debt/index.html'


class AuthQuerySetMixin:
    """A mixin for generic display views for user data.

    Restricts the queryset to user-associated data only.
    """
    model = None
    request = None

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class AuthCreateFormMixin:
    """A mixin for generic create views for user data.

    Automatically assigns the logged-in user to the 'user' field of the
    model.
    """
    request = None

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AuthForeignKeyMixin:
    """A mixin for generic edit views to protect other users' data.

    Restricts the queryset for all foreign key fields to user-
    associated data only.
    """
    model = None
    request = None

    def get_context_data(self, **kwargs):
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


# -- ACCOUNT HOLDERS --
class AccountHolderList(LoginRequiredMixin, AuthQuerySetMixin,
                        generic.ListView):
    model = models.AccountHolder
    template_name = 'debt/accountholder-list.html'


class AccountHolderView(LoginRequiredMixin, AuthQuerySetMixin,
                        generic.DetailView):
    model = models.AccountHolder
    template_name = 'debt/accountholder-detail.html'


class AccountHolderCreate(LoginRequiredMixin, AuthCreateFormMixin,
                          AuthForeignKeyMixin, CreateView):
    model = models.AccountHolder
    fields = ['name']
    template_name = 'debt/accountholder-add.html'


class AccountHolderUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                          AuthForeignKeyMixin, UpdateView):
    model = models.AccountHolder
    fields = ['name']
    template_name = 'debt/accountholder-update.html'


class AccountHolderDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.AccountHolder
    success_url = reverse_lazy('debt:accountholder-list')
    template_name = 'debt/accountholder-delete.html'


# -- ACCOUNTS --
class AccountList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.CreditLine
    template_name = 'debt/account-list.html'


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


class DebtSummary(LoginRequiredMixin, SingleTableView):
    template_name = 'debt/debt_summary.html'
    table_class = tables.SummaryTable
    table_pagination = False

    def get_queryset(self):
        return debt_summary(self.request.user)

    def get_table_kwargs(self) -> Dict[str, List[Tuple[str, Column]]]:
        credit_lines = models.CreditLine.objects.filter(
            user=self.request.user
        ).order_by('priority')
        extra_cols = []  # type: List[Tuple[str, Column]]
        for cl in credit_lines:
            name = cl.name
            print(f"Defining lambda: {name}")

            def linkme(record):
                print(f"Inside lambda: {name}")
                return tables.linkify_statement(name, record['month'])
            extra_cols.append(
                (cl.name, Column(
                    attrs={'td': dict(align='right')},
                    orderable=False,
                    linkify=lambda record: linkme(record)))
            )

        return {'extra_columns': extra_cols}
