from django.conf import settings
from django.db import migrations


DEFAULT_STUDENT_PASSWORD = 'psw123456'
MANAGED_ROLES = ('admin', 'teacher', 'student')


def backfill_student_accounts(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)
    Group = apps.get_model('auth', 'Group')
    Student = apps.get_model('xx', 'student')

    student_group, _ = Group.objects.get_or_create(name='student')

    for stu in Student.objects.all().iterator():
        user = User.objects.filter(username=stu.sno).first()
        if user is None:
            user = User.objects.create_user(
                username=stu.sno,
                password=DEFAULT_STUDENT_PASSWORD,
                first_name=(stu.sname or stu.sno),
            )
        managed_roles = set(
            user.groups.filter(name__in=MANAGED_ROLES).values_list('name', flat=True)
        )
        if managed_roles and managed_roles != {'student'}:
            continue

        if 'student' not in managed_roles:
            user.set_password(DEFAULT_STUDENT_PASSWORD)
            user.save(update_fields=['password'])
            user.groups.add(student_group)

        if stu.user_id is None:
            if Student.objects.filter(user_id=user.id).exclude(pk=stu.pk).exists():
                continue
            stu.user_id = user.id
            stu.save(update_fields=['user'])


class Migration(migrations.Migration):

    dependencies = [
        ('xx', '0004_student_user_alter_student_entime_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_student_accounts, migrations.RunPython.noop),
    ]
