"""
Custom validators for the accounts app.
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Egyptian mobile numbers: start with 010 / 011 / 012 / 015, 11 digits total.
# PROJECT_SPEC.md 5.1
egyptian_phone_validator = RegexValidator(
    regex=r'^(010|011|012|015)\d{8}$',
    message='رقم الموبايل غير صحيح. لازم يبدأ بـ 010 أو 011 أو 012 أو 015 ويكون 11 رقم بالكامل.',
    code='invalid_egyptian_phone',
)
