# 🎯 Hybrid Algorithm Implementation Plan
## Administrative Spatial Analysis + GEO-RBAC for ONETAGUMVISION

---

## 📋 Overview

This plan outlines the step-by-step implementation of the hybrid spatial clustering algorithm combining:
- **Administrative Spatial Analysis** (for governance-aligned clustering)
- **GEO-RBAC** (for location-based access control)

---

## 🎯 Goals

1. **Cluster projects** by administrative boundaries (barangays/districts)
2. **Enforce spatial access control** - users can only access projects in their assigned zones
3. **Maintain governance alignment** - all clustering respects official administrative boundaries
4. **Support analytics** - provide clustering metrics (Silhouette Score, Zoning Alignment Score)

---

## 📊 Current State Analysis

### ✅ What We Have:
- Projects with `barangay`, `latitude`, `longitude` fields
- `BarangayMetadata` model for administrative zone data
- `ZoningZone` model for detailed zoning classifications
- Role-based access control (`Head Engineer`, `Project Engineer`, `Finance Manager`)
- Basic barangay filtering in views

### ❌ What We Need:
- Spatial clustering algorithm implementation
- Location-based access control (GEO-RBAC)
- User-to-barangay assignment system
- Clustering metrics calculation
- API endpoints for clustering operations
- Visualization of clusters

---

## 🏗️ Implementation Phases

### **Phase 1: Database Schema Extensions** (Week 1)

#### 1.1 Create User Spatial Assignment Model
**File:** `projeng/models.py`

```python
class UserSpatialAssignment(models.Model):
    """Links users to specific administrative zones (GEO-RBAC)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='spatial_assignment')
    
    # Administrative boundaries
    assigned_barangays = models.ManyToManyField(
        'BarangayMetadata',
        related_name='assigned_users',
        blank=True,
        help_text="Barangays this user can access"
    )
    
    # Spatial role type
    SPATIAL_ROLE_CHOICES = [
        ('city_wide', 'City-Wide Access'),
        ('district', 'District Access'),
        ('barangay', 'Barangay Access'),
        ('project_specific', 'Project-Specific Access'),
    ]
    spatial_role = models.CharField(
        max_length=20,
        choices=SPATIAL_ROLE_CHOICES,
        default='barangay',
        help_text="Type of spatial access role"
    )
    
    # Additional spatial constraints
    allowed_zones = models.ManyToManyField(
        'ZoningZone',
        related_name='allowed_users',
        blank=True,
        help_text="Specific zoning zones user can access"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Spatial Assignment"
        verbose_name_plural = "User Spatial Assignments"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_spatial_role_display()}"
```

#### 1.2 Create Project Cluster Model
**File:** `projeng/models.py`

```python
class ProjectCluster(models.Model):
    """Represents a cluster of projects based on administrative boundaries"""
    
    # Cluster identification
    cluster_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255, help_text="Human-readable cluster name")
    
    # Administrative boundary
    barangay = models.ForeignKey(
        'BarangayMetadata',
        on_delete=models.CASCADE,
        related_name='clusters',
        null=True,
        blank=True
    )
    
    # Cluster metadata
    cluster_type = models.CharField(
        max_length=50,
        choices=[
            ('administrative', 'Administrative Boundary'),
            ('zoning', 'Zoning-Based'),
            ('hybrid', 'Hybrid (Admin + Zoning)'),
        ],
        default='administrative'
    )
    
    # Clustering metrics
    silhouette_score = models.FloatField(null=True, blank=True, help_text="Silhouette Score (-1 to 1)")
    zoning_alignment_score = models.FloatField(null=True, blank=True, help_text="Zoning Alignment Score (0 to 1)")
    
    # Projects in this cluster
    projects = models.ManyToManyField(
        'Project',
        related_name='clusters',
        blank=True
    )
    
    # Statistics
    project_count = models.IntegerField(default=0)
    total_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['barangay__name', 'name']
        indexes = [
            models.Index(fields=['cluster_id']),
            models.Index(fields=['barangay', 'cluster_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.project_count} projects)"
```

#### 1.3 Migration
```bash
python manage.py makemigrations projeng
python manage.py migrate
```

---

### **Phase 2: Core Algorithm Implementation** (Week 2)

#### 2.1 Create Clustering Module
**File:** `projeng/spatial_clustering.py`

