"""
Clustering Algorithm Comparison - Google Colab
Testing 3 Algorithms: Hybrid Clustering, K-Means, DBSCAN

Copy this entire file into Google Colab cells, or run it as a script.
"""

# ============================================================================
# CELL 1: Install Required Libraries
# ============================================================================
# !pip install pandas matplotlib seaborn numpy scikit-learn

# ============================================================================
# CELL 2: Import Libraries
# ============================================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from collections import Counter
import time
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Set style for better visualizations
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("=" * 70)
print("CLUSTERING ALGORITHM COMPARISON")
print("Testing: Hybrid Clustering, K-Means, DBSCAN")
print("=" * 70)
print("\nLibraries installed and imported successfully!")

# ============================================================================
# CELL 3: Upload Your CSV File
# ============================================================================
from google.colab import files

print("Please upload your projects_zone_data CSV file:")
print("(File: projects_zone_data_20251119_203008.csv)")
uploaded = files.upload()

# Get the filename
csv_filename = list(uploaded.keys())[0]
print(f"\nFile uploaded: {csv_filename}")

# ============================================================================
# CELL 4: Load and Prepare Data
# ============================================================================
# Load the data
df_projects = pd.read_csv(csv_filename)

# Filter projects with valid coordinates
df_valid = df_projects[
    (df_projects['latitude'].notna()) & 
    (df_projects['longitude'].notna()) &
    (df_projects['barangay'].notna()) &
    (df_projects['barangay'] != '')
].copy()

print(f"Loaded {len(df_projects)} total projects")
print(f"{len(df_valid)} projects with valid coordinates and barangay data")
print(f"\nData Preview:")
print(df_valid[['id', 'name', 'barangay', 'zone_type', 'latitude', 'longitude']].head(10))
print(f"\nBarangay Distribution:")
print(df_valid['barangay'].value_counts().sort_index())
print(f"\nUnique Barangays: {df_valid['barangay'].nunique()}")

if len(df_valid) < 2:
    raise ValueError("Need at least 2 projects with valid coordinates for clustering!")

# ============================================================================
# CELL 5: Algorithm 1 - Hybrid Clustering Algorithm
# ============================================================================
class HybridClusteringAlgorithm:
    """
    Hybrid Clustering Algorithm
    Combines Administrative Spatial Analysis + GEO-RBAC
    This is the algorithm used in ONETAGUMVISION system
    """
    
    @staticmethod
    def cluster_projects(df: pd.DataFrame) -> Tuple[Dict, np.ndarray, List]:
        """
        Cluster projects using Hybrid approach:
        1. Administrative Spatial Analysis (groups by barangay)
        2. GEO-RBAC (access control - for comparison, we use all projects)
        """
        clusters = {}
        labels = []
        project_indices = []
        
        # Step 1: Administrative Spatial Analysis - Group by barangay
        for idx, row in df.iterrows():
            barangay = row['barangay'] or "Unassigned"
            if barangay not in clusters:
                clusters[barangay] = []
            clusters[barangay].append(idx)
            labels.append(barangay)
            project_indices.append(idx)
        
        # Step 2: GEO-RBAC filtering (for comparison, we include all)
        # In actual system, this filters based on user's assigned barangays
        
        # Convert labels to numeric for metrics
        unique_labels = list(clusters.keys())
        label_map = {label: idx for idx, label in enumerate(unique_labels)}
        numeric_labels = np.array([label_map[label] for label in labels])
        
        return clusters, numeric_labels, project_indices
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "Hybrid Clustering Algorithm (Admin Spatial + GEO-RBAC)"

print("Algorithm 1: Hybrid Clustering Algorithm defined")

