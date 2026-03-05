from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from .models import AuditLog, cl, course, depart, sc, student


DEFAULT_PASSWORD = "pass123456"
DEFAULT_STUDENT_PASSWORD = "psw123456"
MANAGED_ROLES = ("admin", "teacher", "student")


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        for role in MANAGED_ROLES:
            Group.objects.get_or_create(name=role)

    def create_user(self, username, role=None, password=DEFAULT_PASSWORD):
        user = User.objects.create_user(username=username, password=password, first_name=username)
        if role:
            user.groups.add(Group.objects.get(name=role))
        return user

    def create_school_base(self, dno="D001", classno="C001", cno="K01"):
        dep = depart.objects.create(dno=dno, dname=f"系{dno[-1]}", telephone="123456")
        cls = cl.objects.create(classno=classno, classname=f"班{classno[-1]}", dno=dep)
        crs = course.objects.create(cno=cno, cname=f"课程{cno}", credit=2, semester=1, type="crc")
        return dep, cls, crs

    def build_student_excel_file(self, rows, headers=None):
        if headers is None:
            headers = [
                "sno", "sname", "sex", "native", "age",
                "classno", "semester", "home", "telephone",
            ]
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        buf = BytesIO()
        wb.save(buf)
        return SimpleUploadedFile(
            "students.xlsx",
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class AuthAndPasswordTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_auth", role="admin")
        self.dep, self.cls, _ = self.create_school_base()

    def test_login_register_pages_accessible(self):
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)

    def test_register_creates_pending_user_and_cannot_enter_by_login_view(self):
        resp = self.client.post(
            reverse("register"),
            {
                "username": "pending_user",
                "nickname": "待审",
                "password1": "Pending123!",
                "password2": "Pending123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("login"))

        u = User.objects.get(username="pending_user")
        self.assertEqual(u.groups.count(), 0)

        login_resp = self.client.post(
            reverse("login"),
            {"username": "pending_user", "password": "Pending123!"},
        )
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, reverse("login"))

    def test_logout_requires_post(self):
        self.assertTrue(self.client.login(username="admin_auth", password=DEFAULT_PASSWORD))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

        resp = self.client.post(reverse("logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("login"))

    def test_password_change_success(self):
        teacher = self.create_user("teacher_pwd", role="teacher")
        self.assertTrue(self.client.login(username="teacher_pwd", password=DEFAULT_PASSWORD))

        resp = self.client.post(
            reverse("password"),
            {"old": DEFAULT_PASSWORD, "new1": "NewPass123!", "new2": "NewPass123!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("login"))

        self.assertTrue(self.client.login(username="teacher_pwd", password="NewPass123!"))

    def test_student_login_redirect_to_profile_detail(self):
        stu_user = self.create_user("S2001", role="student", password="Student123!")
        stu = student.objects.create(sno="S2001", user=stu_user, sname="学生2001", sex="boy", classno=self.cls)

        resp = self.client.post(
            reverse("login"),
            {"username": "S2001", "password": "Student123!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("student_detail", args=[stu.sno]))

    def test_legacy_student_can_login_with_default_password(self):
        student.objects.create(sno="S2002", sname="学生2002", sex="girl", classno=self.cls)
        resp = self.client.post(
            reverse("login"),
            {"username": "S2002", "password": DEFAULT_STUDENT_PASSWORD},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("student_detail", args=["S2002"]))
        self.assertTrue(User.objects.filter(username="S2002").exists())


class UserManagementTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_user", role="admin")
        self.teacher = self.create_user("teacher_user", role="teacher")
        self.dep, self.cls, _ = self.create_school_base(dno="D011", classno="C011", cno="K11")

    def test_user_list_admin_only(self):
        self.assertTrue(self.client.login(username="admin_user", password=DEFAULT_PASSWORD))
        resp = self.client.get(reverse("user_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.context["roles"]), set(MANAGED_ROLES))
        self.client.logout()

        self.assertTrue(self.client.login(username="teacher_user", password=DEFAULT_PASSWORD))
        forbidden = self.client.get(reverse("user_list"))
        self.assertEqual(forbidden.status_code, 302)
        self.assertEqual(forbidden.url, "/")

    def test_user_create_teacher_success(self):
        self.assertTrue(self.client.login(username="admin_user", password=DEFAULT_PASSWORD))
        resp = self.client.post(
            reverse("user_add"),
            {
                "username": "new_teacher",
                "nickname": "新教师",
                "password1": "Teacher123!",
                "password2": "Teacher123!",
                "groups": ["teacher"],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("user_list"))
        self.assertTrue(User.objects.filter(username="new_teacher").exists())
        self.assertTrue(User.objects.get(username="new_teacher").groups.filter(name="teacher").exists())

    def test_user_create_student_requires_profile(self):
        self.assertTrue(self.client.login(username="admin_user", password=DEFAULT_PASSWORD))
        resp = self.client.post(
            reverse("user_add"),
            {
                "username": "S3001",
                "nickname": "学生",
                "password1": "AnyPass123!",
                "password2": "AnyPass123!",
                "groups": ["student"],
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="S3001").exists())

    def test_user_create_student_profile_and_default_password(self):
        self.assertTrue(self.client.login(username="admin_user", password=DEFAULT_PASSWORD))
        resp = self.client.post(
            reverse("user_add"),
            {
                "username": "S3002",
                "nickname": "学生3002",
                "password1": "Ignored123!",
                "password2": "Ignored123!",
                "groups": ["student"],
                "create_student": "on",
                "sname": "学生3002",
                "sex": "boy",
                "classno": self.cls.classno,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("user_list"))
        self.client.logout()
        self.assertTrue(self.client.login(username="S3002", password=DEFAULT_STUDENT_PASSWORD))

    def test_user_edit_promote_pending_to_student_sets_default_password(self):
        pending = self.create_user("S3003", role=None, password="OldPass123!")
        self.assertTrue(self.client.login(username="admin_user", password=DEFAULT_PASSWORD))
        resp = self.client.post(
            reverse("user_edit", args=[pending.id]),
            {
                "nickname": "升级学生",
                "groups": ["student"],
                "create_student": "on",
                "sname": "升级学生",
                "sex": "girl",
                "classno": self.cls.classno,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("user_list"))

        pending.refresh_from_db()
        self.assertTrue(pending.groups.filter(name="student").exists())
        self.client.logout()
        self.assertFalse(self.client.login(username="S3003", password="OldPass123!"))
        self.assertTrue(self.client.login(username="S3003", password=DEFAULT_STUDENT_PASSWORD))


class StudentManagementTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_stu", role="admin")
        self.teacher = self.create_user("teacher_stu", role="teacher")
        self.dep, self.cls, self.course1 = self.create_school_base(dno="D021", classno="C021", cno="K21")
        self.stu_user = self.create_user("S2101", role="student")
        self.stu = student.objects.create(
            sno="S2101",
            user=self.stu_user,
            sname="学生2101",
            sex="boy",
            classno=self.cls,
        )

    def test_student_add_edit_delete(self):
        self.assertTrue(self.client.login(username="admin_stu", password=DEFAULT_PASSWORD))
        add_resp = self.client.post(
            reverse("student_add"),
            {
                "sno": "S2102",
                "sname": "学生2102",
                "sex": "girl",
                "native": "北京",
                "age": "20",
                "classno": self.cls.classno,
                "semester": "2",
                "home": "海淀",
                "telephone": "13800000000",
            },
        )
        self.assertEqual(add_resp.status_code, 302)
        self.assertTrue(student.objects.filter(sno="S2102").exists())
        self.assertTrue(User.objects.filter(username="S2102").exists())

        edit_resp = self.client.post(
            reverse("student_edit", args=["S2102"]),
            {
                "sname": "学生2102改",
                "sex": "boy",
                "native": "上海",
                "age": "21",
                "classno": self.cls.classno,
                "semester": "3",
                "home": "浦东",
                "telephone": "13900000000",
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        self.assertEqual(student.objects.get(sno="S2102").sname, "学生2102改")

        delete_resp = self.client.post(reverse("student_delete", args=["S2102"]))
        self.assertEqual(delete_resp.status_code, 302)
        self.assertFalse(student.objects.filter(sno="S2102").exists())

    def test_student_delete_clears_student_role(self):
        self.assertTrue(self.client.login(username="admin_stu", password=DEFAULT_PASSWORD))
        delete_resp = self.client.post(reverse("student_delete", args=[self.stu.sno]))
        self.assertEqual(delete_resp.status_code, 302)
        self.assertFalse(student.objects.filter(sno=self.stu.sno).exists())
        self.stu_user.refresh_from_db()
        self.assertFalse(self.stu_user.groups.filter(name="student").exists())

    def test_student_list_teacher_can_access(self):
        self.assertTrue(self.client.login(username="teacher_stu", password=DEFAULT_PASSWORD))
        resp = self.client.get(reverse("student_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "S2101")

    def test_student_detail_and_course_self_only(self):
        other_user = self.create_user("S2199", role="student")
        other = student.objects.create(sno="S2199", user=other_user, sname="学生2199", sex="girl", classno=self.cls)
        self.assertTrue(self.client.login(username="S2101", password=DEFAULT_PASSWORD))

        own_detail = self.client.get(reverse("student_detail", args=[self.stu.sno]))
        self.assertEqual(own_detail.status_code, 200)

        forbidden_detail = self.client.get(reverse("student_detail", args=[other.sno]))
        self.assertEqual(forbidden_detail.status_code, 302)
        self.assertEqual(forbidden_detail.url, "/")

        forbidden_course = self.client.get(reverse("student_course", args=[other.sno]))
        self.assertEqual(forbidden_course.status_code, 302)
        self.assertEqual(forbidden_course.url, "/")

    def test_student_import_excel_success(self):
        self.assertTrue(self.client.login(username="admin_stu", password=DEFAULT_PASSWORD))
        upload = self.build_student_excel_file(
            rows=[
                ["S2110", "导入学生A", "boy", "北京", 20, self.cls.classno, 1, "海淀", "13800000001"],
                ["S2111", "导入学生B", "girl", "上海", 19, self.cls.classno, 1, "浦东", "13800000002"],
            ]
        )
        resp = self.client.post(reverse("student_import_excel"), {"file": upload})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("student_list"))
        self.assertTrue(student.objects.filter(sno="S2110").exists())
        self.assertTrue(User.objects.filter(username="S2111").exists())

    def test_student_import_excel_invalid_header_rejected(self):
        self.assertTrue(self.client.login(username="admin_stu", password=DEFAULT_PASSWORD))
        upload = self.build_student_excel_file(
            rows=[["S2112", "坏表头学生"]],
            headers=["bad1", "bad2"],
        )
        resp = self.client.post(reverse("student_import_excel"), {"file": upload})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("student_import_excel"))
        self.assertFalse(student.objects.filter(sno="S2112").exists())

    def test_student_export_excel_download(self):
        self.assertTrue(self.client.login(username="admin_stu", password=DEFAULT_PASSWORD))
        resp = self.client.get(reverse("student_export_excel"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resp["Content-Type"],
        )
        self.assertIn("attachment;", resp["Content-Disposition"])


class AcademicCrudAndPermissionTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_acad", role="admin")
        self.teacher = self.create_user("teacher_acad", role="teacher")
        self.dep, self.cls, self.crs = self.create_school_base(dno="D031", classno="C031", cno="K31")

    def test_depart_crud(self):
        self.assertTrue(self.client.login(username="admin_acad", password=DEFAULT_PASSWORD))

        add = self.client.post(reverse("depart_add"), {"dno": "D032", "dname": "新系", "telephone": "8888"})
        self.assertEqual(add.status_code, 302)
        self.assertTrue(depart.objects.filter(dno="D032").exists())

        edit = self.client.post(reverse("depart_edit", args=["D032"]), {"dname": "新系改", "telephone": "9999"})
        self.assertEqual(edit.status_code, 302)
        self.assertEqual(depart.objects.get(dno="D032").dname, "新系改")

        get_delete = self.client.get(reverse("depart_delete", args=["D032"]))
        self.assertEqual(get_delete.status_code, 405)
        post_delete = self.client.post(reverse("depart_delete", args=["D032"]))
        self.assertEqual(post_delete.status_code, 302)
        self.assertFalse(depart.objects.filter(dno="D032").exists())

    def test_class_crud(self):
        self.assertTrue(self.client.login(username="admin_acad", password=DEFAULT_PASSWORD))

        add = self.client.post(
            reverse("class_add"),
            {"classno": "C032", "classname": "新班", "dno": self.dep.dno},
        )
        self.assertEqual(add.status_code, 302)
        self.assertTrue(cl.objects.filter(classno="C032").exists())

        edit = self.client.post(
            reverse("class_edit", args=["C032"]),
            {"classname": "新班改", "dno": self.dep.dno},
        )
        self.assertEqual(edit.status_code, 302)
        self.assertEqual(cl.objects.get(classno="C032").classname, "新班改")

        self.assertEqual(self.client.get(reverse("class_delete", args=["C032"])).status_code, 405)
        self.assertEqual(self.client.post(reverse("class_delete", args=["C032"])).status_code, 302)
        self.assertFalse(cl.objects.filter(classno="C032").exists())

    def test_course_crud_and_course_students_page(self):
        self.assertTrue(self.client.login(username="admin_acad", password=DEFAULT_PASSWORD))
        add = self.client.post(
            reverse("course_add"),
            {"cno": "K32", "cname": "新课程", "lecture": "32", "semester": "2", "credit": "3", "type": "spc"},
        )
        self.assertEqual(add.status_code, 302)
        self.assertTrue(course.objects.filter(cno="K32").exists())

        edit = self.client.post(
            reverse("course_edit", args=["K32"]),
            {"cname": "新课程改", "lecture": "48", "semester": "3", "credit": "4", "type": "bcim"},
        )
        self.assertEqual(edit.status_code, 302)
        self.assertEqual(course.objects.get(cno="K32").cname, "新课程改")

        stu_user = self.create_user("S3201", role="student")
        stu = student.objects.create(sno="S3201", user=stu_user, sname="学生3201", sex="boy", classno=self.cls)
        sc.objects.create(sno=stu, cno=course.objects.get(cno="K32"))
        students_resp = self.client.get(reverse("course_students", args=["K32"]))
        self.assertEqual(students_resp.status_code, 200)
        self.assertContains(
            students_resp,
            reverse("update_grade", args=[stu.sno, "K32"]),
        )

        self.assertEqual(self.client.get(reverse("course_delete", args=["K32"])).status_code, 405)
        self.assertEqual(self.client.post(reverse("course_delete", args=["K32"])).status_code, 302)
        self.assertFalse(course.objects.filter(cno="K32").exists())

    def test_teacher_can_view_lists_but_cannot_mutate(self):
        self.assertTrue(self.client.login(username="teacher_acad", password=DEFAULT_PASSWORD))
        self.assertEqual(self.client.get(reverse("class_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("depart_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("course_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("class_add")).status_code, 302)
        self.assertEqual(self.client.get(reverse("depart_add")).status_code, 302)
        self.assertEqual(self.client.get(reverse("course_add")).status_code, 302)


class SelectionAndGradeTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_sel", role="admin")
        self.teacher = self.create_user("teacher_sel", role="teacher")
        self.dep, self.cls, self.crs = self.create_school_base(dno="D041", classno="C041", cno="K41")
        self.stu_user = self.create_user("S4101", role="student")
        self.stu = student.objects.create(
            sno="S4101",
            user=self.stu_user,
            sname="学生4101",
            sex="boy",
            classno=self.cls,
        )

    def test_select_course_get_post_and_duplicate_guard(self):
        self.assertTrue(self.client.login(username="teacher_sel", password=DEFAULT_PASSWORD))
        get_resp = self.client.get(reverse("select_course", args=[self.stu.sno]))
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, self.crs.cname)

        post_resp = self.client.post(reverse("select_course", args=[self.stu.sno]), {"cno": self.crs.cno})
        self.assertEqual(post_resp.status_code, 302)
        self.assertEqual(post_resp.url, reverse("student_course", args=[self.stu.sno]))
        self.assertEqual(sc.objects.filter(sno=self.stu, cno=self.crs).count(), 1)

        dup_resp = self.client.post(reverse("select_course", args=[self.stu.sno]), {"cno": self.crs.cno})
        self.assertEqual(dup_resp.status_code, 302)
        self.assertEqual(sc.objects.filter(sno=self.stu, cno=self.crs).count(), 1)

    def test_student_course_page_and_update_grade(self):
        record = sc.objects.create(sno=self.stu, cno=self.crs)
        self.assertTrue(self.client.login(username="teacher_sel", password=DEFAULT_PASSWORD))

        course_resp = self.client.get(reverse("student_course", args=[self.stu.sno]))
        self.assertEqual(course_resp.status_code, 200)

        grade_get = self.client.get(reverse("update_grade", args=[self.stu.sno, self.crs.cno]))
        self.assertEqual(grade_get.status_code, 200)

        grade_post = self.client.post(reverse("update_grade", args=[self.stu.sno, self.crs.cno]), {"grade": "88.5"})
        self.assertEqual(grade_post.status_code, 302)
        self.assertEqual(grade_post.url, reverse("student_course", args=[self.stu.sno]))
        record.refresh_from_db()
        self.assertEqual(record.grade, 88.5)

    def test_update_grade_validation(self):
        sc.objects.create(sno=self.stu, cno=self.crs)
        self.assertTrue(self.client.login(username="teacher_sel", password=DEFAULT_PASSWORD))

        bad_num = self.client.post(reverse("update_grade", args=[self.stu.sno, self.crs.cno]), {"grade": "abc"})
        self.assertEqual(bad_num.status_code, 200)

        bad_range = self.client.post(reverse("update_grade", args=[self.stu.sno, self.crs.cno]), {"grade": "101"})
        self.assertEqual(bad_range.status_code, 200)

    def test_sc_unique_constraint_blocks_duplicates(self):
        sc.objects.create(sno=self.stu, cno=self.crs)
        with self.assertRaises(IntegrityError):
            sc.objects.create(sno=self.stu, cno=self.crs)


class FormPageSmokeTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_form", role="admin")
        self.dep, self.cls, self.crs = self.create_school_base(dno="D045", classno="C045", cno="K45")
        self.user_to_edit = self.create_user("edit_target", role="teacher")
        self.stu_user = self.create_user("S4501", role="student")
        self.stu = student.objects.create(
            sno="S4501",
            user=self.stu_user,
            sname="学生4501",
            sex="boy",
            classno=self.cls,
        )
        self.record = sc.objects.create(sno=self.stu, cno=self.crs, grade=None)

    def test_admin_can_open_all_form_pages(self):
        self.assertTrue(self.client.login(username="admin_form", password=DEFAULT_PASSWORD))
        targets = [
            reverse("user_add"),
            reverse("user_edit", args=[self.user_to_edit.id]),
            reverse("student_add"),
            reverse("student_edit", args=[self.stu.sno]),
            reverse("student_import_excel"),
            reverse("class_add"),
            reverse("class_edit", args=[self.cls.classno]),
            reverse("depart_add"),
            reverse("depart_edit", args=[self.dep.dno]),
            reverse("course_add"),
            reverse("course_edit", args=[self.crs.cno]),
            reverse("select_course", args=[self.stu.sno]),
            reverse("update_grade", args=[self.stu.sno, self.crs.cno]),
        ]
        for url in targets:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class DashboardAuditAndChatTests(BaseTestCase):
    def setUp(self):
        self.admin = self.create_user("admin_misc", role="admin")
        self.teacher = self.create_user("teacher_misc", role="teacher")
        self.dep, self.cls, self.crs = self.create_school_base(dno="D051", classno="C051", cno="K51")
        self.stu_user = self.create_user("S5101", role="student")
        self.stu = student.objects.create(
            sno="S5101",
            user=self.stu_user,
            sname="学生5101",
            sex="girl",
            classno=self.cls,
        )
        self.record = sc.objects.create(sno=self.stu, cno=self.crs, grade=90)

    def test_dashboard_for_admin_and_student(self):
        self.assertTrue(self.client.login(username="admin_misc", password=DEFAULT_PASSWORD))
        admin_dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(admin_dashboard.status_code, 200)
        self.assertIn("student_total", admin_dashboard.context)
        self.client.logout()

        self.assertTrue(self.client.login(username="S5101", password=DEFAULT_PASSWORD))
        student_dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(student_dashboard.status_code, 200)
        self.assertEqual(student_dashboard.context["stu"].sno, self.stu.sno)

    def test_audit_list_admin_only_and_filter(self):
        self.assertTrue(self.client.login(username="admin_misc", password=DEFAULT_PASSWORD))
        self.client.post(reverse("depart_add"), {"dno": "D059", "dname": "审计系", "telephone": "1111"})
        self.assertTrue(AuditLog.objects.filter(action="create", model_name="depart").exists())

        filtered = self.client.get(reverse("audit_list"), {"action": "create"})
        self.assertEqual(filtered.status_code, 200)
        self.assertGreaterEqual(filtered.context["logs"].count(), 1)
        self.client.logout()

        self.assertTrue(self.client.login(username="teacher_misc", password=DEFAULT_PASSWORD))
        denied = self.client.get(reverse("audit_list"))
        self.assertEqual(denied.status_code, 302)
        self.assertEqual(denied.url, "/")

    def test_chat_permissions_and_clear(self):
        self.assertTrue(self.client.login(username="S5101", password=DEFAULT_PASSWORD))
        denied = self.client.get(reverse("chat"))
        self.assertEqual(denied.status_code, 302)
        self.assertEqual(denied.url, reverse("dashboard"))
        self.client.logout()

        self.assertTrue(self.client.login(username="teacher_misc", password=DEFAULT_PASSWORD))
        clear_resp = self.client.get(f"{reverse('chat')}?clear=1")
        self.assertEqual(clear_resp.status_code, 302)
        self.assertEqual(clear_resp.url, reverse("chat"))
        self.assertEqual(len(self.client.session["chat_messages"]), 2)

    @patch("xx.views_misc.get_ai_response")
    def test_chat_post_with_mocked_ai(self, mocked_ai):
        mocked_ai.return_value = "```python\nresult = list(student.objects.values('sno'))\n```"
        self.assertTrue(self.client.login(username="teacher_misc", password=DEFAULT_PASSWORD))

        resp = self.client.post(reverse("chat"), {"message": "查询学生"})
        self.assertEqual(resp.status_code, 200)
        messages = self.client.session.get("chat_messages", [])
        self.assertGreaterEqual(len(messages), 2)
        self.assertEqual(messages[-1]["role"], "assistant")