```python
"""
Spatial Clustering Algorithms for ONETAGUMVISION
Implements Administrative Spatial Analysis + GEO-RBAC hybrid approach
"""

from django.db.models import Q, Count, Sum
from django.contrib.gis.geos import Point
from sklearn.metrics import silhouette_score
import numpy as np
from typing import List, Dict, Tuple
from .models import Project, BarangayMetadata, ZoningZone, ProjectCluster


class AdministrativeSpatialAnalysis:
    """Groups projects based on official administrative boundaries"""
    
    @staticmethod
    def cluster_by_barangay(projects: List[Project]) -> Dict[str, List[Project]]:
        """
        Cluster projects by barangay (Administrative Spatial Analysis)
        
        Returns:
            Dict mapping barangay names to list of projects
        """
        clusters = {}
        for project in projects:
            barangay = project.barangay or "Unassigned"
            if barangay not in clusters:
                clusters[barangay] = []
            clusters[barangay].append(project)
        return clusters
    
    @staticmethod
    def calculate_silhouette_score(clusters: Dict[str, List[Project]]) -> float:
        """
        Calculate Silhouette Score for administrative clusters
        
        Formula: s(i) = (b(i) - a(i)) / max{a(i), b(i)}
        """
        if len(clusters) < 2:
            return 0.0
        
        # Prepare data points
        points = []
        labels = []
        
        for barangay, projects in clusters.items():
            for project in projects:
                if project.latitude and project.longitude:
                    points.append([project.latitude, project.longitude])
                    labels.append(barangay)
        
        if len(points) < 2:
            return 0.0
        
        # Calculate intra-cluster and inter-cluster distances
        points = np.array(points)
        labels = np.array(labels)
        
        try:
            score = silhouette_score(points, labels, metric='euclidean')
            return float(score)
        except:
            return 0.0
    
    @staticmethod
    def calculate_zoning_alignment_score(
        cluster: List[Project],
        barangay: BarangayMetadata
    ) -> float:
        """
        Calculate Zoning Alignment Score
        
        Formula: ZAS = |C ∩ Z| / |C ∪ Z|
        Where C = cluster projects, Z = official barangay boundary
        """
        if not cluster or not barangay:
            return 0.0
        
        # Projects in cluster that match barangay
        matching_projects = sum(1 for p in cluster if p.barangay == barangay.name)
        total_projects = len(cluster)
        
        if total_projects == 0:
            return 0.0
        
        # Simplified ZAS: ratio of projects correctly assigned to barangay
        return matching_projects / total_projects


class GeoRBAC:
    """Geographic Role-Based Access Control"""
    
    @staticmethod
    def get_user_accessible_barangays(user) -> List[str]:
        """Get list of barangay names user can access"""
        try:
            assignment = user.spatial_assignment
            if assignment.spatial_role == 'city_wide':
                # Return all barangays
                return list(BarangayMetadata.objects.values_list('name', flat=True))
            elif assignment.spatial_role == 'barangay':
                return list(assignment.assigned_barangays.values_list('name', flat=True))
            else:
                return list(assignment.assigned_barangays.values_list('name', flat=True))
        except:
            # Default: no access (or all access for Head Engineers)
            if user.groups.filter(name='Head Engineer').exists():
                return list(BarangayMetadata.objects.values_list('name', flat=True))
            return []
    
    @staticmethod
    def filter_projects_by_spatial_access(user, queryset) -> QuerySet:
        """Filter projects based on user's spatial assignment"""
        accessible_barangays = GeoRBAC.get_user_accessible_barangays(user)
        
        if not accessible_barangays:
            return queryset.none()
        
        return queryset.filter(barangay__in=accessible_barangays)
    
    @staticmethod
    def can_access_project(user, project: Project) -> bool:
        """Check if user can access a specific project"""
        accessible_barangays = GeoRBAC.get_user_accessible_barangays(user)
        
        # Head Engineers can access all
        if user.groups.filter(name='Head Engineer').exists():
            return True
        
        # Check if project's barangay is in accessible list
        return project.barangay in accessible_barangays


class HybridClusteringEngine:
    """Main engine combining Administrative Spatial Analysis + GEO-RBAC"""
    
    def __init__(self):
        self.admin_analysis = AdministrativeSpatialAnalysis()
        self.geo_rbac = GeoRBAC()
    
    def cluster_projects(
        self,
        projects: List[Project] = None,
        user: User = None
    ) -> Dict[str, any]:
        """
        Perform hybrid clustering on projects
        
        Args:
            projects: List of projects to cluster (if None, uses all)
            user: User for GEO-RBAC filtering (if None, uses all projects)
        
        Returns:
            Dict with clusters, metrics, and metadata
        """
        # Get projects
        if projects is None:
            projects = list(Project.objects.all())
        
        # Apply GEO-RBAC filtering
        if user:
            accessible_barangays = self.geo_rbac.get_user_accessible_barangays(user)
            projects = [p for p in projects if p.barangay in accessible_barangays]
        
        # Apply Administrative Spatial Analysis
        clusters = self.admin_analysis.cluster_by_barangay(projects)
        
        # Calculate metrics
        silhouette = self.admin_analysis.calculate_silhouette_score(clusters)
        
        # Calculate ZAS for each cluster
        cluster_metrics = {}
        for barangay_name, cluster_projects in clusters.items():
            try:
                barangay = BarangayMetadata.objects.get(name=barangay_name)
                zas = self.admin_analysis.calculate_zoning_alignment_score(
                    cluster_projects,
                    barangay
                )
                cluster_metrics[barangay_name] = {
                    'project_count': len(cluster_projects),
                    'zoning_alignment_score': zas,
                    'silhouette_score': silhouette,
                }
            except BarangayMetadata.DoesNotExist:
                cluster_metrics[barangay_name] = {
                    'project_count': len(cluster_projects),
                    'zoning_alignment_score': 0.0,
                    'silhouette_score': silhouette,
                }
        
        return {
            'clusters': clusters,
            'metrics': {
                'overall_silhouette_score': silhouette,
                'cluster_count': len(clusters),
                'total_projects': len(projects),
            },
            'cluster_metrics': cluster_metrics,
        }
    
    def save_clusters_to_database(
        self,
        clustering_result: Dict,
        cluster_type: str = 'administrative'
    ) -> List[ProjectCluster]:
        """Save clustering results to database"""
        saved_clusters = []
        
        for barangay_name, projects in clustering_result['clusters'].items():
            # Get or create cluster
            cluster_id = f"admin_{barangay_name.lower().replace(' ', '_')}"
            
            cluster, created = ProjectCluster.objects.get_or_create(
                cluster_id=cluster_id,
                defaults={
                    'name': f"{barangay_name} Cluster",
                    'cluster_type': cluster_type,
                    'silhouette_score': clustering_result['metrics']['overall_silhouette_score'],
                    'project_count': len(projects),
                }
            )
            
            # Update cluster
            if not created:
                cluster.silhouette_score = clustering_result['metrics']['overall_silhouette_score']
                cluster.project_count = len(projects)
                cluster.save()
            
            # Add projects to cluster
            cluster.projects.set(projects)
            
            # Set barangay if exists
            try:
                barangay = BarangayMetadata.objects.get(name=barangay_name)
                cluster.barangay = barangay
                cluster.zoning_alignment_score = clustering_result['cluster_metrics'].get(
                    barangay_name, {}
                ).get('zoning_alignment_score', 0.0)
                cluster.save()
            except BarangayMetadata.DoesNotExist:
                pass
            
            saved_clusters.append(cluster)
        
        return saved_clusters
```

