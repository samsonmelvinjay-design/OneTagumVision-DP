"""
🚀 GISTAGUM Comprehensive Analytics Testing - Google Colab
===========================================================

Testing All 8 Analytics Categories with Real Data

This script tests all analytics used in the GISTAGUM system:
1. Zoning Analytics - Zone distribution and compliance
2. Clustering Analytics - Barangay-based clustering
3. Suitability Analytics - Land suitability analysis
4. Financial Analytics - Budget and cost analysis
5. Status Analytics - Project status distribution
6. Timeline Analytics - Project timeline and delays
7. Progress Analytics - Progress tracking and trends
8. Integrated Analytics - Combined health scores

📋 Instructions:
1. Copy each section into separate cells in Google Colab
2. Run the first cell to install required libraries
3. Upload your exported CSV files:
   - all_projects_data_YYYYMMDD_HHMMSS.csv
   - progress_data_YYYYMMDD_HHMMSS.csv
   - cost_data_YYYYMMDD_HHMMSS.csv
4. Upload the JSON file: all_analytics_YYYYMMDD_HHMMSS.json (optional, for comparison)
5. Run all cells in order
6. Compare results with your system's analytics
"""

# ============================================================================
# CELL 1: Install Libraries
# ============================================================================
# !pip install pandas matplotlib seaborn numpy scikit-learn plotly -q
# print("✅ Libraries installed successfully!")

# ============================================================================
# CELL 2: Import Libraries
# ============================================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from collections import defaultdict
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("✅ Libraries imported successfully!")
print("📊 Ready to analyze data!")

# ============================================================================
# CELL 3: Upload Data Files
# ============================================================================
from google.colab import files

print("📤 Please upload your exported CSV and JSON files:")
print("   1. all_projects_data_*.csv")
print("   2. progress_data_*.csv")
print("   3. cost_data_*.csv")
print("   4. all_analytics_*.json (optional)")
print("\nClick 'Choose Files' and select all files, then click 'Upload'")

uploaded = files.upload()

# Get filenames
project_file = [f for f in uploaded.keys() if 'all_projects_data' in f][0]
progress_file = [f for f in uploaded.keys() if 'progress_data' in f][0]
cost_file = [f for f in uploaded.keys() if 'cost_data' in f][0]
analytics_json = [f for f in uploaded.keys() if 'all_analytics' in f and f.endswith('.json')]

print(f"\n✅ Files uploaded:")
print(f"   - Projects: {project_file}")
print(f"   - Progress: {progress_file}")
print(f"   - Costs: {cost_file}")
if analytics_json:
    print(f"   - Analytics JSON: {analytics_json[0]}")

# ============================================================================
# CELL 4: Load Data
# ============================================================================
# Load data
df_projects = pd.read_csv(project_file)
df_progress = pd.read_csv(progress_file)
df_costs = pd.read_csv(cost_file)

# Convert date columns
date_cols = ['start_date', 'end_date', 'created_at']
for col in date_cols:
    if col in df_projects.columns:
        df_projects[col] = pd.to_datetime(df_projects[col], errors='coerce')

if 'date' in df_progress.columns:
    df_progress['date'] = pd.to_datetime(df_progress['date'], errors='coerce')
if 'date' in df_costs.columns:
    df_costs['date'] = pd.to_datetime(df_costs['date'], errors='coerce')

print(f"✅ Data loaded successfully!")
print(f"\n📊 Data Overview:")
print(f"   - Projects: {len(df_projects)} rows")
print(f"   - Progress Updates: {len(df_progress)} rows")
print(f"   - Cost Entries: {len(df_costs)} rows")

# Display first few rows
print(f"\n📋 Projects Preview:")
display(df_projects.head())

