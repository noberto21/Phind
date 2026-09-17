from django import forms
from .services import validate_imei, validate_email


class IMEITrackingForm(forms.Form):
    DEVICE_CHOICES = [
        ('android', 'Android Device'),
        ('iphone', 'Apple iPhone (iOS)'),
    ]

    device_type = forms.ChoiceField(
        choices=DEVICE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial='android'
    )
    imei = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control font-monospace',
            'placeholder': 'e.g. 354595804618131',
            'id': 'imeiInput'
        })
    )
    apple_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. user@icloud.com',
            'id': 'appleIdInput'
        })
    )
    account_email = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Google account email (optional)',
            'id': 'accountEmailInput'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        device_type = cleaned_data.get('device_type')
        imei = cleaned_data.get('imei')
        apple_id = cleaned_data.get('apple_id')

        if device_type == 'android':
            if not imei:
                self.add_error('imei', 'Please enter a 15-digit IMEI number for Android tracking.')
            else:
                is_valid, clean_imei, warning = validate_imei(imei)
                if not is_valid:
                    self.add_error('imei', warning)
                cleaned_data['clean_imei'] = clean_imei
        elif device_type == 'iphone':
            if not apple_id:
                self.add_error('apple_id', 'Please enter an Apple ID / iCloud email for iPhone tracking.')
            elif not validate_email(apple_id):
                self.add_error('apple_id', 'Please enter a valid Apple ID email address.')

        return cleaned_data


class PhoneLocatorForm(forms.Form):
    phone_number = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control font-monospace',
            'placeholder': '+254712345678 or +14155552671',
            'id': 'phoneNumberInput'
        })
    )
    user_location = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Nairobi, Kenya or London, UK (optional)',
            'id': 'userLocationInput'
        })
    )
