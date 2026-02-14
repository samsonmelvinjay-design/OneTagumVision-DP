"""
Tests for projeng app: engineer projects API and Project model.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from projeng.models import Project


class EngineerProjectsApiTest(TestCase):
    """Engineer projects API returns JSON with projects and status_counts."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='testpass')
        self.client.login(username='apiuser', password='testpass')

    def test_engineer_projects_api_returns_200_when_logged_in(self):
        response = self.client.get('/api/engineer-projects/999/', follow=True)  # no such engineer -> empty list
        self.assertEqual(response.status_code, 200)

    def test_engineer_projects_api_returns_json(self):
        response = self.client.get('/api/engineer-projects/999/', follow=True)
        self.assertEqual(response.get('Content-Type', '').split(';')[0].strip(), 'application/json')

    def test_engineer_projects_api_structure(self):
        response = self.client.get('/api/engineer-projects/999/', follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertIn('projects', data)
        self.assertIn('status_counts', data)
        self.assertIsInstance(data['projects'], list)
        self.assertIsInstance(data['status_counts'], dict)

    def test_engineer_projects_api_anonymous_redirects_to_login(self):
        client = Client()
        response = client.get('/api/engineer-projects/1/', follow=True)
        final_url = response.redirect_chain[-1][0] if response.redirect_chain else ''
        self.assertIn('login', final_url, msg='Anonymous should end at login')


class ProjectModelTest(TestCase):
    """Basic Project model create/save."""

    def test_create_project_minimal(self):
        user = User.objects.create_user(username='creator', password='testpass')
        project = Project(
            name='Test Road Project',
            created_by=user,
        )
        project.save()
        self.assertIsNotNone(project.pk)
        self.assertEqual(project.name, 'Test Road Project')
        self.assertEqual(project.status, 'planned')
        self.assertTrue(project.prn is not None and project.prn.startswith('PRN-'))