---

### **Phase 3: Access Control Integration** (Week 2-3)

#### 3.1 Extend Access Control Module
**File:** `gistagum/access_control.py` (additions)

```python
from projeng.spatial_clustering import GeoRBAC

def spatial_access_required(view_func):
    """
    Decorator to enforce GEO-RBAC spatial access control
    Users can only access projects in their assigned administrative zones
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Head Engineers bypass spatial restrictions
        if is_head_engineer(request.user):
            return view_func(request, *args, **kwargs)
        
        # Check spatial access for project-specific views
        if 'project_id' in kwargs or 'pk' in kwargs:
            project_id = kwargs.get('project_id') or kwargs.get('pk')
            try:
                from projeng.models import Project
                project = Project.objects.get(pk=project_id)
                
                if not GeoRBAC.can_access_project(request.user, project):
                    messages.error(
                        request,
                        f"You don't have permission to access projects in {project.barangay}."
                    )
                    return redirect(get_user_dashboard_url(request.user))
            except Project.DoesNotExist:
                pass
        
        return view_func(request, *args, **kwargs)
    return wrapper
```

#### 3.2 Update Views with Spatial Filtering
**File:** `projeng/views.py` (example updates)

```python
from projeng.spatial_clustering import GeoRBAC, HybridClusteringEngine
from gistagum.access_control import spatial_access_required

@login_required
@spatial_access_required
def my_projects(request):
    """Project Engineer's projects - filtered by spatial access"""
    # Get base queryset
    projects = Project.objects.filter(assigned_engineers=request.user)
    
    # Apply GEO-RBAC filtering
    projects = GeoRBAC.filter_projects_by_spatial_access(request.user, projects)
    
    # ... rest of view logic
```