# ============================================================================
# CELL 5: Zone Configuration
# ============================================================================
# Zone type display names
ZONE_DISPLAY_NAMES = {
    'R-1': 'Low Density Residential',
    'R-2': 'Medium Density Residential',
    'R-3': 'High Density Residential',
    'SHZ': 'Socialized Housing',
    'C-1': 'Major Commercial',
    'C-2': 'Minor Commercial',
    'I-1': 'Heavy Industrial',
    'I-2': 'Light/Medium Industrial',
    'AGRO': 'Agro-Industrial',
    'INS-1': 'Institutional',
    'PARKS': 'Parks & Open Spaces',
    'AGRICULTURAL': 'Agricultural',
    'ECO-TOURISM': 'Eco-tourism',
    'SPECIAL': 'Special Use',
}

print("✅ Zone configuration loaded")

# ============================================================================
# CELL 6: 1️⃣ ZONING ANALYTICS
# ============================================================================
def calculate_zoning_analytics(projects_df):
    """Calculate zoning analytics"""
    # Filter projects with zones
    projects_with_zones = projects_df[
        (projects_df['zone_type'].notna()) & 
        (projects_df['zone_type'] != '')
    ].copy()
    
    if len(projects_with_zones) == 0:
        return {}
    
    # Aggregate by zone
    zones = []
    for zone_type in projects_with_zones['zone_type'].unique():
        zone_projects = projects_with_zones[projects_with_zones['zone_type'] == zone_type]
        
        zones.append({
            'zone_type': zone_type,
            'display_name': ZONE_DISPLAY_NAMES.get(zone_type, zone_type),
            'total_projects': len(zone_projects),
            'completed': len(zone_projects[zone_projects['status'] == 'completed']),
            'in_progress': len(zone_projects[zone_projects['status'].isin(['in_progress', 'ongoing'])]),
            'planned': len(zone_projects[zone_projects['status'].isin(['planned', 'pending'])]),
            'delayed': len(zone_projects[zone_projects['status'] == 'delayed']),
            'total_cost': float(zone_projects['project_cost'].sum())
        })
    
    zones.sort(key=lambda x: x['zone_type'])
    
    return {
        'total_projects_with_zones': len(projects_with_zones),
        'zones': zones,
        'zone_validation_rate': (projects_with_zones['zone_validated'].sum() / len(projects_with_zones) * 100) if 'zone_validated' in projects_with_zones.columns else 0
    }

# Calculate
zoning_analytics = calculate_zoning_analytics(df_projects)

print("=" * 70)
print("1️⃣ ZONING ANALYTICS")
print("=" * 70)
print(f"\nTotal projects with zones: {zoning_analytics['total_projects_with_zones']}")
print(f"Zone validation rate: {zoning_analytics['zone_validation_rate']:.1f}%")
print(f"\nZone Distribution:")
for zone in zoning_analytics['zones']:
    print(f"  {zone['zone_type']:8} ({zone['display_name']:30}): {zone['total_projects']:3} projects | ${zone['total_cost']:,.2f}")

# ============================================================================
# CELL 7: Visualize Zoning Analytics
# ============================================================================
# Visualize zoning analytics
zones_df = pd.DataFrame(zoning_analytics['zones'])

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Chart 1: Projects by Zone
zones_sorted = zones_df.sort_values('total_projects', ascending=True)
axes[0].barh(zones_sorted['zone_type'], zones_sorted['total_projects'], color='steelblue', alpha=0.8)
axes[0].set_xlabel('Number of Projects', fontweight='bold')
axes[0].set_ylabel('Zone Type', fontweight='bold')
axes[0].set_title('Projects by Zone Type', fontweight='bold', fontsize=14)
axes[0].grid(axis='x', alpha=0.3)

# Chart 2: Status Distribution by Zone
status_cols = ['completed', 'in_progress', 'planned', 'delayed']
zones_df[status_cols].plot(kind='bar', stacked=True, ax=axes[1], 
                           color=['green', 'blue', 'orange', 'red'], alpha=0.8)
