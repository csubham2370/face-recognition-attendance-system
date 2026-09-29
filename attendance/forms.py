from django import forms
import re
from .models import AdminUser, Student

class StudentForm(forms.ModelForm):

    class Meta:

        model = Student

        fields = ["student_id","name","email","photo",]

        widgets = {
            "student_id": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter student ID"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter full name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def clean_student_id(self):
        student_id = self.cleaned_data["student_id"].strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", student_id):
            raise forms.ValidationError("Use only letters, numbers, hyphens, and underscores in the student ID.")
        duplicate = Student.objects.filter(student_id=student_id)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("A student with this ID already exists.")
        return student_id



class AdminLoginForm(forms.Form):

    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control","placeholder": "Enter username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control","placeholder": "Enter password"}))



class CreateAdminForm(forms.Form):

    username = forms.CharField(max_length=100,widget=forms.TextInput(attrs={"class": "form-control","placeholder": "Enter username"}))

    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control","placeholder": "Enter email"}))

    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={"class": "form-control","placeholder": "Enter password"}))

    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control","placeholder": "Confirm password"}))


    def clean(self):

        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:

            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data


class UpdateAdminForm(forms.ModelForm):
    password = forms.CharField(required=False, min_length=8, help_text="Leave blank to keep the current password.", widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New password"}))
    confirm_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm new password"}))

    class Meta:
        model = AdminUser
        fields = ["username", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")
        if username and AdminUser.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            self.add_error("username", "An admin with this username already exists.")
        if email and AdminUser.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            self.add_error("email", "An admin with this email already exists.")
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        admin = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            admin.set_password(password)
        if commit:
            admin.save()
        return admin


class ForgotPasswordForm(forms.Form):

    email = forms.EmailField( widget=forms.EmailInput(attrs={"class": "form-control","placeholder": "Enter admin email"}))
