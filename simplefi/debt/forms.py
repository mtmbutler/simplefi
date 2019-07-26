from django import forms


class StatementBulkUpdateForm(forms.Form):
    csv = forms.FileField()