axes[1].set_xticklabels(zones_df['zone_type'], rotation=45, ha='right')
axes[1].set_ylabel('Number of Projects', fontweight='bold')
axes[1].set_title('Status Distribution by Zone', fontweight='bold', fontsize=14)
axes[1].legend(title='Status')
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================================
# CELL 8: 2️⃣ CLUSTERING ANALYTICS
# ============================================================================
def calculate_clustering_analytics(projects_df):
    """Calculate clustering analytics (barangay-based)"""
    # Filter projects with barangay
    projects_with_barangay = projects_df[projects_df['barangay'].notna() & (projects_df['barangay'] != '')].copy()
    
    if len(projects_with_barangay) == 0:
        return {}
    
    # Aggregate by barangay
    clusters = []
    for barangay in projects_with_barangay['barangay'].unique():
        barangay_projects = projects_with_barangay[projects_with_barangay['barangay'] == barangay]
        
        clusters.append({
            'barangay': barangay,
            'total_projects': len(barangay_projects),
            'avg_latitude': float(barangay_projects['latitude'].mean()) if 'latitude' in barangay_projects.columns else 0,
            'avg_longitude': float(barangay_projects['longitude'].mean()) if 'longitude' in barangay_projects.columns else 0,
        })
    
    clusters.sort(key=lambda x: x['total_projects'], reverse=True)
    
    return {
        'total_clusters': len(clusters),
        'clusters': clusters
    }

# Calculate
clustering_analytics = calculate_clustering_analytics(df_projects)

print("=" * 70)
print("2️⃣ CLUSTERING ANALYTICS")
print("=" * 70)
print(f"\nTotal clusters (barangays): {clustering_analytics['total_clusters']}")
print(f"\nTop 10 Barangays by Project Count:")
for i, cluster in enumerate(clustering_analytics['clusters'][:10], 1):
    print(f"  {i:2}. {cluster['barangay']:25}: {cluster['total_projects']:3} projects")

# ============================================================================
# CELL 9: Visualize Clustering Analytics
# ============================================================================
# Visualize clustering analytics
clusters_df = pd.DataFrame(clustering_analytics['clusters'])

fig, ax = plt.subplots(figsize=(14, 8))

# Bar chart of projects per barangay
top_15 = clusters_df.head(15).sort_values('total_projects', ascending=True)
ax.barh(top_15['barangay'], top_15['total_projects'], color='coral', alpha=0.8)
ax.set_xlabel('Number of Projects', fontweight='bold', fontsize=12)
ax.set_ylabel('Barangay', fontweight='bold', fontsize=12)
ax.set_title('Projects per Barangay (Top 15)', fontweight='bold', fontsize=14)
ax.grid(axis='x', alpha=0.3)

# Add value labels
for i, (barangay, count) in enumerate(zip(top_15['barangay'], top_15['total_projects'])):
    ax.text(count + 0.5, i, str(int(count)), va='center', fontweight='bold')

plt.tight_layout()
plt.show()

# ============================================================================
# CELL 10: 3️⃣ FINANCIAL ANALYTICS
# ============================================================================
def calculate_financial_analytics(projects_df, costs_df):
    """Calculate financial analytics"""
    total_budget = float(projects_df['project_cost'].sum())
    total_spent = float(costs_df['amount'].sum())
    
    # Cost by type
    cost_by_type = costs_df.groupby('cost_type')['amount'].sum().to_dict()
    
    # Budget utilization per project
    project_financials = []
    for _, project in projects_df.iterrows():
        project_costs = costs_df[costs_df['project_id'] == project['id']]
        spent = float(project_costs['amount'].sum()) if len(project_costs) > 0 else 0.0
        budget = float(project['project_cost']) if pd.notna(project['project_cost']) else 0.0
        utilization = (spent / budget * 100) if budget > 0 else 0
        
        project_financials.append({
            'project_id': project['id'],
            'project_name': project['name'],
            'budget': budget,
            'spent': spent,
            'remaining': budget - spent,
            'utilization_percentage': utilization
        })
    
    return {
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining_budget': total_budget - total_spent,
        'utilization_percentage': (total_spent / total_budget * 100) if total_budget > 0 else 0,
        'cost_by_type': cost_by_type,
        'project_financials': project_financials
    }