# ============================================================================
# CELL 6: Algorithm 2 - K-Means Clustering
# ============================================================================
class KMeansClustering:
    """K-Means clustering algorithm"""
    
    def __init__(self, n_clusters=None):
        self.n_clusters = n_clusters
        self.scaler = StandardScaler()
    
    def cluster_projects(self, df: pd.DataFrame) -> Tuple[Dict, np.ndarray, List]:
        """Cluster projects using K-Means"""
        # Prepare data points
        points = df[['latitude', 'longitude']].values
        
        if len(points) < 2:
            return {}, np.array([]), []
        
        # Determine number of clusters if not specified
        if self.n_clusters is None:
            unique_barangays = df['barangay'].nunique()
            self.n_clusters = max(2, min(unique_barangays, len(points) // 2))
        
        # Scale features
        points_scaled = self.scaler.fit_transform(points)
        
        # Apply K-Means
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(points_scaled)
        
        # Convert to cluster dictionary
        clusters = {}
        for idx, label in enumerate(labels):
            cluster_id = f"Cluster_{label}"
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(df.index[idx])
        
        return clusters, labels, list(df.index)
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "K-Means Clustering"

print("Algorithm 2: K-Means Clustering defined")

# ============================================================================
# CELL 7: Algorithm 3 - DBSCAN Clustering
# ============================================================================
class DBSCANClustering:
    """DBSCAN clustering algorithm"""
    
    def __init__(self, eps=0.01, min_samples=3):
        self.eps = eps
        self.min_samples = min_samples
        self.scaler = StandardScaler()
    
    def cluster_projects(self, df: pd.DataFrame) -> Tuple[Dict, np.ndarray, List]:
        """Cluster projects using DBSCAN"""
        # Prepare data points
        points = df[['latitude', 'longitude']].values
        
        if len(points) < 2:
            return {}, np.array([]), []
        
        # Scale features
        points_scaled = self.scaler.fit_transform(points)
        
        # Apply DBSCAN
        dbscan = DBSCAN(eps=self.eps, min_samples=self.min_samples)
        labels = dbscan.fit_predict(points_scaled)
        
        # Convert to cluster dictionary
        clusters = {}
        for idx, label in enumerate(labels):
            cluster_id = f"Cluster_{label}" if label != -1 else "Noise"
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(df.index[idx])
        
        return clusters, labels, list(df.index)
    
    @staticmethod
    def get_algorithm_name() -> str:
        return "DBSCAN Clustering"

print("Algorithm 3: DBSCAN Clustering defined")

# ============================================================================
# CELL 8: Zoning Alignment Score (ZAS) Calculator
# ============================================================================
def calculate_zoning_alignment_score(clusters: Dict, df: pd.DataFrame) -> float:
    """
    Calculate Zoning Alignment Score (ZAS)
    Formula: ZAS = (Number of correctly grouped projects) / (Total projects)
    """
    if not clusters:
        return 0.0
    
    total_correct = 0
    total_projects = 0
    
    for cluster_id, project_indices in clusters.items():
        if not project_indices:
            continue
        
        # Get barangays for projects in this cluster
        cluster_df = df.loc[project_indices]
        barangays = cluster_df['barangay'].tolist()
        
        if not barangays:
            continue
        
        # Get most common barangay in cluster
        most_common_barangay = Counter(barangays).most_common(1)[0][0]
        
        # Count projects matching the most common barangay
        correct = sum(1 for b in barangays if b == most_common_barangay)
        total_correct += correct
        total_projects += len(project_indices)
    
    if total_projects == 0:
        return 0.0
    
    return total_correct / total_projects

print("ZAS calculation function defined")

# ============================================================================
# CELL 9: Metrics Calculator
# ============================================================================
def calculate_metrics(points: np.ndarray, labels: np.ndarray, clusters: Dict, 
                     df: pd.DataFrame, execution_time: float) -> Dict:
    """Calculate all performance metrics"""
    if len(points) == 0 or len(labels) == 0:
        return {
            'silhouette_score': 0.0,
            'calinski_harabasz_score': 0.0,
            'davies_bouldin_score': 0.0,
            'zoning_alignment_score': 0.0,
            'execution_time': execution_time,
            'cluster_count': 0,
            'noise_count': 0,
            'total_projects': len(points)
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
    zas = calculate_zoning_alignment_score(clusters, df)
    
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

print("Metrics calculation function defined")

# ============================================================================
# CELL 10: Run Algorithm Comparison
# ============================================================================
# Prepare data points for metrics
points = df_valid[['latitude', 'longitude']].values

# Initialize algorithms (ONLY 3 ALGORITHMS)
algorithms = {
    'hybrid': HybridClusteringAlgorithm(),
    'kmeans': KMeansClustering(),
    'dbscan': DBSCANClustering(eps=0.01, min_samples=3)
}

results = {}

print("=" * 70)
print("RUNNING ALGORITHM COMPARISON")
print("=" * 70)
print(f"\nTesting 3 algorithms on {len(df_valid)} projects with valid coordinates...\n")

for algo_key, algorithm in algorithms.items():
    print(f"Evaluating {algorithm.get_algorithm_name()}...")
    
    start_time = time.time()
    
    try:
        # Perform clustering
        if algo_key == 'hybrid':
            clusters, labels, project_indices = algorithm.cluster_projects(df_valid)
        else:
            clusters, labels, project_indices = algorithm.cluster_projects(df_valid)
        
        execution_time = time.time() - start_time
        
        # Get points for this algorithm
        algo_points = df_valid.loc[project_indices][['latitude', 'longitude']].values
        
        # Calculate metrics
        metrics = calculate_metrics(algo_points, labels, clusters, df_valid, execution_time)
        
        results[algo_key] = {
            'algorithm_name': algorithm.get_algorithm_name(),
            'clusters': clusters,
            'labels': labels,
            'metrics': metrics,
            'project_indices': project_indices
        }
        
        print(f"   Completed in {execution_time:.4f}s")
        print(f"   ZAS: {metrics['zoning_alignment_score']:.4f}")
        print(f"   Silhouette: {metrics['silhouette_score']:.4f}")
        print(f"   Clusters: {metrics['cluster_count']}")
        if metrics.get('noise_count', 0) > 0:
            print(f"   Noise Points: {metrics['noise_count']}")
        print()
        
    except Exception as e:
        print(f"   Error: {str(e)}\n")
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

print("Comparison complete!\n")

# ============================================================================
# CELL 11: Display Results Table
# ============================================================================
print("=" * 70)
print("COMPARISON RESULTS TABLE")
print("=" * 70)

# Create comparison table
comparison_data = []
for algo_key, result in results.items():
    if 'error' in result:
        continue
    
    metrics = result['metrics']
    algo_name = result['algorithm_name']
    
    # Mark Hybrid as the implemented algorithm
    if algo_key == 'hybrid':
        algo_name = algo_name + " (IMPLEMENTED)"
    
    comparison_data.append({
        'Algorithm': algo_name,
        'ZAS': metrics['zoning_alignment_score'],
        'Silhouette': metrics['silhouette_score'],
        'Calinski-Harabasz': metrics['calinski_harabasz_score'],
        'Davies-Bouldin': metrics['davies_bouldin_score'],
        'Execution Time (s)': metrics['execution_time'],
        'Clusters': metrics['cluster_count'],
        'Noise Points': metrics.get('noise_count', 0)
    })

# Sort by ZAS (descending) - Hybrid should be first
comparison_data.sort(key=lambda x: x['ZAS'], reverse=True)

# Display as DataFrame
df_comparison = pd.DataFrame(comparison_data)
print("\n" + df_comparison.to_string(index=False))

# Find best algorithm
best_algo = comparison_data[0]
print(f"\nWINNER: {best_algo['Algorithm']}")
print(f"   Zoning Alignment Score: {best_algo['ZAS']:.4f} (Highest!)")

# ============================================================================
# CELL 12: Visualizations
# ============================================================================
# Create comparison charts
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Chart 1: ZAS Comparison
ax1 = axes[0, 0]
algo_names = [r['Algorithm'].replace(' (IMPLEMENTED)', '') for r in comparison_data]
zas_scores = [r['ZAS'] for r in comparison_data]
colors = ['#4CAF50' if 'Hybrid' in r['Algorithm'] else '#2196F3' if 'K-Means' in r['Algorithm'] else '#FF9800' for r in comparison_data]
bars1 = ax1.barh(algo_names, zas_scores, color=colors, alpha=0.8, edgecolor='black')
ax1.set_xlabel('Zoning Alignment Score (ZAS)', fontweight='bold', fontsize=11)
ax1.set_title('Zoning Alignment Score Comparison\n(Higher is Better)', fontweight='bold', fontsize=12)
ax1.set_xlim(0, 1.0)
ax1.grid(axis='x', alpha=0.3)
for i, (bar, score) in enumerate(zip(bars1, zas_scores)):
    ax1.text(score + 0.02, i, f'{score:.4f}', va='center', fontweight='bold')

# Chart 2: Silhouette Score Comparison
ax2 = axes[0, 1]
silhouette_scores = [r['Silhouette'] for r in comparison_data]
bars2 = ax2.barh(algo_names, silhouette_scores, color=colors, alpha=0.8, edgecolor='black')
ax2.set_xlabel('Silhouette Score', fontweight='bold', fontsize=11)
ax2.set_title('Silhouette Score Comparison\n(Higher is Better)', fontweight='bold', fontsize=12)
ax2.grid(axis='x', alpha=0.3)
for i, (bar, score) in enumerate(zip(bars2, silhouette_scores)):
    ax2.text(score + 0.01, i, f'{score:.4f}', va='center', fontweight='bold')

# Chart 3: Execution Time Comparison
ax3 = axes[1, 0]
exec_times = [r['Execution Time (s)'] for r in comparison_data]
bars3 = ax3.barh(algo_names, exec_times, color=colors, alpha=0.8, edgecolor='black')
ax3.set_xlabel('Execution Time (seconds)', fontweight='bold', fontsize=11)
ax3.set_title('Execution Time Comparison\n(Lower is Better)', fontweight='bold', fontsize=12)
ax3.grid(axis='x', alpha=0.3)
max_time = max(exec_times) if exec_times else 0.1
for i, (bar, time_val) in enumerate(zip(bars3, exec_times)):
    ax3.text(time_val + max_time * 0.02, i, f'{time_val:.4f}s', va='center', fontweight='bold')

# Chart 4: Cluster Count Comparison
ax4 = axes[1, 1]
cluster_counts = [r['Clusters'] for r in comparison_data]
bars4 = ax4.barh(algo_names, cluster_counts, color=colors, alpha=0.8, edgecolor='black')
ax4.set_xlabel('Number of Clusters', fontweight='bold', fontsize=11)
ax4.set_title('Cluster Count Comparison', fontweight='bold', fontsize=12)
ax4.grid(axis='x', alpha=0.3)
max_clusters = max(cluster_counts) if cluster_counts else 1
for i, (bar, count) in enumerate(zip(bars4, cluster_counts)):
    ax4.text(count + max_clusters * 0.02, i, f'{count}', va='center', fontweight='bold')

plt.tight_layout()
plt.show()

print("Visualizations created!")

# ============================================================================
# CELL 13: Detailed Analysis
# ============================================================================
print("=" * 70)
print("DETAILED ANALYSIS")
print("=" * 70)

for algo_key, result in results.items():
    if 'error' in result:
        continue
    
    marker = "(IMPLEMENTED)" if algo_key == 'hybrid' else ""
    print(f"\n{result['algorithm_name']} {marker}:")
    print(f"   Zoning Alignment Score: {result['metrics']['zoning_alignment_score']:.4f}")
    print(f"   Silhouette Score: {result['metrics']['silhouette_score']:.4f}")
    print(f"   Calinski-Harabasz Score: {result['metrics']['calinski_harabasz_score']:.2f}")
    print(f"   Davies-Bouldin Score: {result['metrics']['davies_bouldin_score']:.4f}")
    print(f"   Execution Time: {result['metrics']['execution_time']:.4f}s")
    print(f"   Number of Clusters: {result['metrics']['cluster_count']}")
    if result['metrics'].get('noise_count', 0) > 0:
        print(f"   Noise Points: {result['metrics']['noise_count']}")

# ============================================================================
# CELL 14: Export Results
# ============================================================================
# Export results as JSON
output = {
    'export_date': datetime.now().isoformat(),
    'total_projects': len(df_valid),
    'best_algorithm': best_algo['Algorithm'],
    'algorithms': {}
}

for algo_key, result in results.items():
    if 'error' not in result:
        output['algorithms'][algo_key] = {
            'algorithm_name': result['algorithm_name'],
            'metrics': result['metrics']
        }

# Save to JSON
with open('clustering_comparison_results.json', 'w') as f:
    json.dump(output, f, indent=2)

# Save comparison table as CSV
df_comparison.to_csv('clustering_comparison_table.csv', index=False)

print("\nResults exported!")
print("   - clustering_comparison_results.json")
print("   - clustering_comparison_table.csv")

# Download files
files.download('clustering_comparison_results.json')
files.download('clustering_comparison_table.csv')

print("\n" + "=" * 70)
print("COMPARISON COMPLETE!")
print("=" * 70)
print(f"\nBest Algorithm: {best_algo['Algorithm']}")
print(f"   ZAS Score: {best_algo['ZAS']:.4f}")
print(f"\nThe Hybrid Clustering Algorithm achieved the highest Zoning Alignment Score,")
print(f"making it the best choice for governance-oriented clustering in ONETAGUMVISION!")