---

### **Phase 4: Management Commands** (Week 3)

#### 4.1 Create Clustering Command
**File:** `projeng/management/commands/cluster_projects.py`

```python
from django.core.management.base import BaseCommand
from projeng.spatial_clustering import HybridClusteringEngine
from projeng.models import Project


class Command(BaseCommand):
    help = 'Perform spatial clustering on all projects using hybrid algorithm'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save clusters to database',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='User ID to apply GEO-RBAC filtering',
        )
    
    def handle(self, *args, **options):
        engine = HybridClusteringEngine()
        
        # Get user if specified
        user = None
        if options['user']:
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(pk=options['user'])
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {options["user"]} not found'))
                return
        
        # Perform clustering
        self.stdout.write('Performing hybrid clustering...')
        result = engine.cluster_projects(user=user)
        
        # Display results
        self.stdout.write(self.style.SUCCESS(f'\nClustering Results:'))
        self.stdout.write(f'  Total Projects: {result["metrics"]["total_projects"]}')
        self.stdout.write(f'  Clusters: {result["metrics"]["cluster_count"]}')
        self.stdout.write(f'  Silhouette Score: {result["metrics"]["overall_silhouette_score"]:.3f}')
        
        self.stdout.write(f'\nCluster Details:')
        for barangay, metrics in result['cluster_metrics'].items():
            self.stdout.write(
                f'  {barangay}: {metrics["project_count"]} projects '
                f'(ZAS: {metrics["zoning_alignment_score"]:.3f})'
            )
        
        # Save to database if requested
        if options['save']:
            self.stdout.write('\nSaving clusters to database...')
            saved = engine.save_clusters_to_database(result)
            self.stdout.write(
                self.style.SUCCESS(f'  Saved {len(saved)} clusters')
            )
```

#### 4.2 Create User Assignment Command
**File:** `projeng/management/commands/assign_user_spatial_role.py`

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from projeng.models import UserSpatialAssignment, BarangayMetadata


class Command(BaseCommand):
    help = 'Assign spatial roles to users (GEO-RBAC)'
    
    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username')
        parser.add_argument('--role', type=str, choices=['city_wide', 'district', 'barangay', 'project_specific'], default='barangay')
        parser.add_argument('--barangays', nargs='+', help='List of barangay names')
    
    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {options["username"]} not found'))
            return
        
        # Get or create assignment
        assignment, created = UserSpatialAssignment.objects.get_or_create(user=user)
        assignment.spatial_role = options['role']
        
        # Assign barangays
        if options['barangays']:
            barangays = BarangayMetadata.objects.filter(name__in=options['barangays'])
            assignment.assigned_barangays.set(barangays)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Assigned {barangays.count()} barangays to {user.username}'
                )
            )
        
        assignment.save()
        self.stdout.write(
            self.style.SUCCESS(
                f'Updated spatial assignment for {user.username}'
            )
        )
```

---

### **Phase 5: API Endpoints** (Week 3-4)

#### 5.1 Create Clustering API
**File:** `projeng/api_views.py` (new file)

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from projeng.spatial_clustering import HybridClusteringEngine
from projeng.models import ProjectCluster


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_clusters(request):
    """API endpoint to get project clusters"""
    engine = HybridClusteringEngine()
    result = engine.cluster_projects(user=request.user)
    
    return Response({
        'clusters': {
            barangay: {
                'project_ids': [p.id for p in projects],
                'project_count': len(projects),
                'metrics': result['cluster_metrics'].get(barangay, {})
            }
            for barangay, projects in result['clusters'].items()
        },
        'overall_metrics': result['metrics']
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cluster_metrics(request):
    """API endpoint to get clustering performance metrics"""
    clusters = ProjectCluster.objects.all()
    
    return Response({
        'clusters': [
            {
                'id': c.cluster_id,
                'name': c.name,
                'barangay': c.barangay.name if c.barangay else None,
                'project_count': c.project_count,
                'silhouette_score': c.silhouette_score,
                'zoning_alignment_score': c.zoning_alignment_score,
            }
            for c in clusters
        ]
    })
```

#### 5.2 Add URL Routes
**File:** `projeng/urls.py` (additions)

```python
from .api_views import get_clusters, get_cluster_metrics

urlpatterns = [
    # ... existing patterns
    path('api/clusters/', get_clusters, name='api_clusters'),
    path('api/cluster-metrics/', get_cluster_metrics, name='api_cluster_metrics'),
]
```