# Calculate
financial_analytics = calculate_financial_analytics(df_projects, df_costs)

print("=" * 70)
print("3️⃣ FINANCIAL ANALYTICS")
print("=" * 70)
print(f"\nTotal Budget: ${financial_analytics['total_budget']:,.2f}")
print(f"Total Spent: ${financial_analytics['total_spent']:,.2f}")
print(f"Remaining: ${financial_analytics['remaining_budget']:,.2f}")
print(f"Utilization: {financial_analytics['utilization_percentage']:.1f}%")
print(f"\nCost Breakdown by Type:")
for cost_type, amount in financial_analytics['cost_by_type'].items():
    percentage = (amount / financial_analytics['total_spent'] * 100) if financial_analytics['total_spent'] > 0 else 0
    print(f"  {cost_type:15}: ${amount:,.2f} ({percentage:5.1f}%)")

# ============================================================================
# CELL 11: Visualize Financial Analytics
# ============================================================================
# Visualize financial analytics
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Chart 1: Budget Utilization (Doughnut)
utilization_data = [financial_analytics['total_spent'], financial_analytics['remaining_budget']]
axes[0, 0].pie(utilization_data, labels=['Spent', 'Remaining'], autopct='%1.1f%%', 
               colors=['#FF6B6B', '#4ECDC4'], startangle=90)
axes[0, 0].set_title('Budget Utilization', fontweight='bold', fontsize=14)

# Chart 2: Cost by Type (Pie)
cost_types = list(financial_analytics['cost_by_type'].keys())
cost_amounts = list(financial_analytics['cost_by_type'].values())
axes[0, 1].pie(cost_amounts, labels=cost_types, autopct='%1.1f%%', startangle=90)
axes[0, 1].set_title('Spending by Cost Type', fontweight='bold', fontsize=14)

# Chart 3: Top 10 Projects by Budget
project_fin_df = pd.DataFrame(financial_analytics['project_financials'])
top_projects = project_fin_df.nlargest(10, 'budget')
axes[1, 0].barh(range(len(top_projects)), top_projects['budget'], color='steelblue', alpha=0.8)
axes[1, 0].set_yticks(range(len(top_projects)))
axes[1, 0].set_yticklabels([name[:30] + '...' if len(name) > 30 else name for name in top_projects['project_name']], fontsize=8)
axes[1, 0].set_xlabel('Budget ($)', fontweight='bold')
axes[1, 0].set_title('Top 10 Projects by Budget', fontweight='bold', fontsize=14)
axes[1, 0].grid(axis='x', alpha=0.3)

