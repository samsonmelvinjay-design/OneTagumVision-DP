"""
Tests for core gistagum app: health check and root redirect.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class HealthCheckTest(TestCase):
    """Health check endpoint for load balancers / monitoring."""

    def setUp(self):
        self.client = Client()

    def test_health_returns_200(self):
        response = self.client.get('/health/', follow=True)
        self.assertEqual(response.status_code, 200)

    def test_health_returns_plain_text(self):
        response = self.client.get('/health/', follow=True)
        self.assertEqual(response.get('Content-Type', '').split(';')[0].strip(), 'text/plain')

    def test_health_returns_ok_body(self):
        response = self.client.get('/health/', follow=True)
        self.assertEqual(response.content.decode(), 'OK')


class RedirectToLoginTest(TestCase):
    """Root URL redirects: anonymous -> login, authenticated -> dashboard."""

    def setUp(self):
        self.client = Client()

    def _final_url(self, response):
        """Get the final URL after following redirects."""
        if response.redirect_chain:
            return response.redirect_chain[-1][0]
        return getattr(response, 'request', None) and getattr(response.request, 'path', None) or ''

    def test_anonymous_redirects_to_login(self):
        response = self.client.get('/', follow=True)
        self.assertIn('login', self._final_url(response), msg='Anonymous user should end at login')

    def test_authenticated_head_engineer_redirects_to_dashboard(self):
        user = User.objects.create_user(username='head1', password='testpass')
        from django.contrib.auth.models import Group
        g, _ = Group.objects.get_or_create(name='Head Engineer')
        user.groups.add(g)
        self.client.login(username='head1', password='testpass')
        response = self.client.get('/', follow=True)
        self.assertIn('/dashboard/', self._final_url(response), msg='Head Engineer should end at dashboard')

    def test_authenticated_project_engineer_redirects_to_projeng_dashboard(self):
        user = User.objects.create_user(username='eng1', password='testpass')
        from django.contrib.auth.models import Group
        g, _ = Group.objects.get_or_create(name='Project Engineer')
        user.groups.add(g)
        self.client.login(username='eng1', password='testpass')
        response = self.client.get('/', follow=True)
        self.assertIn('/projeng/dashboard/', self._final_url(response), msg='Project Engineer should end at projeng dashboard')
