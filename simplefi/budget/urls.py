from django.urls import path

from . import views

app_name = 'budget'
urlpatterns = [
    path('', views.index, name='index'),
    
    # Banks
    path('banks/', views.BankList.as_view(), name='bank-list'),
    path('banks/add/', views.BankCreate.as_view(), name='bank-add'),
    path('banks/<int:pk>/', views.BankView.as_view(), name='bank-detail'),
    path('banks/<int:pk>/update/', views.BankUpdate.as_view(), name='bank-update'),
    path('banks/<int:pk>/delete/', views.BankDelete.as_view(), name='bank-delete'),
    
    # Account holders
    path('accountholders/', views.AccountHolderList.as_view(), name='accountholder-list'),
    path('accountholders/add/', views.AccountHolderCreate.as_view(), name='accountholder-add'),
    path('accountholders/<int:pk>/', views.AccountHolderView.as_view(), name='accountholder-detail'),
    path('accountholders/<int:pk>/update/', views.AccountHolderUpdate.as_view(), name='accountholder-update'),
    path('accountholders/<int:pk>/delete/', views.AccountHolderDelete.as_view(), name='accountholder-delete'),
    
    # Accounts
    path('accounts/', views.AccountList.as_view(), name='account-list'),
    path('accounts/add/', views.AccountCreate.as_view(), name='account-add'),
    path('accounts/<int:pk>/', views.AccountView.as_view(), name='account-detail'),
    path('accounts/<int:pk>/update/', views.AccountUpdate.as_view(), name='account-update'),
    path('accounts/<int:pk>/delete/', views.AccountDelete.as_view(), name='account-delete'),

    # Statements
    path('statements/add/', views.StatementCreate.as_view(), name='statement-add'),
    path('statements/<int:pk>/update/', views.StatementUpdate.as_view(), name='statement-update'),
    path('statements/<int:pk>/delete/', views.StatementDelete.as_view(), name='statement-delete'),
    
    # Uploads
    path('uploads/', views.UploadList.as_view(), name='upload-list'),
    path('uploads/add/', views.UploadCreate.as_view(), name='upload-add'),
    path('uploads/<int:pk>/', views.UploadView.as_view(), name='upload-detail'),
    path('uploads/<int:pk>/delete/', views.UploadDelete.as_view(), name='upload-delete'),
    
    # Classes
    path('classes/', views.ClassList.as_view(), name='class-list'),
    path('classes/<int:pk>/', views.ClassView.as_view(), name='class-detail'),
    path('classes/<int:pk>/update/', views.BudgetUpdate.as_view(), name='budget-update'),
    
    # Categories
    path('categories/', views.CategoryList.as_view(), name='category-list'),
    path('categories/add/', views.CategoryCreate.as_view(), name='category-add'),
    path('categories/<int:pk>/', views.CategoryView.as_view(), name='category-detail'),
    path('categories/<int:pk>/update/', views.CategoryUpdate.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', views.CategoryDelete.as_view(), name='category-delete'),
    
    # Patterns
    path('patterns/', views.PatternList.as_view(), name='pattern-list'),
    path('patterns/add/', views.PatternCreate.as_view(), name='pattern-add'),
    path('patterns/<int:pk>/', views.PatternView.as_view(), name='pattern-detail'),
    path('patterns/<int:pk>/update/', views.PatternUpdate.as_view(), name='pattern-update'),
    path('patterns/<int:pk>/delete/', views.PatternDelete.as_view(), name='pattern-delete'),
    path('patterns/classify/', views.PatternClassify.as_view(), name='classify'),
    path('patterns/declassify/', views.PatternDeclassify.as_view(), name='declassify'),
    
    # Transactions
    path('transactions/', views.TransactionList.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', views.TransactionView.as_view(), name='transaction-detail'),
    path('transactions/<int:pk>/delete/', views.TransactionDelete.as_view(), name='transaction-delete'),

    # Summaries
    path('summaries/one_year', views.OneYearSummary.as_view(), name='one-year-summary'),
    path('summaries/debt', views.DebtSummary.as_view(), name='debt-summary')
]
