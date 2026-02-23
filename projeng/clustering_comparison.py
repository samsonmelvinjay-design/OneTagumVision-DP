"""
Spatial Clustering Algorithm Comparison Module
Compares Administrative Spatial Analysis, K-Means, DBSCAN, and Hierarchical Clustering
"""

import time
from typing import Dict, List, Tuple, Optional

from django.db.models import Q
from .models import Project, BarangayMetadata

try:
    import numpy as np
    import pandas as pd
    from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
    from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
    from sklearn.preprocessing import StandardScaler
    HAS_ML = True
except ImportError:
    HAS_ML = False
    np = None  # type: ignore
    pd = None  # type: ignore


class AdministrativeSpatialAnalysis:
    """Groups projects based on official administrative boundaries (barangays)"""
    
    @staticmethod
    def cluster_projects(projects: List[Project]) -> Tuple[Dict[str, List[Project]], np.ndarray]:
        """
        Cluster projects by barangay
        
        Returns:
            Tuple of (clusters_dict, labels_array)
        """
        clusters = {}
        labels = []
        
        for idx, project in enumerate(projects):
            barangay = project.barangay or "Unassigned"
            if barangay not in clusters:
                clusters[barangay] = []
            clusters[barangay].append(project)
            labels.append(barangay)
        
        # Convert labels to numeric for metrics
        unique_labels = list(clusters.keys())
        label_map = {label: idx for idx, label in enumerate(unique_labels)}
        numeric_labels = np.array([label_map[label] for label in labels])
        
        return clusters, numeric_labels
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "Administrative Spatial Analysis"


