from django.urls import path

from debt import views

app_name = 'debt'
urlpatterns = [
    path('', views.Index.as_view(), name='index'),

    # Accounts
    path('accounts/', views.AccountList.as_view(), name='account-list'),
    path('accounts/add/', views.AccountCreate.as_view(), name='account-add'),
    path('accounts/<int:pk>/', views.AccountView.as_view(), name='account-detail'),
    path('accounts/<int:pk>/update/', views.AccountUpdate.as_view(), name='account-update'),
    path('accounts/<int:pk>/delete/', views.AccountDelete.as_view(), name='account-delete'),
    path('accounts/upload/', views.CreditLineBulkUpdate.as_view(), name='creditline-bulk-update'),

    # Statements
    path('statements/add/', views.StatementCreate.as_view(), name='statement-add'),
    path('statements/download/', views.StatementBulkDownload.as_view(), name='statement-download'),
    path('statements/upload/', views.StatementBulkUpdate.as_view(), name='statement-bulk-update'),
    path('statements/delete/confirm', views.StatementBulkDeleteConfirm.as_view(), name='statement-bulk-delete-confirm'),
    path('statements/delete/', views.StatementBulkDelete.as_view(), name='statement-bulk-delete'),
    path('statements/<int:pk>/update/', views.StatementUpdate.as_view(), name='statement-update'),
    path('statements/<int:pk>/delete/', views.StatementDelete.as_view(), name='statement-delete'),

    # Summaries
    path('summaries/debt', views.DebtSummary.as_view(), name='debt-summary')
]