# Chart 4: Budget Utilization Distribution
axes[1, 1].hist(project_fin_df['utilization_percentage'], bins=20, color='orange', alpha=0.7, edgecolor='black')
axes[1, 1].set_xlabel('Utilization Percentage', fontweight='bold')
axes[1, 1].set_ylabel('Number of Projects', fontweight='bold')
axes[1, 1].set_title('Budget Utilization Distribution', fontweight='bold', fontsize=14)
axes[1, 1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================================
# CELL 12: 4️⃣ STATUS ANALYTICS
# ============================================================================
def calculate_status_analytics(projects_df):
    """Calculate status analytics"""
    status_counts = projects_df['status'].value_counts().to_dict()
    
    return {
        'distribution': status_counts,
        'total': len(projects_df)
    }

# Calculate
status_analytics = calculate_status_analytics(df_projects)

print("=" * 70)
print("4️⃣ STATUS ANALYTICS")
print("=" * 70)
print(f"\nTotal Projects: {status_analytics['total']}")
print(f"\nStatus Distribution:")
for status, count in sorted(status_analytics['distribution'].items()):
    percentage = (count / status_analytics['total'] * 100)
    print(f"  {status:15}: {count:3} projects ({percentage:5.1f}%)")

# ============================================================================
# CELL 13: Visualize Status Analytics
# ============================================================================
# Visualize status analytics
status_df = pd.DataFrame(list(status_analytics['distribution'].items()), columns=['Status', 'Count'])

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Pie chart
colors = {'completed': 'green', 'in_progress': 'blue', 'ongoing': 'lightblue', 
          'planned': 'orange', 'pending': 'yellow', 'delayed': 'red', 'cancelled': 'gray'}
pie_colors = [colors.get(status.lower(), 'gray') for status in status_df['Status']]
axes[0].pie(status_df['Count'], labels=status_df['Status'], autopct='%1.1f%%', 
            colors=pie_colors, startangle=90)
axes[0].set_title('Project Status Distribution', fontweight='bold', fontsize=14)

# Bar chart
axes[1].bar(status_df['Status'], status_df['Count'], color=pie_colors, alpha=0.8, edgecolor='black')
axes[1].set_xlabel('Status', fontweight='bold')
axes[1].set_ylabel('Number of Projects', fontweight='bold')
axes[1].set_title('Projects by Status', fontweight='bold', fontsize=14)
axes[1].tick_params(axis='x', rotation=45)
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================================
# CELL 14: 5️⃣ PROGRESS ANALYTICS
# ============================================================================
def calculate_progress_analytics(projects_df, progress_df):
    """Calculate progress analytics"""
    # Get latest progress for each project
    latest_progress = progress_df.sort_values('date').groupby('project_id').last()
    
    progress_data = []
    for _, project in projects_df.iterrows():
        project_progress = latest_progress[latest_progress.index == project['id']]
        latest_pct = float(project_progress['percentage_complete'].iloc[0]) if len(project_progress) > 0 else 0.0
        progress_count = len(progress_df[progress_df['project_id'] == project['id']])
        
        progress_data.append({
            'project_id': project['id'],
            'project_name': project['name'],
            'latest_progress': latest_pct,
            'progress_updates_count': progress_count
        })
    
    progress_df_analytics = pd.DataFrame(progress_data)
    avg_progress = progress_df_analytics['latest_progress'].mean()
    
    return {
        'avg_progress': avg_progress,
        'total_progress_updates': len(progress_df),
        'progress_data': progress_data
    }

# Calculate
progress_analytics = calculate_progress_analytics(df_projects, df_progress)

print("=" * 70)
print("5️⃣ PROGRESS ANALYTICS")
print("=" * 70)
print(f"\nAverage Progress: {progress_analytics['avg_progress']:.1f}%")
print(f"Total Progress Updates: {progress_analytics['total_progress_updates']}")
print(f"\nTop 10 Projects by Progress:")
progress_df_viz = pd.DataFrame(progress_analytics['progress_data'])
top_progress = progress_df_viz.nlargest(10, 'latest_progress')
for i, (_, row) in enumerate(top_progress.iterrows(), 1):
    print(f"  {i:2}. {row['project_name'][:40]:40} {row['latest_progress']:5.1f}% ({row['progress_updates_count']} updates)")

# ============================================================================
# CELL 15: Visualize Progress Analytics
# ============================================================================
# Visualize progress analytics
progress_df_viz = pd.DataFrame(progress_analytics['progress_data'])

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Chart 1: Progress Distribution Histogram
axes[0, 0].hist(progress_df_viz['latest_progress'], bins=20, color='steelblue', alpha=0.7, edgecolor='black')
axes[0, 0].axvline(progress_analytics['avg_progress'], color='red', linestyle='--', linewidth=2, label=f'Average: {progress_analytics["avg_progress"]:.1f}%')
axes[0, 0].set_xlabel('Progress Percentage', fontweight='bold')
axes[0, 0].set_ylabel('Number of Projects', fontweight='bold')
axes[0, 0].set_title('Progress Distribution', fontweight='bold', fontsize=14)
axes[0, 0].legend()
axes[0, 0].grid(axis='y', alpha=0.3)

# Chart 2: Top 15 Projects by Progress
top_15_progress = progress_df_viz.nlargest(15, 'latest_progress').sort_values('latest_progress', ascending=True)
axes[0, 1].barh(range(len(top_15_progress)), top_15_progress['latest_progress'], color='green', alpha=0.8)
axes[0, 1].set_yticks(range(len(top_15_progress)))
axes[0, 1].set_yticklabels([name[:25] + '...' if len(name) > 25 else name for name in top_15_progress['project_name']], fontsize=8)
axes[0, 1].set_xlabel('Progress (%)', fontweight='bold')
axes[0, 1].set_title('Top 15 Projects by Progress', fontweight='bold', fontsize=14)
axes[0, 1].grid(axis='x', alpha=0.3)

# Chart 3: Progress Updates Count Distribution
axes[1, 0].hist(progress_df_viz['progress_updates_count'], bins=15, color='orange', alpha=0.7, edgecolor='black')
axes[1, 0].set_xlabel('Number of Progress Updates', fontweight='bold')
axes[1, 0].set_ylabel('Number of Projects', fontweight='bold')
axes[1, 0].set_title('Progress Updates Distribution', fontweight='bold', fontsize=14)
axes[1, 0].grid(axis='y', alpha=0.3)

# Chart 4: Progress vs Updates Scatter
axes[1, 1].scatter(progress_df_viz['progress_updates_count'], progress_df_viz['latest_progress'], 
                   alpha=0.6, s=50, color='purple')
axes[1, 1].set_xlabel('Number of Progress Updates', fontweight='bold')
axes[1, 1].set_ylabel('Latest Progress (%)', fontweight='bold')
axes[1, 1].set_title('Progress vs Number of Updates', fontweight='bold', fontsize=14)
axes[1, 1].grid(alpha=0.3)

plt.tight_layout()
plt.show()

# ============================================================================
# CELL 16: 6️⃣ TIMELINE ANALYTICS
# ============================================================================
def calculate_timeline_analytics(projects_df, progress_df):
    """Calculate timeline analytics"""
    from datetime import date
    today = date.today()
    
    projects_with_dates = projects_df[
        projects_df['start_date'].notna() & projects_df['end_date'].notna()
    ].copy()
    
    timeline_stats = {
        'total_with_dates': len(projects_with_dates),
        'on_time': 0,
        'delayed': 0,
        'upcoming': 0,
        'avg_duration_days': 0
    }
    
    durations = []
    for _, project in projects_with_dates.iterrows():
        if pd.notna(project['end_date']):
            end_date = project['end_date'].date() if hasattr(project['end_date'], 'date') else project['end_date']
            
            if end_date < today:
                # Check if completed or delayed
                project_progress = progress_df[progress_df['project_id'] == project['id']]
                if len(project_progress) > 0:
                    latest_progress = project_progress.sort_values('date').iloc[-1]
                    if latest_progress['percentage_complete'] >= 99:
                        timeline_stats['on_time'] += 1
                    else:
                        timeline_stats['delayed'] += 1
                else:
                    timeline_stats['delayed'] += 1
            else:
                timeline_stats['upcoming'] += 1
            
            if pd.notna(project['start_date']):
                start_date = project['start_date'].date() if hasattr(project['start_date'], 'date') else project['start_date']
                duration = (end_date - start_date).days
                durations.append(duration)
    
    if durations:
        timeline_stats['avg_duration_days'] = sum(durations) / len(durations)
    
    return timeline_stats

# Calculate
timeline_analytics = calculate_timeline_analytics(df_projects, df_progress)

print("=" * 70)
print("6️⃣ TIMELINE ANALYTICS")
print("=" * 70)
print(f"\nProjects with dates: {timeline_analytics['total_with_dates']}")
print(f"On time (completed): {timeline_analytics['on_time']}")
print(f"Delayed: {timeline_analytics['delayed']}")
print(f"Upcoming: {timeline_analytics['upcoming']}")
print(f"Average duration: {timeline_analytics['avg_duration_days']:.1f} days")

# ============================================================================
# CELL 17: 7️⃣ INTEGRATED ANALYTICS SUMMARY
# ============================================================================
print("=" * 70)
print("7️⃣ INTEGRATED ANALYTICS SUMMARY")
print("=" * 70)
print("\n📊 COMPREHENSIVE OVERVIEW:")
print(f"\n1. ZONING: {zoning_analytics['total_projects_with_zones']} projects with zones")
print(f"2. CLUSTERING: {clustering_analytics['total_clusters']} barangay clusters")
print(f"3. FINANCIAL: ${financial_analytics['total_budget']:,.2f} total budget, {financial_analytics['utilization_percentage']:.1f}% utilized")
print(f"4. STATUS: {len(status_analytics['distribution'])} different statuses")
print(f"5. PROGRESS: {progress_analytics['avg_progress']:.1f}% average progress")
print(f"6. TIMELINE: {timeline_analytics['total_with_dates']} projects with dates")

print("\n✅ All analytics calculated successfully!")

# ============================================================================
# CELL 18: Compare with Original JSON (Optional)
# ============================================================================
if analytics_json:
    print("📄 Loading original analytics JSON for comparison...")
    with open(analytics_json[0], 'r') as f:
        original_analytics = json.load(f)
    
    print("\n✅ Original analytics loaded!")
    print("\n📊 Comparison Results:")
    
    # Compare key metrics
    print(f"\nTotal Projects:")
    print(f"  Original: {original_analytics['total_projects']}")
    print(f"  Colab: {len(df_projects)}")
    print(f"  Match: {'✅' if original_analytics['total_projects'] == len(df_projects) else '❌'}")
    
    if 'zoning_analytics' in original_analytics:
        print(f"\nZoning Analytics:")
        print(f"  Original zones: {len(original_analytics['zoning_analytics']['zones'])}")
        print(f"  Colab zones: {len(zoning_analytics['zones'])}")
        print(f"  Match: {'✅' if len(original_analytics['zoning_analytics']['zones']) == len(zoning_analytics['zones']) else '❌'}")
    
    if 'financial_analytics' in original_analytics:
        print(f"\nFinancial Analytics:")
        orig_budget = original_analytics['financial_analytics']['total_budget']
        colab_budget = financial_analytics['total_budget']
        print(f"  Original budget: ${orig_budget:,.2f}")
        print(f"  Colab budget: ${colab_budget:,.2f}")
        print(f"  Match: {'✅' if abs(orig_budget - colab_budget) < 0.01 else '❌'}")
else:
    print("⚠️  No original analytics JSON uploaded. Skipping comparison.")

# ============================================================================
# CELL 19: Export Results
# ============================================================================
# Export all analytics results
results = {
    'zoning_analytics': zoning_analytics,
    'clustering_analytics': clustering_analytics,
    'financial_analytics': {
        'total_budget': financial_analytics['total_budget'],
        'total_spent': financial_analytics['total_spent'],
        'remaining_budget': financial_analytics['remaining_budget'],
        'utilization_percentage': financial_analytics['utilization_percentage'],
        'cost_by_type': financial_analytics['cost_by_type']
    },
    'status_analytics': status_analytics,
    'progress_analytics': {
        'avg_progress': progress_analytics['avg_progress'],
        'total_progress_updates': progress_analytics['total_progress_updates']
    },
    'timeline_analytics': timeline_analytics
}

# Save to JSON
output_filename = 'colab_analytics_results.json'
with open(output_filename, 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f"✅ Results exported to {output_filename}")
print("\n📥 Download the results file:")
files.download(output_filename)

print("\n🎉 All analytics testing complete!")

