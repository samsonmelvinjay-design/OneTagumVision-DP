# Algorithms

To determine the most suitable spatial clustering approach for the ONETAGUMVISION system, four algorithms were selected and evaluated: GEO-RBAC, DBSCAN, Administrative Spatial Analysis, and Hierarchical Clustering. These algorithms were chosen based on their relevance to geospatial data segmentation, to determine the best algorithm, and their potential to support urban infrastructure planning.

## GEO-RBAC

GEO-RBAC model extends the traditional Role-Based Access Control (RBAC) framework by introducing the concept of spatial roles, which link user permissions to specific geographic areas. In this model, a spatial role represents an organizational function that is geographically bounded for example, a role limited to a city, road, or district. A user can only activate or perform their role if they are located within the defined spatial boundary of that role.

GEO-RBAC provides a unified way to represent spatial aspects of roles, objects, and contextual data, including user positions. It follows the Open Geospatial Consortium (OGC) standard, where spatial entities are defined as features (e.g., a road, region, or town) with precise geometries such as points, lines, or polygons. Each object in GEO-RBAC corresponds to a set of these spatial features, enabling consistent geographic access control. [21].

## DBSCAN

DBSCAN is a clustering algorithm that groups dense areas of data and marks isolated points as outliers. It handles irregular shapes well without needing a predefined number of clusters. However, since it ignores administrative boundaries, it is less effective for governance-focused systems like ONETAGUMVISION.

## Administrative Spatial Analysis

Administrative Spatial Analysis is a method that groups data based on official geographic boundaries, such as barangays or districts. This makes it ideal for government systems like ONETAGUMVISION, as it aligns project tracking, resource allocation, and reporting with actual administrative zones.

## Hierarchical Clustering

Hierarchical clustering is an unsupervised learning technique that organizes data into a hierarchy of clusters using either a bottom-up (agglomerative) or top-down (divisive) approach. It merges similar data points step by step to form a dendrogram, a visual tree structure that shows how clusters are related at different levels of similarity. This helps in understanding the overall relationships among data groups.

## Hybrid Approach

While GEO-RBAC effectively integrates role-based access control with geospatial data, it initially lacks sensitivity to administrative boundaries such as barangays or districts. To address this, ONETAGUMVISION extends GEO-RBAC with Administrative Spatial Analysis, ensuring that access permissions and project clusters align with official governance zones. Additionally, hierarchical clustering is applied to evaluate relationships among projects across different administrative levels, offering deeper insights for strategic planning. However, due to its computational intensity, this approach is optimized for analytical visualization rather than real-time, large-scale clustering.

## Evaluation Methodology

To evaluate the performance of the spatial clustering algorithms GEO-RBAC, DBSCAN, and Administrative Spatial Analysis, a synthetic dataset was created to simulate real infrastructure data following Tagum City's planning framework. The dataset included geospatial coordinates, administrative zones, and project details, enabling accurate testing without exposing sensitive data. Silhouette scoring in Google Colab was used to assess clustering quality, ensuring that each project was appropriately grouped. This controlled setup provided a realistic and secure environment for comparing algorithm performance and validating their suitability for urban planning and infrastructure monitoring in ONETAGUMVISION. Although synthetic, the data closely reflects typical attributes and spatial distribution patterns of actual infrastructure records, allowing realistic analysis while preserving privacy.

Silhouette scoring [22], applied through Google Colab, further validated the clustering quality by assessing how well each project fits within its assigned group. This makes the dummy dataset not just a placeholder but a vital tool for algorithm testing, performance comparison, and overall system simulation.

## Performance Metrics

In urban planning systems, selecting the most suitable spatial clustering algorithm is crucial to achieving accurate, interpretable, and governance-aligned results. To evaluate the performance of clustering models within ONETAGUMVISION, two primary metrics were used: the Silhouette Score and the Zoning Alignment Score.

### Silhouette Score

The Silhouette Score [23], measures the consistency and separation of clusters by quantifying how similar a data point is to its own cluster compared to other clusters. It is mathematically expressed as:

\[
s(i) = \frac{b(i) - a(i)}{\max\{a(i), b(i)\}}
\]

where \(a(i)\) represents the average distance between the point and all other points within the same cluster (intra-cluster distance), while \(b(i)\) denotes the minimum average distance between the point and all other clusters (nearest-cluster distance). The Silhouette Score ranges from -1 to 1, where values near 1 indicate well-separated clusters and values near 0 suggest overlapping or ambiguous boundaries. As demonstrated [23], this metric serves as a reliable indicator of cluster quality and compactness, ensuring that data-driven groupings maintain both cohesion and distinctiveness.

### Zoning Alignment Score

The Zoning Alignment Score, inspired by spatial similarity measures such as the Geosilhouette Index [24], evaluates how well computationally generated clusters correspond to real administrative boundaries (e.g., barangays, districts, or city zones). It is computed using the formula:

\[
ZAS = \frac{|C \cap Z|}{|C \cup Z|}
\]

This ratio, similar to the Jaccard Similarity Index [25], yields a value between 0 and 1, where higher values indicate stronger spatial alignment with official zoning boundaries. According to Knaap [24], traditional clustering metrics may overlook spatial feasibility, but incorporating geographic or zoning alignment enhances governance relevance and supports decision-making in urban planning.

## Algorithm Comparison and Selection

Using these metrics, ONETAGUMVISION evaluated multiple clustering algorithms, including GEO-RBAC, DBSCAN, Hierarchical Clustering, and Administrative Spatial Analysis. GEO-RBAC demonstrated computational efficiency while incorporating role- and location-based constraints, but it initially lacked sensitivity to detailed zoning borders. DBSCAN effectively identified irregular spatial patterns yet did not conform to structured city layouts. Hierarchical Clustering provided multi-level visualization of spatial relationships but was computationally intensive. In contrast, Administrative Spatial Analysis achieved superior Silhouette and Zoning Alignment Scores, proving most effective for governance-oriented clustering. To optimize both analytical performance and policy relevance, ONETAGUMVISION adopts a hybrid approach combining GEO-RBAC and Administrative Spatial Analysis, enabling clusters that are both data-driven and administratively compliant. This integration supports enhanced project visualization, equitable resource allocation, and data-informed urban planning for Tagum City. [26]

## References

[21] - GEO-RBAC reference  
[22] - Silhouette scoring reference  
[23] - Silhouette Score reference  
[24] - Knaap reference (Geosilhouette Index)  
[25] - Jaccard Similarity Index reference  
[26] - ONETAGUMVISION implementation reference

