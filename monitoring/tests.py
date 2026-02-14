"""
Tests for monitoring app: dashboard and map require login.
"""
from django.test import TestCase, Client
from django.urls import reverse


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
