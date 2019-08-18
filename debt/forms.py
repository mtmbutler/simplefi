from django import forms


class CreditLineBulkUpdateForm(forms.Form):
    csv = forms.FileField()


class StatementBulkUpdateForm(forms.Form):
    csv = forms.FileField()
