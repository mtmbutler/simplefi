import calendar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from . import models
from .utils import one_year_summary, debt_summary


def index(request):
    return render(request, 'budget/index.html')


class AuthQuerySetMixin:
    model = None
    request = None

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class AuthCreateFormMixin:
    request = None

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


# -- BANKS --
class BankList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Bank
    template_name = 'budget/bank-list.html'


class BankView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Bank
    template_name = 'budget/bank-detail.html'


class BankCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.Bank
    fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']
    template_name = 'budget/bank-add.html'


class BankUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.Bank
    fields = ['name', 'date_col_name', 'amt_col_name', 'desc_col_name']
    template_name = 'budget/bank-update.html'


class BankDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Bank
    success_url = reverse_lazy('budget:bank-list')
    template_name = 'budget/bank-delete.html'


# -- ACCOUNT HOLDERS --
class AccountHolderList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.AccountHolder
    template_name = 'budget/accountholder-list.html'


class AccountHolderView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.AccountHolder
    template_name = 'budget/accountholder-detail.html'


class AccountHolderCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.AccountHolder
    fields = ['name']
    template_name = 'budget/accountholder-add.html'


class AccountHolderUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.AccountHolder
    fields = ['name']
    template_name = 'budget/accountholder-update.html'


class AccountHolderDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.AccountHolder
    success_url = reverse_lazy('budget:accountholder-list')
    template_name = 'budget/accountholder-delete.html'


# -- ACCOUNTS --
class AccountList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Account
    template_name = 'budget/account-list.html'


class AccountView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Account
    template_name = 'budget/account-detail.html'


class AccountCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.Account
    fields = ['name', 'bank', 'holder', 'statement_date', 'date_opened',
              'annual_fee', 'interest_rate', 'credit_line',
              'min_pay_pct', 'min_pay_dlr', 'priority']
    template_name = 'budget/account-add.html'


class AccountUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.Account
    fields = ['name', 'bank', 'holder', 'statement_date', 'date_opened',
              'annual_fee', 'interest_rate', 'credit_line',
              'min_pay_pct', 'min_pay_dlr', 'priority']
    template_name = 'budget/account-update.html'


class AccountDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Account
    success_url = reverse_lazy('budget:account-list')
    template_name = 'budget/account-delete.html'


# -- STATEMENTS --
class StatementCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.Statement
    fields = ['account', 'month', 'year', 'balance']
    template_name = 'budget/statement-add.html'


class StatementUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.Statement
    fields = ['account', 'month', 'year', 'balance']
    template_name = 'budget/statement-update.html'


class StatementDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Statement
    success_url = reverse_lazy('budget:account-list')
    template_name = 'budget/statement-delete.html'


# -- UPLOADS --
class UploadList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Upload
    template_name = 'budget/upload-list.html'


class UploadView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Upload
    template_name = 'budget/upload-detail.html'


class UploadCreate(LoginRequiredMixin, CreateView):
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


# -- CATEGORIES --
class CategoryList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Category
    template_name = 'budget/category-list.html'


class CategoryView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Category
    template_name = 'budget/category-detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # Add a dict of subcategory names and pks
        context['subcategories'] = {
            sc.name: sc.id
            for sc in self.object.subcategory_set.all()
        }

        if context['subcategories']:  # Has subcategories
            df = one_year_summary(category=self.object.name)

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


class CategoryCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.Category
    fields = ['name', 'budget']
    template_name = 'budget/category-add.html'


class CategoryUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.Category
    fields = ['name', 'budget']
    template_name = 'budget/category-update.html'


class CategoryDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Category
    success_url = reverse_lazy('budget:category-list')
    template_name = 'budget/category-delete.html'


# -- SUBCATEGORIES --
class SubcategoryList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Subcategory
    template_name = 'budget/subcategory-list.html'


class SubcategoryView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Subcategory
    template_name = 'budget/subcategory-detail.html'


class SubcategoryCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.Subcategory
    fields = ['name', 'category']
    template_name = 'budget/subcategory-add.html'


class SubcategoryUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.Subcategory
    fields = ['name', 'category']
    template_name = 'budget/subcategory-update.html'


class SubcategoryDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Subcategory
    success_url = reverse_lazy('budget:subcategory-list')
    template_name = 'budget/subcategory-delete.html'


# -- PATTERNS --
class PatternClassify(LoginRequiredMixin, generic.RedirectView):
    pattern_name = 'budget:pattern-list'

    def get_redirect_url(self, *args, **kwargs):
        # Classify
        for p in models.Pattern.objects.all():
            p.match_transactions()
        return super().get_redirect_url(*args, **kwargs)


class PatternDeclassify(LoginRequiredMixin, generic.RedirectView):
    pattern_name = 'budget:pattern-list'

    def get_redirect_url(self, *args, **kwargs):
        # Delassify
        models.Transaction.objects.all().update(pattern=None, category=None, subcategory=None)
        return super().get_redirect_url(*args, **kwargs)


class PatternList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Pattern
    template_name = 'budget/pattern-list.html'

    def get_context_data(self, **kwargs):
        context = super(PatternList, self).get_context_data(**kwargs)
        li = models.Transaction.objects.filter(category_id=None)
        context['unmatched_transaction_list'] = li
        context['num_unmatched_transactions'] = len(li)
        return context


class PatternView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
    model = models.Pattern
    template_name = 'budget/pattern-detail.html'


class PatternCreate(LoginRequiredMixin, AuthCreateFormMixin, CreateView):
    model = models.Pattern
    fields = ['pattern', 'subcategory']
    template_name = 'budget/pattern-add.html'

    def get_context_data(self, **kwargs):
        context = super(PatternCreate, self).get_context_data(**kwargs)
        li = models.Transaction.objects.filter(category_id=None).order_by('description')
        context['unmatched_transaction_list'] = li
        context['num_unmatched_transactions'] = len(li)
        return context

    def get_success_url(self):
        # Classify
        for p in models.Pattern.objects.all():
            p.match_transactions()
        return reverse('budget:pattern-add')


class PatternUpdate(LoginRequiredMixin, AuthQuerySetMixin, UpdateView):
    model = models.Pattern
    fields = ['pattern', 'subcategory']
    template_name = 'budget/pattern-update.html'


class PatternDelete(LoginRequiredMixin, AuthQuerySetMixin, DeleteView):
    model = models.Pattern
    success_url = reverse_lazy('budget:pattern-list')
    template_name = 'budget/pattern-delete.html'


# -- TRANSACTIONS --
class TransactionList(LoginRequiredMixin, AuthQuerySetMixin, generic.ListView):
    model = models.Transaction
    template_name = 'budget/transaction-list.html'


class TransactionView(LoginRequiredMixin, AuthQuerySetMixin, generic.DetailView):
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

    @staticmethod
    def get_context_data():
        df = one_year_summary()

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
            # Add a dict of subcategory names and pks
            'categories': {c.name: c.id
                           for c in models.Category.objects.all()}
        }
        return context


class DebtSummary(LoginRequiredMixin, generic.TemplateView):
    template_name = 'budget/debt_summary.html'

    @staticmethod
    def get_context_data():
        df = debt_summary()

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
                         for a in models.Account.objects.all()}
        }
        return context

