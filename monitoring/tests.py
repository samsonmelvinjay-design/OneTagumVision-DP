"""
Tests for monitoring app: dashboard and map require login.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from decimal import Decimal
from projeng.models import Project, ProjectCost, Notification


class DashboardAccessTest(TestCase):
    """Dashboard and map redirect anonymous users to login."""

    def setUp(self):
        self.client = Client()

    def _final_url(self, response):
        if response.redirect_chain:
            return response.redirect_chain[-1][0]
        return ''

    def test_dashboard_anonymous_redirects_to_login(self):
        response = self.client.get('/dashboard/', follow=True)
        self.assertIn('login', self._final_url(response), msg='Anonymous should end at login')

    def test_map_anonymous_redirects_to_login(self):
        response = self.client.get('/dashboard/map/', follow=True)
        self.assertIn('login', self._final_url(response), msg='Anonymous should end at login')

    def test_project_list_anonymous_redirects_to_login(self):
        response = self.client.get('/dashboard/projects/', follow=True)
        self.assertIn('login', self._final_url(response), msg='Anonymous should end at login')


class FinanceManagerModulesTest(TestCase):
    """Smoke/regression tests for finance manager pages and data wiring."""

    def setUp(self):
        self.client = Client(HTTP_HOST='127.0.0.1')
        user_model = get_user_model()

        self.finance_user = user_model.objects.create_user(
            username='fm_test',
            password='fm_test_password',
            email='fm_test@example.com',
        )
        finance_group, _ = Group.objects.get_or_create(name='Finance Manager')
        self.finance_user.groups.add(finance_group)

        self.project = Project.objects.create(
            prn='FM-TEST-001',
            name='Finance Manager Test Project',
            barangay='Apokon',
            project_cost=Decimal('1000000.00'),
            status='in_progress',
            created_by=self.finance_user,
        )
        ProjectCost.objects.create(
            project=self.project,
            date='2026-03-01',
            cost_type='labor',
            description='Initial labor allocation',
            amount=Decimal('250000.00'),
            created_by=self.finance_user,
        )
        Notification.objects.create(
            recipient=self.finance_user,
            message='Budget Review Request: FM test project',
        )

        self.client.force_login(self.finance_user)

    def test_finance_pages_render(self):
        page_names = [
            'finance_dashboard',
            'finance_projects',
            'finance_cost_management',
            'finance_reports',
            'finance_notifications',
            'finance_project_detail',
        ]
        for name in page_names:
            if name == 'finance_project_detail':
                response = self.client.get(reverse(name, args=[self.project.id]), secure=True)
            else:
                response = self.client.get(reverse(name), secure=True)
            self.assertEqual(response.status_code, 200, msg=f'{name} should render for finance manager')

    def test_finance_cost_management_includes_drawer_data(self):
        response = self.client.get(reverse('finance_cost_management'), secure=True)
        self.assertEqual(response.status_code, 200)
        drawer_data = response.context['project_drawer_data']
        self.assertIn(str(self.project.id), drawer_data)
        self.assertEqual(drawer_data[str(self.project.id)]['name'], self.project.name)

    def test_finance_cost_management_add_cost_entry_post(self):
        before_count = ProjectCost.objects.filter(project=self.project).count()
        response = self.client.post(
            reverse('finance_cost_management'),
            {
                'action': 'add_cost_entry',
                'project_id': self.project.id,
                'cost_type': 'material',
                'amount': '10000.50',
                'date': '2026-03-02',
                'description': 'Test material entry',
                'next': reverse('finance_cost_management'),
            },
            secure=True,
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ProjectCost.objects.filter(project=self.project).count(),
            before_count + 1,
            msg='Cost entry POST from finance drawer should save successfully.',
        )

    def test_finance_reports_over_budget_filter_is_valid(self):
        response = self.client.get(reverse('finance_reports'), secure=True)
        self.assertContains(response, 'data-budget-status="over"')
