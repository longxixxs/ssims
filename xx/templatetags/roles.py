from django import template

register = template.Library()


@register.filter
def has_role(user, role_name):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return user.groups.filter(name=role_name).exists()


@register.simple_tag(takes_context=True)
def nav_active(context, *route_names):
    request = context.get('request')
    resolver_match = getattr(request, 'resolver_match', None)
    current = getattr(resolver_match, 'url_name', None)
    return 'active' if current in route_names else ''
