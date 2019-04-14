import calendar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from budget import models
from budget.utils import one_year_summary


def index(request):
    return render(request, 'budget/index.html')


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


# -- BANKS --
class BankList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Bank
    template_name = 'budget/bank-list.html'


class BankView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Bank
    template_name = 'budget/bank-detail.html'


class BankCreate(LoginRequiredMixin, AuthCreateFormMixin, AuthForeignKeyMixin,
                 CreateView):
    model = models.Bank
    fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']
    template_name = 'budget/bank-add.html'


class BankUpdate(LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin,
                 UpdateView):
    model = models.Bank
    fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']
    template_name = 'budget/bank-update.html'


class BankDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Bank
    success_url = reverse_lazy('budget:bank-list')
    template_name = 'budget/bank-delete.html'


# -- ACCOUNTS --
class AccountList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Account
    template_name = 'budget/account-list.html'


class AccountView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Account
    template_name = 'budget/account-detail.html'


class AccountCreate(LoginRequiredMixin, AuthCreateFormMixin,
                    AuthForeignKeyMixin, CreateView):
    model = models.Account
    fields = ['name', 'bank']
    template_name = 'budget/account-add.html'


class AccountUpdate(LoginRequiredMixin, AuthQuerySetMixin, AuthForeignKeyMixin,
                    UpdateView):
    model = models.Account
    fields = ['name', 'bank']
    template_name = 'budget/account-update.html'


class AccountDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Account
    success_url = reverse_lazy('budget:account-list')
    template_name = 'budget/account-delete.html'


# -- UPLOADS --
class UploadList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Upload
    template_name = 'budget/upload-list.html'


class UploadView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Upload
    template_name = 'budget/upload-detail.html'


class UploadCreate(LoginRequiredMixin, AuthForeignKeyMixin, CreateView):
    model = models.Upload
    fields = ['account', 'csv']
    template_name = 'budget/upload-add.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()

        if self.object.parse_transactions():  # Add transactions after saving, before redirecting
            return HttpResponseRedirect(self.get_success_url())
        else:
            self.object.delete()
            return reverse('budget:upload-list')


class UploadDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Upload
    template_name = 'budget/upload-delete.html'

    def get_success_url(self):
        return reverse_lazy('budget:upload-list')


# -- CLASSES --
class BudgetUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                   AuthForeignKeyMixin, generic.UpdateView):
    model = models.Budget
    fields = ['value']
    template_name = 'budget/budget-update.html'


class ClassList(LoginRequiredMixin, generic.ListView):
    model = models.TransactionClass
    template_name = 'budget/class-list.html'


class ClassView(LoginRequiredMixin, generic.DetailView):
    model = models.TransactionClass
    template_name = 'budget/class-detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # Get user's transactions
        context['transactions'] = self.object.transactions(
            user=self.request.user)

        # Get budget
        context['budget'] = models.Budget.objects.filter(
            user=self.request.user, class_field=self.object).first()

        # Add a dict of category names and pks
        context['categories'] = {
            sc.name: sc.id
            for sc in self.object.category_set.all()
        }

        if context['categories']:  # Has categories
            df = one_year_summary(
                user=self.request.user,
                class_field=models.TransactionClass.objects.get(
                    name=self.object.name))

            # Convert (2018, 2) MultiIndex into "Feb 2018"
            cols = []
            for i in df.columns:
                if i[1] in range(1, 13):
                    cols.append(str(calendar.month_abbr[i[1]]) + " " + str(i[0]))
                else:
                    cols.append(i[0])
            context.update({
                'columns': cols,
                # Convert each row into a list of strings
                # (formatted to 0 decimal places)
                'data': {i: [f'{f:.0f}' for f in r]
                         for i, r in df.iterrows()}
            })
        else:
            context['columns'] = []
            context['data'] = {}
        return context


# -- CATEGORIES --
class CategoryList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Category
    template_name = 'budget/category-list.html'


class CategoryView(LoginRequiredMixin, AuthQuerySetMixin,
                   generic.DetailView):
    model = models.Category
    template_name = 'budget/category-detail.html'


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
    success_url = reverse_lazy('budget:category-list')
    template_name = 'budget/category-delete.html'


# -- PATTERNS --
class PatternClassify(LoginRequiredMixin, generic.RedirectView):
    pattern_name = 'budget:pattern-list'

    def get_redirect_url(self, *args, **kwargs):
        # Classify
        for p in models.Pattern.objects.filter(user=self.request.user):
            p.match_transactions()
        return super().get_redirect_url(*args, **kwargs)


class PatternDeclassify(LoginRequiredMixin, generic.RedirectView):
    pattern_name = 'budget:pattern-list'

    def get_redirect_url(self, *args, **kwargs):
        # Delassify
        models.Transaction.objects.filter(user=self.request.user).update(
            pattern=None)
        return super().get_redirect_url(*args, **kwargs)


class PatternList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Pattern
    template_name = 'budget/pattern-list.html'

    def get_context_data(self, **kwargs):
        context = super(PatternList, self).get_context_data(**kwargs)
        li = models.Transaction.objects.filter(user=self.request.user,
                                               pattern=None)
        context['unmatched_transaction_list'] = li
        context['num_unmatched_transactions'] = len(li)
        return context


class PatternView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Pattern
    template_name = 'budget/pattern-detail.html'


class PatternCreate(LoginRequiredMixin, AuthCreateFormMixin,
                    AuthForeignKeyMixin, CreateView):
    model = models.Pattern
    fields = ['pattern', 'category']
    template_name = 'budget/pattern-add.html'

    def get_context_data(self, **kwargs):
        context = super(PatternCreate, self).get_context_data(**kwargs)
        li = models.Transaction.objects.filter(
            user=self.request.user, pattern=None).order_by('description')
        context['unmatched_transaction_list'] = li
        context['num_unmatched_transactions'] = len(li)
        return context

    def get_success_url(self):
        return reverse('budget:pattern-add')


class PatternUpdate(LoginRequiredMixin, AuthQuerySetMixin,
                    AuthForeignKeyMixin, UpdateView):
    model = models.Pattern
    fields = ['pattern', 'category']
    template_name = 'budget/pattern-update.html'


class PatternDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Pattern
    success_url = reverse_lazy('budget:pattern-list')
    template_name = 'budget/pattern-delete.html'


# -- TRANSACTIONS --
class TransactionList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Transaction
    template_name = 'budget/transaction-list.html'


class TransactionView(LoginRequiredMixin, AuthQuerySetMixin,
                      generic.DetailView):
    model = models.Transaction
    template_name = 'budget/transaction-detail.html'


class TransactionDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Transaction
    template_name = 'budget/transaction-delete.html'

    def get_success_url(self):
        return reverse_lazy('budget:transaction-list')


# -- SUMMARIES --
class OneYearSummary(LoginRequiredMixin, generic.TemplateView):
    template_name = 'budget/one_year_summary.html'

    def get_context_data(self):
        df = one_year_summary(user=self.request.user)

        # Convert (2018, 2) MultiIndex into "Feb 2018"
        cols = []
        for i in df.columns:
            if i[1] in range(1, 13):
                cols.append(str(calendar.month_abbr[i[1]]) + " " + str(i[0]))
            else:
                cols.append(i[0])
        context = {
            'columns': cols,
            # Convert each row into a list of strings
            # (formatted to 0 decimal places)
            'data': {i: [f'{f:.0f}' for f in r]
                     for i, r in df.iterrows()},
            # Add a dict of category names and pks
            'classes': {c.name: c.id
                        for c in models.TransactionClass.objects.all()}}
        return context
