from django.contrib import admin
from django.contrib.auth import get_user_model
from django import forms
from django.utils import timezone
from .models import Notification

User = get_user_model()


class NotificationForm(forms.ModelForm):
    send_to = forms.ChoiceField(
        choices=[
            ('all', 'All Users'),
            ('selected', 'Selected User (choose below)'),
        ],
        required=True,
        help_text="Choose whether to send this to all users or a specific user."
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        help_text="Required if 'Selected User' is chosen above."
    )

    class Meta:
        model = Notification
        fields = ['send_to', 'user', 'title', 'message', 'notification_type', 'action_url']

    def clean(self):
        cleaned_data = super().clean()
        send_to = cleaned_data.get('send_to')
        user = cleaned_data.get('user')

        if send_to == 'selected' and not user:
            self.add_error('user', 'Please select a user.')
        return cleaned_data


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at',)
    form = NotificationForm

    def get_form(self, request, obj=None, **kwargs):
        if obj:  # On edit, don't show the bulk send fields
            kwargs['exclude'] = ['send_to']
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:  # Only intercept on creation
            send_to = form.cleaned_data.get('send_to')
            if send_to == 'all':
                # Save the master object to the admin user to satisfy Django admin logging
                obj.user = request.user
                super().save_model(request, obj, form, change)
                
                # Bulk create for everyone else
                users = User.objects.exclude(id=request.user.id)
                notifications = []
                for user in users:
                    notifications.append(
                        Notification(
                            user=user,
                            title=obj.title,
                            message=obj.message,
                            notification_type=obj.notification_type,
                            action_url=obj.action_url,
                        )
                    )
                if notifications:
                    Notification.objects.bulk_create(notifications)
                return
            else:
                obj.user = form.cleaned_data.get('user')
        super().save_model(request, obj, form, change)
