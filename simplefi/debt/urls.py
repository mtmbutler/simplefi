from django.urls import path

from debt import views

app_name = 'debt'
urlpatterns = [
    path('', views.Index.as_view(), name='index'),

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

    # Summaries
    path('summaries/debt', views.DebtSummary.as_view(), name='debt-summary')
]
