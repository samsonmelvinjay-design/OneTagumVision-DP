# Comparative Analysis of Algorithms

Comparative spatial clustering algorithms including Hybrid Clustering Algorithm (Administrative Spatial Analysis + GEO-RBAC), K-Means Clustering, and DBSCAN Clustering were tested to determine the best algorithm for ONETAGUMVISION. Each algorithm was trained and evaluated using real-world infrastructure project data from Tagum City, and assessed with key performance metrics including Zoning Alignment Score (ZAS) (to measure how well clusters align with administrative boundaries), Silhouette Score (to measure clustering quality and cohesion), Calinski-Harabasz Index (to evaluate cluster separation), Davies-Bouldin Index (to assess cluster compactness), Execution Time (to measure processing speed), Clusters Count (to monitor grouping accuracy), and Noise Points (to identify outliers). These analyses were tested in Google Colab using the metrics to determine the best algorithm for ONETAGUMVISION [58].

## Table 8. Metrics

| Metric | Description | Remarks |
|--------|-------------|---------|
| **Zoning Alignment Score (ZAS)** | Measures how well the clusters align with actual administrative zones (custom metric). Computed as the ratio of correctly aligned projects to total projects, where alignment is determined by matching cluster assignments with official barangay boundaries. Calculated using the `calculate_zoning_alignment_score()` function which compares cluster assignments with actual barangay boundaries. | Crucial for governance-based planning. Perfect score (1.0) indicates complete alignment with administrative boundaries. Range: 0.0 to 1.0 (higher is better). This is the primary metric for government systems as it ensures compliance with administrative structure. |
| **Silhouette Score** | Measures how similar a data point is to its own cluster vs. other clusters (range: -1 to 1). Calculated using `sklearn.metrics.silhouette_score()` on scaled coordinate points and cluster labels. | Indicates how well clusters are separated and cohesive. Higher values (closer to 1) indicate better defined clusters. Values above 0.5 indicate good clustering quality. |
| **Calinski-Harabasz Index** | Measures cluster separation by computing the ratio of between-cluster variance to within-cluster variance. Calculated using `sklearn.metrics.calinski_harabasz_score()` on scaled coordinate points and cluster labels. | Higher values indicate better-defined clusters with clear separation between groups. No fixed range (higher is better). |
| **Davies-Bouldin Index** | Evaluates cluster compactness and separation by measuring the average similarity ratio of each cluster with its most similar cluster. Calculated using `sklearn.metrics.davies_bouldin_score()` on scaled coordinate points and cluster labels. | Lower values indicate better clustering quality. Values below 1.0 indicate excellent clustering. Range: 0.0 to infinity (lower is better). |
| **Clusters Count** | Total distinct clusters identified by the algorithm. For governance systems, it should ideally match the number of administrative units (barangays). | Helps assess control over granularity and ensure complete administrative coverage. In Tagum City, there are 23 barangays, so 23 clusters is the ideal count. |
| **Noise Points** | Number of data points not assigned to any cluster (labeled as outliers/noise). For DBSCAN, points with label -1 are considered noise. | Useful in identifying outliers, but zero noise points preferred for governance system to ensure all projects are accounted for. High noise point counts indicate poor clustering for administrative purposes. |
| **Execution Time** | Measures how quickly the algorithm processes the dataset, recording in seconds during the clustering operations. Calculated using Python's `time.time()` before and after algorithm execution. | Affects real-time performance and scalability. Critical for production systems requiring fast response times. Lower values indicate better performance. |

The metrics table provides a basis for testing the algorithms Hybrid Clustering Algorithm (Administrative Spatial Analysis + GEO-RBAC), K-Means Clustering, and DBSCAN Clustering using metrics that measure how well each algorithm performs in a spatial clustering context. Each metric is calculated by the `calculate_metrics()` method in the clustering comparison implementation within the ONETAGUMVISION system's `clustering_algorithm_comparison_colab.py` module. The evaluation process extracts geospatial coordinates (latitude, longitude) from the Project model, applies feature scaling using `StandardScaler`, executes each algorithm, and computes all performance indicators systematically. Each analysis plays a specific role in assessing the algorithm's suitability and effectiveness for the system's goal of zoning and spatial data integration [59].

## Comparison Results

Based on the evaluation with real project data from Tagum City (143 projects across 23 barangays), the following results were obtained:

| Algorithm | ZAS | Silhouette | Calinski-Harabasz | Davies-Bouldin | Execution Time (s) | Clusters | Noise Points |
|-----------|-----|------------|-------------------|----------------|-------------------|----------|--------------|
| **Hybrid Clustering Algorithm (Admin Spatial + GEO-RBAC) (IMPLEMENTED)** | **1.0000** | 0.0826 | 130.51 | 1.4703 | 0.0413 | 23 | 0 |
| K-Means Clustering | 0.5804 | 0.3488 | 260.18 | 0.6633 | 0.0947 | 23 | 0 |
| DBSCAN Clustering | 0.0839 | 0.0000 | 0.00 | 0.0000 | 0.0049 | 0 | 143 |

**Winner: Hybrid Clustering Algorithm (Admin Spatial + GEO-RBAC) (IMPLEMENTED)**

**Zoning Alignment Score: 1.0000 (Highest!)**

### Key Findings:

1. **Hybrid Clustering Algorithm achieved perfect ZAS (1.0000)** because it groups projects by official barangay boundaries, ensuring 100% alignment with administrative structure. This is critical for government systems where projects must be organized according to administrative units for reporting, accountability, and resource allocation.

2. **K-Means Clustering** achieved a ZAS of 0.5804, indicating that only 58.04% of projects were correctly aligned with their barangay boundaries. While it produced 23 clusters matching the number of barangays and achieved a better Silhouette Score (0.3488) and Calinski-Harabasz Index (260.18), its failure to respect administrative boundaries makes it unsuitable for governance applications.

3. **DBSCAN Clustering** performed poorly with a ZAS of 0.0839, producing 0 clusters and classifying all 143 projects as noise points. This indicates that DBSCAN's density-based approach is incompatible with the sparse geographic distribution of infrastructure projects across Tagum City's 23 barangays.

4. **Execution Time**: While DBSCAN was fastest (0.0049s), the Hybrid Algorithm achieved excellent performance (0.0413s), making it suitable for real-time applications. K-Means was slower (0.0947s) but still acceptable.

5. **Noise Points**: The Hybrid Algorithm and K-Means both achieved zero noise points, ensuring all projects are accounted for. DBSCAN's 143 noise points (100% of data) renders it completely unsuitable for the system.

The Hybrid Clustering Algorithm's perfect Zoning Alignment Score of 1.0000, combined with zero noise points, 23 clusters matching the administrative structure, and fast execution time, makes it the optimal choice for ONETAGUMVISION's governance-oriented spatial clustering requirements.

