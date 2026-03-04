from django.forms.models import model_to_dict

from .models import AuditLog


def serialize_instance(instance, fields=None):
    return model_to_dict(instance, fields=fields)


def log_action(request, action, instance, before=None, after=None):
    actor = getattr(request, 'user', None)
    actor_name = ''
    if actor and getattr(actor, 'is_authenticated', False):
        actor_name = actor.get_username()
    AuditLog.objects.create(
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance),
        actor=actor if actor and actor.is_authenticated else None,
        actor_name=actor_name,
        ip=(request.META.get('REMOTE_ADDR') or ''),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:255],
        before=before,
        after=after,
    )
