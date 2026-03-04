from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.urls import reverse

from .models import depart, cl, student, course


class AuthAndPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass123456")
        admin_group, _ = Group.objects.get_or_create(name="admin")
        self.user.groups.add(admin_group)

    def test_login_page_accessible(self):
        resp = self.client.get(reverse("login"))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)

    def test_login_then_dashboard_ok(self):
        ok = self.client.login(username="tester", password="pass123456")
        self.assertTrue(ok)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)


class StudentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester2", password="pass123456")
        admin_group, _ = Group.objects.get_or_create(name="admin")
        self.user.groups.add(admin_group)
        self.dep = depart.objects.create(dno="D001", dname="计算机", telephone="123456")
        self.cls = cl.objects.create(classno="C001", classname="一班", dno=self.dep)

    def test_add_student_success(self):
        self.client.login(username="tester2", password="pass123456")
        resp = self.client.post(
            reverse("student_add"),
            {
                "sno": "S0001",
                "sname": "张三",
                "sex": "boy",
                "native": "北京",
                "age": "20",
                "classno": self.cls.classno,
                "semester": "1",
                "home": "海淀",
                "telephone": "13800000000",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/students/")
        self.assertTrue(student.objects.filter(sno="S0001", sname="张三").exists())

    def test_student_list_page(self):
        student.objects.create(
            sno="S0002",
            sname="李四",
            sex="girl",
            native="上海",
            age=19,
            classno=self.cls,
            semester=1,
            home="浦东",
            telephone="13900000000",
        )
        self.client.login(username="tester2", password="pass123456")
        resp = self.client.get(reverse("student_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "李四")


class DeleteMethodTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="deleter", password="pass123456")
        admin_group, _ = Group.objects.get_or_create(name="admin")
        self.user.groups.add(admin_group)

        self.dep = depart.objects.create(dno="D101", dname="电子", telephone="123456")
        self.cls = cl.objects.create(classno="C101", classname="电一", dno=self.dep)
        self.stu = student.objects.create(
            sno="S101",
            sname="王五",
            sex="boy",
            classno=self.cls,
        )
        self.course = course.objects.create(cno="K01", cname="数学")

    def test_student_delete_requires_post(self):
        self.client.login(username="deleter", password="pass123456")

        get_resp = self.client.get(reverse("student_delete", args=[self.stu.sno]))
        self.assertEqual(get_resp.status_code, 405)

        post_resp = self.client.post(reverse("student_delete", args=[self.stu.sno]))
        self.assertEqual(post_resp.status_code, 302)
        self.assertEqual(post_resp.url, "/students/")
        self.assertFalse(student.objects.filter(sno=self.stu.sno).exists())

    def test_class_depart_course_delete_requires_post(self):
        self.client.login(username="deleter", password="pass123456")

        class_get = self.client.get(reverse("class_delete", args=[self.cls.classno]))
        depart_get = self.client.get(reverse("depart_delete", args=[self.dep.dno]))
        course_get = self.client.get(reverse("course_delete", args=[self.course.cno]))
        self.assertEqual(class_get.status_code, 405)
        self.assertEqual(depart_get.status_code, 405)
        self.assertEqual(course_get.status_code, 405)

        class_post = self.client.post(reverse("class_delete", args=[self.cls.classno]))
        self.assertEqual(class_post.status_code, 302)
        self.assertEqual(class_post.url, "/classes/")
        self.assertFalse(cl.objects.filter(classno=self.cls.classno).exists())

        dep2 = depart.objects.create(dno="D102", dname="化学", telephone="654321")
        depart_post = self.client.post(reverse("depart_delete", args=[dep2.dno]))
        self.assertEqual(depart_post.status_code, 302)
        self.assertEqual(depart_post.url, "/departs/")
        self.assertFalse(depart.objects.filter(dno=dep2.dno).exists())

        course_post = self.client.post(reverse("course_delete", args=[self.course.cno]))
        self.assertEqual(course_post.status_code, 302)
        self.assertEqual(course_post.url, "/courses/")
        self.assertFalse(course.objects.filter(cno=self.course.cno).exists())


class UserManagementRulesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin_rule", password="pass123456")
        admin_group, _ = Group.objects.get_or_create(name="admin")
        self.admin.groups.add(admin_group)
        self.dep = depart.objects.create(dno="D201", dname="机械", telephone="123456")
        self.cls = cl.objects.create(classno="C201", classname="机一", dno=self.dep)

    def test_register_creates_pending_user_without_role(self):
        resp = self.client.post(
            reverse("register"),
            {
                "username": "pending_user",
                "nickname": "待审",
                "password1": "Pending123",
                "password2": "Pending123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/login/")

        u = User.objects.get(username="pending_user")
        self.assertEqual(u.groups.count(), 0)

        login_resp = self.client.post(reverse("login"), {"username": "pending_user", "password": "Pending123"})
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, "/login/")

    def test_user_create_rejects_multiple_roles_and_invalid_role(self):
        self.client.login(username="admin_rule", password="pass123456")

        multi_resp = self.client.post(
            reverse("user_add"),
            {
                "username": "multi_role_u",
                "nickname": "多角色",
                "password1": "Valid123",
                "password2": "Valid123",
                "groups": ["admin", "teacher"],
            },
        )
        self.assertEqual(multi_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="multi_role_u").exists())

        invalid_resp = self.client.post(
            reverse("user_add"),
            {
                "username": "invalid_role_u",
                "nickname": "非法角色",
                "password1": "Valid123",
                "password2": "Valid123",
                "groups": ["madeup_role"],
            },
        )
        self.assertEqual(invalid_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="invalid_role_u").exists())
        self.assertFalse(Group.objects.filter(name="madeup_role").exists())

    def test_user_create_requires_student_profile_for_student_role(self):
        self.client.login(username="admin_rule", password="pass123456")

        resp = self.client.post(
            reverse("user_add"),
            {
                "username": "stu_without_profile",
                "nickname": "学生",
                "password1": "Valid123",
                "password2": "Valid123",
                "groups": ["student"],
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="stu_without_profile").exists())

    def test_password_endpoints_apply_password_validators(self):
        weak_register = self.client.post(
            reverse("register"),
            {
                "username": "weak_user",
                "nickname": "弱密",
                "password1": "11111111",
                "password2": "11111111",
            },
        )
        self.assertEqual(weak_register.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak_user").exists())

        changer = User.objects.create_user(username="pwd_change_u", password="OldPass123")
        teacher_group, _ = Group.objects.get_or_create(name="teacher")
        changer.groups.add(teacher_group)
        self.client.login(username="pwd_change_u", password="OldPass123")
        weak_change = self.client.post(
            reverse("password"),
            {"old": "OldPass123", "new1": "11111111", "new2": "11111111"},
        )
        self.assertEqual(weak_change.status_code, 200)
        self.client.logout()
        self.assertFalse(self.client.login(username="pwd_change_u", password="11111111"))
