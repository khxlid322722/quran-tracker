from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import DailyLog, User


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'password1',
            'password2',
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'First name'},
            ),
            'last_name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Last name'},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('password1', 'password2'):
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        if not User.get_class_teacher():
            raise forms.ValidationError(
                'Student registration is not open yet. Ask your admin to approve '
                'a teacher account first.',
            )
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.teacher = User.get_class_teacher()
        if commit:
            user.save()
        return user


class DailyLogForm(forms.ModelForm):
    class Meta:
        model = DailyLog
        fields = [
            'reading_type',
            'minutes_read',
            'amount_read',
            'unit',
            'notes',
        ]
        widgets = {
            'reading_type': forms.Select(attrs={'class': 'form-control'}),
            'minutes_read': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Minutes'},
            ),
            'amount_read': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Amount'},
            ),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Optional notes about today’s reading',
                },
            ),
        }