---

### **Phase 6: Frontend Integration** (Week 4-5)

#### 6.1 Update Map View with Clusters
**File:** `templates/monitoring/map_choropleth.html` (additions)

```javascript
// Load clusters from API
async function loadClusters() {
    try {
        const response = await fetch('/projeng/api/clusters/');
        const data = await response.json();
        
        // Visualize clusters on map
        visualizeClusters(data.clusters);
    } catch (error) {
        console.error('Error loading clusters:', error);
    }
}

function visualizeClusters(clusters) {
    // Add cluster boundaries to map
    // Color-code by cluster
    // Show cluster metrics in popups
}
```

#### 6.2 Create Clustering Dashboard
**File:** `templates/monitoring/clustering_dashboard.html` (new file)

```html
<!-- Display cluster metrics, visualization, and controls -->
```

---

### **Phase 7: Testing & Validation** (Week 5-6)

#### 7.1 Unit Tests
**File:** `projeng/tests/test_spatial_clustering.py`

```python
from django.test import TestCase
from django.contrib.auth.models import User
from projeng.models import Project, BarangayMetadata, UserSpatialAssignment
from projeng.spatial_clustering import (
    AdministrativeSpatialAnalysis,
    GeoRBAC,
    HybridClusteringEngine
)


class SpatialClusteringTestCase(TestCase):
    def setUp(self):
        # Create test data
        pass
    
    def test_administrative_clustering(self):
        # Test barangay-based clustering
        pass
    
    def test_geo_rbac_filtering(self):
        # Test spatial access control
        pass
    
    def test_hybrid_clustering(self):
        # Test combined approach
        pass
    
    def test_silhouette_score_calculation(self):
        # Test metric calculation
        pass
```

#### 7.2 Integration Tests
- Test end-to-end clustering workflow
- Test access control enforcement
- Test API endpoints
- Test frontend visualization

---

## 📅 Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1** | Week 1 | Database schema, migrations |
| **Phase 2** | Week 2 | Core algorithm implementation |
| **Phase 3** | Week 2-3 | Access control integration |
| **Phase 4** | Week 3 | Management commands |
| **Phase 5** | Week 3-4 | API endpoints |
| **Phase 6** | Week 4-5 | Frontend integration |
| **Phase 7** | Week 5-6 | Testing & validation |

**Total Estimated Time: 6 weeks**

---

## 🔧 Dependencies

### Python Packages
```txt
scikit-learn>=1.0.0  # For Silhouette Score calculation
numpy>=1.21.0        # For numerical operations
```

Add to `requirements.txt`:
```bash
pip install scikit-learn numpy
```

---

## ✅ Success Criteria

1. ✅ Projects are clustered by administrative boundaries (barangays)
2. ✅ Users can only access projects in their assigned zones
3. ✅ Clustering metrics (Silhouette Score, ZAS) are calculated and stored
4. ✅ Clusters are visualized on the map
5. ✅ API endpoints provide cluster data
6. ✅ Management commands allow easy clustering operations
7. ✅ All tests pass

---

## 🚀 Quick Start Guide

### Step 1: Install Dependencies
```bash
pip install scikit-learn numpy
```

### Step 2: Run Migrations
```bash
python manage.py makemigrations projeng
python manage.py migrate
```

### Step 3: Assign Spatial Roles to Users
```bash
python manage.py assign_user_spatial_role username --role barangay --barangays "Barangay A" "Barangay B"
```

### Step 4: Perform Clustering
```bash
python manage.py cluster_projects --save
```

### Step 5: Test Access Control
- Log in as Project Engineer
- Verify they can only see projects in assigned barangays
- Verify Head Engineers can see all projects

---

## 📝 Notes

- **Performance**: For large datasets (>1000 projects), consider caching cluster results
- **Real-time Updates**: Clusters can be recalculated periodically or on-demand
- **Scalability**: Algorithm is designed to handle city-wide project datasets efficiently
- **Privacy**: GEO-RBAC ensures users only see data they're authorized to access

---

## 🔄 Future Enhancements

1. **Hierarchical Clustering**: Add multi-level clustering (city → district → barangay)
2. **Machine Learning**: Use ML to optimize cluster boundaries
3. **Real-time Clustering**: Auto-update clusters when projects are added/modified
4. **Advanced Metrics**: Add more clustering quality metrics
5. **Visualization**: Enhanced cluster visualization with heatmaps and boundaries

---

**Ready to implement? Start with Phase 1!** 🎯

