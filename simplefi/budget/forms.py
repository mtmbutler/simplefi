from django import forms

from budget.models import Category, Pattern


class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()


class CategoryClassChoiceField(forms.ModelChoiceField):
    """Use this to show class with categories in a drop-down."""
    def label_from_instance(self, obj: 'Category') -> str:
        return f'{obj.class_field} - {obj.name}'


class PatternForm(forms.ModelForm):
    class Meta:
        model = Pattern
        fields = ['pattern', 'category']
        field_classes = {
            'category': CategoryClassChoiceField,
        }
