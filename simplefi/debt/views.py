import calendar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from debt import models
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


class DebtSummary(LoginRequiredMixin, generic.TemplateView):
    template_name = 'debt/debt_summary.html'

    def get_context_data(self):
        df = debt_summary(self.request.user)

        # Convert (2018, 2) MultiIndex into "Feb 2018"
        index_ = []
        for i in df.index:
            index_.append(str(calendar.month_abbr[i[1]]) + " " + str(i[0]))
        context = {
            'columns': df.columns.tolist(),
            # Convert each row into a list of strings
            # (formatted to 0 decimal places)
            'data': {index_[i]: r.tolist()
                     for i, (__, r) in enumerate(df.iterrows())},
            # Add a dict of account name and pks
            'accounts': {a.name: a.id
                         for a in models.CreditLine.objects.filter(
                            user=self.request.user)}}
        return context