class KMeansClustering:
    """K-Means clustering algorithm"""
    
    def __init__(self, n_clusters: Optional[int] = None):
        self.n_clusters = n_clusters
        self.scaler = StandardScaler()
    
    def cluster_projects(self, projects: List[Project]) -> Tuple[Dict[str, List[Project]], np.ndarray]:
        """
        Cluster projects using K-Means
        
        Returns:
            Tuple of (clusters_dict, labels_array)
        """
        # Prepare data points
        points = []
        valid_projects = []
        
        for project in projects:
            if project.latitude and project.longitude:
                points.append([project.latitude, project.longitude])
                valid_projects.append(project)
        
        if len(points) < 2:
            return {}, np.array([])
        
        points = np.array(points)
        
        # Determine number of clusters if not specified
        if self.n_clusters is None:
            # Use number of unique barangays as estimate
            unique_barangays = len(set(p.barangay for p in valid_projects if p.barangay))
            self.n_clusters = max(2, min(unique_barangays, len(points) // 2))
        
        # Scale features
        points_scaled = self.scaler.fit_transform(points)
        
        # Apply K-Means
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(points_scaled)
        
        # Convert to cluster dictionary
        clusters = {}
        for idx, project in enumerate(valid_projects):
            cluster_id = f"Cluster_{labels[idx]}"
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(project)
        
        return clusters, labels
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "K-Means Clustering"


class DBSCANClustering:
    """DBSCAN clustering algorithm"""
    
    def __init__(self, eps: float = 0.01, min_samples: int = 3):
        self.eps = eps
        self.min_samples = min_samples
        self.scaler = StandardScaler()
    
    def cluster_projects(self, projects: List[Project]) -> Tuple[Dict[str, List[Project]], np.ndarray]:
        """
        Cluster projects using DBSCAN
        
        Returns:
            Tuple of (clusters_dict, labels_array)
        """
        # Prepare data points
        points = []
        valid_projects = []
        
        for project in projects:
            if project.latitude and project.longitude:
                points.append([project.latitude, project.longitude])
                valid_projects.append(project)
        
        if len(points) < 2:
            return {}, np.array([])
        
        points = np.array(points)
        
        # Scale features
        points_scaled = self.scaler.fit_transform(points)
        
        # Apply DBSCAN
        dbscan = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = dbscan.fit_predict(points_scaled)
        
        # Convert to cluster dictionary
        clusters = {}
        for idx, project in enumerate(valid_projects):
            cluster_id = f"Cluster_{labels[idx]}" if labels[idx] != -1 else "Noise"
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(project)
        
        return clusters, labels
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "DBSCAN Clustering"


class HierarchicalClustering:
    """Hierarchical (Agglomerative) Clustering algorithm"""
    
    def __init__(self, n_clusters: Optional[int] = None, linkage: str = 'ward'):
        self.n_clusters = n_clusters
        self.linkage = linkage
        self.scaler = StandardScaler()
    
    def cluster_projects(self, projects: List[Project]) -> Tuple[Dict[str, List[Project]], np.ndarray]:
        """
        Cluster projects using Hierarchical Clustering
        
        Returns:
            Tuple of (clusters_dict, labels_array)
        """
        # Prepare data points
        points = []
        valid_projects = []
        
        for project in projects:
            if project.latitude and project.longitude:
                points.append([project.latitude, project.longitude])
                valid_projects.append(project)
        
        if len(points) < 2:
            return {}, np.array([])
        
        points = np.array(points)
        
        # Determine number of clusters if not specified
        if self.n_clusters is None:
            unique_barangays = len(set(p.barangay for p in valid_projects if p.barangay))
            self.n_clusters = max(2, min(unique_barangays, len(points) // 2))
        
        # Scale features
        points_scaled = self.scaler.fit_transform(points)
        
        # Apply Hierarchical Clustering
        hierarchical = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            linkage=self.linkage
        )
        labels = hierarchical.fit_predict(points_scaled)
        
        # Convert to cluster dictionary
        clusters = {}
        for idx, project in enumerate(valid_projects):
            cluster_id = f"Cluster_{labels[idx]}"
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(project)
        
        return clusters, labels
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "Hierarchical Clustering"


class ClusteringAlgorithmComparator:
    """Compares different clustering algorithms"""
    
    def __init__(self):
        self.algorithms = {
            'administrative': AdministrativeSpatialAnalysis(),
            'kmeans': KMeansClustering(),
            'dbscan': DBSCANClustering(),
            'hierarchical': HierarchicalClustering()
        }
        self.results = {}
    
    def prepare_data(self, projects: List[Project]) -> Tuple[np.ndarray, List[Project]]:
        """Prepare coordinate data from projects"""
        points = []
        valid_projects = []
        
        for project in projects:
            if project.latitude and project.longitude:
                points.append([project.latitude, project.longitude])
                valid_projects.append(project)
        
        return np.array(points) if points else np.array([]), valid_projects
    
    def calculate_zoning_alignment_score(
        self,
        clusters: Dict[str, List[Project]]
    ) -> float:
        """
        Calculate Zoning Alignment Score (ZAS)
        Formula: ZAS = |C ∩ Z| / |C ∪ Z|
        Where C = cluster projects, Z = official barangay boundary
        """
        if not clusters:
            return 0.0
        
        total_correct = 0
        total_projects = 0
        
        for cluster_id, cluster_projects in clusters.items():
            if not cluster_projects:
                continue
            
            # Get most common barangay in cluster
            barangays = [p.barangay for p in cluster_projects if p.barangay]
            if not barangays:
                continue
            
            from collections import Counter
            most_common_barangay = Counter(barangays).most_common(1)[0][0]
            
            # Count projects matching the most common barangay
            correct = sum(1 for p in cluster_projects if p.barangay == most_common_barangay)
            total_correct += correct
            total_projects += len(cluster_projects)
        
        if total_projects == 0:
            return 0.0
        
        return total_correct / total_projects
    
    def calculate_metrics(
        self,
        points: np.ndarray,
        labels: np.ndarray,
        clusters: Dict[str, List[Project]],
        execution_time: float
    ) -> Dict:
        """Calculate all performance metrics"""
        if len(points) == 0 or len(labels) == 0:
            return {
                'silhouette_score': 0.0,
                'calinski_harabasz_score': 0.0,
                'davies_bouldin_score': 0.0,
                'zoning_alignment_score': 0.0,
                'execution_time': execution_time,
                'cluster_count': 0,
                'noise_count': 0
            }
        
        # Remove noise points (-1 labels) for some metrics
        valid_mask = labels != -1
        if valid_mask.sum() < 2:
            silhouette = 0.0
            calinski = 0.0
            davies = 0.0
        else:
            points_valid = points[valid_mask]
            labels_valid = labels[valid_mask]
            
            try:
                silhouette = silhouette_score(points_valid, labels_valid)
            except:
                silhouette = 0.0
            
            try:
                calinski = calinski_harabasz_score(points_valid, labels_valid)
            except:
                calinski = 0.0
            
            try:
                davies = davies_bouldin_score(points_valid, labels_valid)
            except:
                davies = 0.0
        
        # Zoning Alignment Score
        zas = self.calculate_zoning_alignment_score(clusters)
        
        # Count clusters and noise
        unique_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        noise_count = (labels == -1).sum()
        
        return {
            'silhouette_score': round(silhouette, 4),
            'calinski_harabasz_score': round(calinski, 2),
            'davies_bouldin_score': round(davies, 4),
            'zoning_alignment_score': round(zas, 4),
            'execution_time': round(execution_time, 4),
            'cluster_count': unique_clusters,
            'noise_count': noise_count,
            'total_projects': len(points)
        }
    
    def compare_algorithms(self, projects: List[Project] = None) -> Dict:
        """
        Compare all clustering algorithms
        
        Args:
            projects: List of projects to cluster (if None, uses all)
        
        Returns:
            Dictionary with results for each algorithm
        """
        if projects is None:
            projects = list(Project.objects.all())
        
        if len(projects) < 2:
            raise ValueError("Need at least 2 projects for clustering comparison")
        
        # Prepare data
        points, valid_projects = self.prepare_data(projects)
        
        if len(points) < 2:
            raise ValueError("Need at least 2 projects with valid coordinates")
        
        results = {}
        
        for algo_key, algorithm in self.algorithms.items():
            print(f"Evaluating {algorithm.get_algorithm_name()}...")
            
            start_time = time.time()
            
            try:
                # Perform clustering
                clusters, labels = algorithm.cluster_projects(valid_projects)
                
                execution_time = time.time() - start_time
                
                # Calculate metrics
                metrics = self.calculate_metrics(points, labels, clusters, execution_time)
                
                # Determine strengths and weaknesses
                strengths, weaknesses = self._analyze_algorithm(algo_key, metrics)
                
                results[algo_key] = {
                    'algorithm_name': algorithm.get_algorithm_name(),
                    'clusters': clusters,
                    'labels': labels,
                    'metrics': metrics,
                    'strengths': strengths,
                    'weaknesses': weaknesses,
                    'remarks': self._get_remarks(algo_key, metrics)
                }
                
            except Exception as e:
                print(f"Error with {algorithm.get_algorithm_name()}: {str(e)}")
                results[algo_key] = {
                    'algorithm_name': algorithm.get_algorithm_name(),
                    'error': str(e),
                    'metrics': {
                        'silhouette_score': 0.0,
                        'zoning_alignment_score': 0.0,
                        'execution_time': 0.0,
                        'cluster_count': 0
                    }
                }
        
        self.results = results
        return results
    
    def _analyze_algorithm(self, algo_key: str, metrics: Dict) -> Tuple[List[str], List[str]]:
        """Analyze algorithm characteristics"""
        strengths = []
        weaknesses = []
        
        if algo_key == 'administrative':
            strengths = [
                "Perfect alignment with administrative boundaries",
                "Fast execution time",
                "Governance-oriented clustering",
                "No parameter tuning required",
                "Interpretable results"
            ]
            weaknesses = [
                "May not capture spatial density patterns",
                "Ignores geographic proximity",
                "Less flexible for irregular patterns"
            ]
        elif algo_key == 'kmeans':
            strengths = [
                "Handles irregular spatial patterns",
                "Fast and scalable",
                "Good for spherical clusters",
                "Deterministic results"
            ]
            weaknesses = [
                "Requires predefined number of clusters",
                "May not align with administrative boundaries",
                "Assumes spherical cluster shapes",
                "Sensitive to initialization"
            ]
        elif algo_key == 'dbscan':
            strengths = [
                "Identifies irregular spatial patterns",
                "No need to specify cluster count",
                "Handles noise/outliers well",
                "Good for dense regions"
            ]
            weaknesses = [
                "Does not conform to administrative boundaries",
                "Sensitive to parameter tuning (eps, min_samples)",
                "May create too many small clusters",
                "Less suitable for governance systems"
            ]
        elif algo_key == 'hierarchical':
            strengths = [
                "Multi-level visualization of relationships",
                "No need to specify cluster count upfront",
                "Provides dendrogram for analysis",
                "Handles non-spherical clusters"
            ]
            weaknesses = [
                "Computationally intensive",
                "May not align with administrative boundaries",
                "Less suitable for real-time clustering",
                "Memory intensive for large datasets"
            ]
        
        return strengths, weaknesses
    
    def _get_remarks(self, algo_key: str, metrics: Dict) -> str:
        """Get remarks for each algorithm"""
        silhouette = metrics['silhouette_score']
        zas = metrics['zoning_alignment_score']
        
        if algo_key == 'administrative':
            if zas >= 0.9:
                return "Most effective for governance-oriented clustering; ideal for ONETAGUMVISION"
            else:
                return "Effective for administrative alignment; suitable for government systems"
        elif algo_key == 'kmeans':
            if silhouette >= 0.5:
                return "Good for spatial pattern identification; useful for exploratory analysis"
            else:
                return "Effective for regular patterns; may need parameter tuning"
        elif algo_key == 'dbscan':
            if metrics['noise_count'] > 0:
                return "Effective for identifying dense regions and outliers; less suitable for governance"
            else:
                return "Good for irregular patterns; requires careful parameter selection"
        elif algo_key == 'hierarchical':
            if metrics['execution_time'] > 1.0:
                return "Provides detailed cluster relationships; best for analytical visualization"
            else:
                return "Useful for understanding spatial hierarchies; computationally intensive"
    
    def get_comparison_table(self) -> List[Dict]:
        """Get formatted comparison table data"""
        table_data = []
        
        for algo_key, result in self.results.items():
            if 'error' in result:
                continue
            
            metrics = result['metrics']
            table_data.append({
                'algorithm': result['algorithm_name'],
                'silhouette_score': metrics['silhouette_score'],
                'zoning_alignment_score': metrics['zoning_alignment_score'],
                'calinski_harabasz_score': metrics['calinski_harabasz_score'],
                'davies_bouldin_score': metrics['davies_bouldin_score'],
                'execution_time': metrics['execution_time'],
                'cluster_count': metrics['cluster_count'],
                'noise_count': metrics.get('noise_count', 0),
                'strengths': result['strengths'],
                'weaknesses': result['weaknesses'],
                'remarks': result['remarks']
            })
        
        # Sort by zoning alignment score (descending) for governance relevance
        table_data.sort(key=lambda x: x['zoning_alignment_score'], reverse=True)
        
        return table_data
    
    def get_best_algorithm(self, metric: str = 'zoning_alignment_score') -> str:
        """Get the best performing algorithm based on metric"""
        if not self.results:
            raise ValueError("No algorithms have been evaluated yet.")
        
        best_algo = None
        best_score = -1
        
        for algo_key, result in self.results.items():
            if 'error' in result:
                continue
            
            score = result['metrics'].get(metric, 0)
            if score > best_score:
                best_score = score
                best_algo = algo_key
        
        return best_algo if best_algo else 'administrative'


def run_clustering_comparison() -> Dict:
    """Main function to run the clustering comparison"""
    if not HAS_ML:
        raise ImportError(
            "Clustering comparison requires scikit-learn, numpy, and pandas. "
            "Install with: pip install -r requirements-ml.txt "
            "(On Windows you may need Microsoft C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/)"
        )
    comparator = ClusteringAlgorithmComparator()
    
    try:
        # Get all projects
        projects = list(Project.objects.all())
        
        if len(projects) < 2:
            raise ValueError("Need at least 2 projects for comparison")
        
        print(f"Comparing clustering algorithms on {len(projects)} projects...")
        
        # Run comparison
        results = comparator.compare_algorithms(projects)
        
        # Get comparison table
        comparison_table = comparator.get_comparison_table()
        
        # Get best algorithm
        best_algo = comparator.get_best_algorithm('zoning_alignment_score')
        
        return {
            'results': results,
            'comparison_table': comparison_table,
            'best_algorithm': best_algo,
            'total_projects': len(projects),
            'valid_projects': sum(1 for p in projects if p.latitude and p.longitude)
        }
    
    except Exception as e:
        print(f"Error during comparison: {str(e)}")
        raise

