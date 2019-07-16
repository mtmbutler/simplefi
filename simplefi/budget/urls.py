from django.urls import path

from budget import views

app_name = 'budget'
urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    
    # Accounts
    path('accounts/', views.AccountList.as_view(), name='account-list'),
    path('accounts/add/', views.AccountCreate.as_view(), name='account-add'),
    path('accounts/<int:pk>/', views.AccountView.as_view(), name='account-detail'),
    path('accounts/<int:pk>/update/', views.AccountUpdate.as_view(), name='account-update'),
    path('accounts/<int:pk>/delete/', views.AccountDelete.as_view(), name='account-delete'),
    
    # Backups
    path('backups/', views.BackupList.as_view(), name='backup-list'),
    path('backups/add/', views.BackupCreate.as_view(), name='backup-add'),
    path('backups/<int:pk>/', views.BackupView.as_view(), name='backup-detail'),
    path('backups/<int:pk>/delete/', views.BackupDelete.as_view(), name='backup-delete'),
    
    # Uploads
    path('uploads/', views.UploadList.as_view(), name='upload-list'),
    path('uploads/add/', views.UploadCreate.as_view(), name='upload-add'),
    path('uploads/<int:pk>/', views.UploadView.as_view(), name='upload-detail'),
    path('uploads/<int:pk>/delete/', views.UploadDelete.as_view(), name='upload-delete'),
    
    # Classes
    path('classes/<int:pk>/', views.ClassView.as_view(), name='class-detail'),
    path('classes/<int:pk>/update/', views.BudgetUpdate.as_view(), name='budget-update'),
    
    # Categories
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
    path('transactions/download/', views.TransactionDownloadView.as_view(), name='transaction-download')
]
