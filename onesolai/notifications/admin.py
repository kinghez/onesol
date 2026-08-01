from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django import forms
from django.utils.html import format_html
from .models import Notification, BroadcastEmail

User = get_user_model()


class NotificationForm(forms.ModelForm):
    send_to = forms.ChoiceField(
        choices=[
            ('all', 'All Users'),
            ('selected', 'Selected User'),
            ('group', 'User Group (Role)'),
        ],
        required=False,
        initial='all',
        help_text="Choose recipient target group for this notification."
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        help_text="Required if 'Selected User' is chosen above."
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        help_text="Required if 'User Group' is chosen above."
    )

    class Meta:
        model = Notification
        fields = ['send_to', 'user', 'group', 'title', 'message', 'notification_type', 'action_url']

    def clean(self):
        cleaned_data = super().clean()
        send_to = cleaned_data.get('send_to')
        user = cleaned_data.get('user')
        group = cleaned_data.get('group')

        if send_to == 'selected' and not user:
            self.add_error('user', 'Please select a user.')
        elif send_to == 'group' and not group:
            self.add_error('group', 'Please select a user group.')
        return cleaned_data


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient_display', 'type_badge', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at',)
    form = NotificationForm

    @admin.display(description='Recipient')
    def recipient_display(self, obj):
        return obj.user.email if obj.user else "System"

    @admin.display(description='Type')
    def type_badge(self, obj):
        colors = {
            'system': '#5B63F6',
            'order': '#10B981',
            'referral': '#8B5CF6',
            'promotion': '#F59E0B',
        }
        color = colors.get(obj.notification_type, '#6B7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.get_notification_type_display().upper()
        )

    def get_fieldsets(self, request, obj=None):
        if obj:  # Viewing / editing existing notification
            return [
                ('Notification Info', {
                    'fields': ('user', 'title', 'message', 'notification_type', 'is_read', 'action_url', 'created_at')
                })
            ]
        # Creating new notification
        return [
            ('Target Audience', {
                'fields': ('send_to', 'user', 'group')
            }),
            ('Notification Details', {
                'fields': ('title', 'message', 'notification_type', 'action_url')
            })
        ]

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new notification
            send_to = form.cleaned_data.get('send_to')
            target_user = form.cleaned_data.get('user')
            target_group = form.cleaned_data.get('group')

            if send_to == 'selected' and target_user:
                obj.user = target_user
                super().save_model(request, obj, form, change)
            elif send_to == 'group' and target_group:
                # First save to current admin user to satisfy instance save
                obj.user = request.user
                super().save_model(request, obj, form, change)

                group_users = User.objects.filter(groups=target_group, is_active=True).exclude(id=request.user.id)
                notifications = [
                    Notification(
                        user=u,
                        title=obj.title,
                        message=obj.message,
                        notification_type=obj.notification_type,
                        action_url=obj.action_url
                    )
                    for u in group_users
                ]
                if notifications:
                    Notification.objects.bulk_create(notifications)
                self.message_user(request, f"Notification sent to {len(notifications) + 1} user(s) in group '{target_group.name}'.")
            else:
                # All users
                obj.user = request.user
                super().save_model(request, obj, form, change)

                all_users = User.objects.filter(is_active=True).exclude(id=request.user.id)
                notifications = [
                    Notification(
                        user=u,
                        title=obj.title,
                        message=obj.message,
                        notification_type=obj.notification_type,
                        action_url=obj.action_url
                    )
                    for u in all_users
                ]
                if notifications:
                    Notification.objects.bulk_create(notifications)
                self.message_user(request, f"Bulk notification broadcasted to {len(notifications) + 1} user(s).")
        else:
            super().save_model(request, obj, form, change)


class BroadcastEmailForm(forms.ModelForm):
    class Meta:
        model = BroadcastEmail
        fields = ['target_type', 'recipient_user', 'group', 'subject', 'message']

    def clean(self):
        cleaned_data = super().clean()
        target_type = cleaned_data.get('target_type')
        recipient_user = cleaned_data.get('recipient_user')
        group = cleaned_data.get('group')

        if target_type == 'single' and not recipient_user:
            self.add_error('recipient_user', 'Please select a specific user.')
        elif target_type == 'group' and not group:
            self.add_error('group', 'Please select a user group.')
        return cleaned_data


@admin.register(BroadcastEmail)
class BroadcastEmailAdmin(admin.ModelAdmin):
    list_display = ('subject', 'target_badge', 'recipient_display', 'recipients_count', 'created_at')
    list_filter = ('target_type', 'created_at')
    search_fields = ('subject', 'message', 'recipient_user__email', 'group__name')
    readonly_fields = ('recipients_count', 'created_at')
    form = BroadcastEmailForm

    @admin.display(description='Target')
    def target_badge(self, obj):
        colors = {
            'all': '#10B981',
            'single': '#3B82F6',
            'group': '#8B5CF6',
        }
        color = colors.get(obj.target_type, '#6B7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.get_target_type_display().upper()
        )

    @admin.display(description='Recipient / Group')
    def recipient_display(self, obj):
        if obj.target_type == 'single' and obj.recipient_user:
            return obj.recipient_user.email
        elif obj.target_type == 'group' and obj.group:
            return f"Group: {obj.group.name}"
        return "All Users"

    def get_fieldsets(self, request, obj=None):
        if obj:  # Viewing sent email
            return [
                ('Email Delivery Summary', {
                    'fields': ('target_type', 'recipient_user', 'group', 'recipients_count', 'created_at')
                }),
                ('Email Content', {
                    'fields': ('subject', 'message')
                })
            ]
        return [
            ('Target Audience', {
                'fields': ('target_type', 'recipient_user', 'group')
            }),
            ('Email Content', {
                'fields': ('subject', 'message')
            })
        ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:  # Send emails on creation
            from core.email_utils import send_async_email
            from core.models import SiteSettings
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from analytics.models import ActivityLog

            cfg = SiteSettings.get()
            site_name = cfg.site_name or 'OneSol AI Hub'
            support_email = cfg.support_email or 'support@onesolai.com'
            site_url = (cfg.site_url or 'https://onesolai.com').rstrip('/')

            if obj.target_type == 'single' and obj.recipient_user:
                recipients = [obj.recipient_user]
            elif obj.target_type == 'group' and obj.group:
                recipients = list(User.objects.filter(groups=obj.group, is_active=True))
            else:
                recipients = list(User.objects.filter(is_active=True))

            count = 0
            for u in recipients:
                if u.email:
                    user_name = u.get_full_name() or u.first_name or u.email.split('@')[0]
                    context = {
                        'user_name': user_name,
                        'site_name': site_name,
                        'support_email': support_email,
                        'site_url': site_url,
                        'subject': obj.subject,
                        'message': obj.message,
                    }
                    html_content = render_to_string('emails/broadcast_email.html', context)
                    plain_text = strip_tags(html_content)

                    send_async_email(
                        subject=f"[{site_name}] {obj.subject}",
                        message=plain_text,
                        recipient_list=[u.email],
                        html_message=html_content
                    )
                    count += 1

            obj.recipients_count = count
            obj.save(update_fields=['recipients_count'])

            ActivityLog.log(
                action_type='system',
                title=f"Broadcast Email Sent: {obj.subject}",
                details=f"Target: {obj.get_target_type_display()} | Sent to {count} user(s)",
                user=request.user,
                severity='info'
            )

            self.message_user(request, f"Broadcast email sent to {count} recipient(s).")
