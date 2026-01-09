"""
Zone Analytics Algorithm Testing - Google Colab
================================================

Copy each section into separate cells in Google Colab.
This tests the Zone Analytics aggregation algorithm used in the dashboard.

Instructions:
1. Upload your projects_zone_data_YYYYMMDD_HHMMSS.csv file
2. Copy each section into a separate Colab cell
3. Run all cells in order
4. Compare results with your exported JSON file
"""

# ============================================================================
# CELL 1: Install Libraries
# ============================================================================
# Install required libraries
!pip install pandas matplotlib seaborn numpy

# ============================================================================
# CELL 2: Import Libraries
# ============================================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
import json

# Set style for better visualizations
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("=" * 70)
print("ZONE ANALYTICS ALGORITHM TESTING")
print("=" * 70)
print("\n✅ Libraries installed and imported successfully!")

# ============================================================================
# CELL 3: Zone Configuration
# ============================================================================
# Zone type display names mapping
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

# Zone colors (matching your dashboard)
ZONE_COLORS = {
    'R-1': '#FFF9C4',  # Very light yellow
    'R-2': '#FFF59D',  # Light yellow
    'R-3': '#FDD835',  # Yellow
    'SHZ': '#C5E1A5',  # Light green-yellow
    'C-1': '#FF6F00',  # Deep orange
    'C-2': '#FFB74D',  # Light orange
    'I-1': '#BA68C8',  # Purple
    'I-2': '#CE93D8',  # Light purple
    'AGRO': '#9CCC65', # Light green
    'INS-1': '#7986CB', # Indigo/purple-blue
    'PARKS': '#66BB6A', # Medium green
    'AGRICULTURAL': '#81C784', # Green
    'ECO-TOURISM': '#26A69A', # Teal
    'SPECIAL': '#A1887F', # Brown
}

print("✅ Zone configuration loaded")

# ============================================================================
# CELL 4: Upload CSV File
# ============================================================================
from google.colab import files

print("Please upload your projects_zone_data CSV file:")
uploaded = files.upload()

# Get the filename
csv_filename = list(uploaded.keys())[0]
print(f"\n✅ File uploaded: {csv_filename}")

# ============================================================================
# CELL 5: Load Data
# ============================================================================
# Load the data
df_projects = pd.read_csv(csv_filename)

print(f"✅ Loaded {len(df_projects)} projects from CSV")
print(f"\n📊 Data Preview:")
print(df_projects.head(10))
print(f"\n📈 Zone Types in Data:")
print(df_projects['zone_type'].value_counts().sort_index())
print(f"\n📋 Data Info:")
print(df_projects.info())

# ============================================================================
# CELL 6: Algorithm Implementation
# ============================================================================
def get_zone_display_name(zone_type):
    """Helper function to get display name for zone type"""
    return ZONE_DISPLAY_NAMES.get(zone_type, zone_type)

def zone_analytics_algorithm(projects_df):
    """
    Zone Analytics Aggregation Algorithm
    
    This replicates the Django ORM aggregation logic:
    - Filters projects with zone_type (not null/empty)
    - Groups by zone_type
    - Aggregates: total_projects, completed, in_progress, planned, delayed, total_cost
    
    Args:
        projects_df: DataFrame with columns: zone_type, status, project_cost
        
    Returns:
        List of dictionaries with zone statistics
    """
    # Step 1: Filter projects with zone_type (not null/empty)
    # Equivalent to: Project.objects.filter(zone_type__isnull=False).exclude(zone_type='')
    projects_with_zones = projects_df[
        (projects_df['zone_type'].notna()) & 
        (projects_df['zone_type'] != '')
    ].copy()
    
    if len(projects_with_zones) == 0:
        return []
    
    # Step 2: Aggregate by zone_type
    # Equivalent to Django's .values('zone_type').annotate(...)
    zones = []
    
    for zone_type in projects_with_zones['zone_type'].unique():
        zone_projects = projects_with_zones[projects_with_zones['zone_type'] == zone_type]
        
        # Count total projects
        total_projects = len(zone_projects)
        
        # Count by status (matching Django Q() filters)
        completed = len(zone_projects[zone_projects['status'] == 'completed'])
        in_progress = len(zone_projects[
            zone_projects['status'].isin(['in_progress', 'ongoing'])
        ])
        planned = len(zone_projects[
            zone_projects['status'].isin(['planned', 'pending'])
        ])
        delayed = len(zone_projects[zone_projects['status'] == 'delayed'])
        
        # Sum project costs
        total_cost = zone_projects['project_cost'].sum()
        
        zones.append({
            'zone_type': zone_type,
            'display_name': get_zone_display_name(zone_type),
            'total_projects': total_projects,
            'completed': completed,
            'in_progress': in_progress,
            'planned': planned,
            'delayed': delayed,
            'total_cost': float(total_cost)
        })
    
    # Step 3: Order by zone_type (matching .order_by('zone_type'))
    zones.sort(key=lambda x: x['zone_type'])
    
    return zones

print("✅ Algorithm functions defined")

# ============================================================================
# CELL 7: Run Algorithm
# ============================================================================
# Run the algorithm
zone_analytics = zone_analytics_algorithm(df_projects)

print("=" * 70)
print("ALGORITHM EXECUTION RESULTS")
print("=" * 70)
print(f"\n✅ Algorithm processed {len(df_projects)} projects")
print(f"✅ Found {len(zone_analytics)} unique zone types\n")

# Display results
for zone in zone_analytics:
    print(f"📍 {zone['zone_type']} ({zone['display_name']}):")
    print(f"   Total Projects: {zone['total_projects']}")
    print(f"   ├─ Completed: {zone['completed']}")
    print(f"   ├─ In Progress: {zone['in_progress']}")
    print(f"   ├─ Planned: {zone['planned']}")
    print(f"   ├─ Delayed: {zone['delayed']}")
    print(f"   └─ Total Cost: ${zone['total_cost']:,.2f}")
    print()

# ============================================================================
# CELL 8: Create Visualization
# ============================================================================
def create_zone_analytics_chart(zone_data):
    """
    Create bar chart matching the dashboard visualization
    """
    # Prepare data
    zones_df = pd.DataFrame(zone_data)
    zones_df = zones_df.sort_values('total_projects', ascending=True)
    
    # Get colors for each zone
    colors = [ZONE_COLORS.get(zt, '#CCCCCC') for zt in zones_df['zone_type']]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create horizontal bar chart (easier to read zone names)
    bars = ax.barh(zones_df['zone_type'], zones_df['total_projects'], color=colors, 
                   edgecolor='black', linewidth=0.5, alpha=0.8)
    
    # Customize chart
    ax.set_xlabel('Number of Projects', fontsize=12, fontweight='bold')
    ax.set_ylabel('Zone Type', fontsize=12, fontweight='bold')
    ax.set_title('Projects by Zone Type\n(Zone Analytics Algorithm Results)', 
                 fontsize=14, fontweight='bold', pad=20)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, zones_df['total_projects'])):
        ax.text(value + 0.5, i, f'{int(value)}', 
                va='center', fontweight='bold', fontsize=10)
    
    # Set x-axis to start at 0 and show integers
    ax.set_xlim(0, zones_df['total_projects'].max() * 1.15)
    ax.set_xticks(range(0, int(zones_df['total_projects'].max()) + 5, 5))
    
    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # Tight layout
    plt.tight_layout()
    
    return fig, ax

# Create and display chart
fig, ax = create_zone_analytics_chart(zone_analytics)
plt.show()

print("\n✅ Chart created successfully!")

# ============================================================================
# CELL 9: Detailed Analytics
# ============================================================================
def display_detailed_analytics(zone_data):
    """Display comprehensive analytics breakdown"""
    zones_df = pd.DataFrame(zone_data)
    
    print("=" * 70)
    print("DETAILED ANALYTICS BREAKDOWN")
    print("=" * 70)
    
    # Overall statistics
    total_projects = zones_df['total_projects'].sum()
    total_cost = zones_df['total_cost'].sum()
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Total Projects: {total_projects}")
    print(f"   Total Cost: ${total_cost:,.2f}")
    print(f"   Average Cost per Project: ${total_cost/total_projects:,.2f}")
    print(f"   Unique Zone Types: {len(zones_df)}")
    
    # Status breakdown
    print(f"\n📈 STATUS BREAKDOWN:")
    print(f"   Completed: {zones_df['completed'].sum()} ({zones_df['completed'].sum()/total_projects*100:.1f}%)")
    print(f"   In Progress: {zones_df['in_progress'].sum()} ({zones_df['in_progress'].sum()/total_projects*100:.1f}%)")
    print(f"   Planned: {zones_df['planned'].sum()} ({zones_df['planned'].sum()/total_projects*100:.1f}%)")
    print(f"   Delayed: {zones_df['delayed'].sum()} ({zones_df['delayed'].sum()/total_projects*100:.1f}%)")
    
    # Top zones by project count
    print(f"\n🏆 TOP 5 ZONES BY PROJECT COUNT:")
    top_zones = zones_df.nlargest(5, 'total_projects')
    for idx, row in top_zones.iterrows():
        print(f"   {row['zone_type']}: {row['total_projects']} projects (${row['total_cost']:,.2f})")
    
    # Top zones by cost
    print(f"\n💰 TOP 5 ZONES BY TOTAL COST:")
    top_cost = zones_df.nlargest(5, 'total_cost')
    for idx, row in top_cost.iterrows():
        print(f"   {row['zone_type']}: ${row['total_cost']:,.2f} ({row['total_projects']} projects)")
    
    # Create comparison chart
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Chart 1: Projects by Status
    status_data = {
        'Completed': zones_df['completed'].sum(),
        'In Progress': zones_df['in_progress'].sum(),
        'Planned': zones_df['planned'].sum(),
        'Delayed': zones_df['delayed'].sum()
    }
    axes[0].bar(status_data.keys(), status_data.values(), 
                color=['#4CAF50', '#2196F3', '#FF9800', '#F44336'], alpha=0.8)
    axes[0].set_title('Projects by Status (All Zones)', fontweight='bold')
    axes[0].set_ylabel('Number of Projects')
    axes[0].grid(axis='y', alpha=0.3)
    
    # Chart 2: Cost Distribution by Zone
    zones_df_sorted = zones_df.sort_values('total_cost', ascending=True)
    axes[1].barh(zones_df_sorted['zone_type'], zones_df_sorted['total_cost']/1e6,
                 color=[ZONE_COLORS.get(zt, '#CCCCCC') for zt in zones_df_sorted['zone_type']],
                 alpha=0.8)
    axes[1].set_title('Total Cost by Zone (Millions)', fontweight='bold')
    axes[1].set_xlabel('Cost (Millions $)')
    axes[1].grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.show()

display_detailed_analytics(zone_analytics)

# ============================================================================
# CELL 10: Algorithm Testing
# ============================================================================
def test_algorithm_correctness(projects_df, zone_analytics_result):
    """
    Test the algorithm for correctness
    """
    print("=" * 70)
    print("ALGORITHM TESTING & VALIDATION")
    print("=" * 70)
    
    # Test 1: Filter logic
    print("\n✅ Test 1: Filter Logic")
    projects_with_zones = projects_df[
        (projects_df['zone_type'].notna()) & 
        (projects_df['zone_type'] != '')
    ]
    print(f"   Projects with zones: {len(projects_with_zones)}/{len(projects_df)}")
    
    # Test 2: Aggregation accuracy
    print("\n✅ Test 2: Aggregation Accuracy")
    
    all_tests_passed = True
    for zone in zone_analytics_result:
        zone_projects = projects_df[projects_df['zone_type'] == zone['zone_type']]
        
        # Verify counts
        if zone['total_projects'] != len(zone_projects):
            print(f"   ❌ Count mismatch for {zone['zone_type']}")
            all_tests_passed = False
            continue
        
        completed_count = len(zone_projects[zone_projects['status'] == 'completed'])
        if zone['completed'] != completed_count:
            print(f"   ❌ Completed count mismatch for {zone['zone_type']}")
            all_tests_passed = False
            continue
        
        in_progress_count = len(zone_projects[
            zone_projects['status'].isin(['in_progress', 'ongoing'])
        ])
        if zone['in_progress'] != in_progress_count:
            print(f"   ❌ In progress count mismatch for {zone['zone_type']}")
            all_tests_passed = False
            continue
        
        cost_sum = zone_projects['project_cost'].sum()
        if abs(zone['total_cost'] - cost_sum) > 0.01:
            print(f"   ❌ Cost mismatch for {zone['zone_type']}")
            all_tests_passed = False
            continue
        
        print(f"   ✓ {zone['zone_type']}: All aggregations correct")
    
    # Test 3: Edge cases
    print("\n✅ Test 3: Edge Cases")
    
    # Empty dataframe
    empty_df = pd.DataFrame(columns=['zone_type', 'status', 'project_cost'])
    empty_result = zone_analytics_algorithm(empty_df)
    if len(empty_result) != 0:
        print("   ❌ Empty dataframe should return empty result")
        all_tests_passed = False
    else:
        print("   ✓ Empty dataframe handled correctly")
    
    if all_tests_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please review the results above.")
    
    return all_tests_passed

# Run tests
test_algorithm_correctness(df_projects, zone_analytics)

# ============================================================================
# CELL 11: Export Results
# ============================================================================
def export_results_json(zone_data, filename='zone_analytics_results.json'):
    """Export results in the same format as the Django API"""
    from datetime import datetime
    
    output = {
        'export_date': datetime.now().isoformat(),
        'total_projects': sum(z['total_projects'] for z in zone_data),
        'zones': zone_data
    }
    
    # Save to JSON
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✅ Results exported to {filename}")
    print("\n📄 JSON Output (matching API format):")
    print(json.dumps(output, indent=2))
    
    return output

# Export results
api_format_output = export_results_json(zone_analytics)

# Also create a DataFrame export
df_zones = pd.DataFrame(zone_analytics)
df_zones.to_csv('zone_analytics_results.csv', index=False)
print("\n✅ Results also exported to zone_analytics_results.csv")

# Download the files
files.download('zone_analytics_results.json')
files.download('zone_analytics_results.csv')

# ============================================================================
# CELL 12: Compare with Original JSON (Optional)
# ============================================================================
# Optional: Upload your original JSON export to compare
print("Optional: Upload your zone_analytics JSON file to compare results:")
print("(Press Cancel if you don't want to compare)")

try:
    uploaded_json = files.upload()
    json_filename = list(uploaded_json.keys())[0]
    
    # Load original JSON
    with open(json_filename, 'r') as f:
        original_data = json.load(f)
    
    print(f"\n✅ Loaded original JSON: {json_filename}")
    
    # Compare results
    print("\n" + "=" * 70)
    print("COMPARISON: Colab Results vs Original JSON")
    print("=" * 70)
    
    original_zones = {z['zone_type']: z for z in original_data['zones']}
    colab_zones = {z['zone_type']: z for z in zone_analytics}
    
    all_match = True
    for zone_type in set(list(original_zones.keys()) + list(colab_zones.keys())):
        if zone_type in original_zones and zone_type in colab_zones:
            orig = original_zones[zone_type]
            colab = colab_zones[zone_type]
            
            if orig['total_projects'] == colab['total_projects']:
                print(f"✅ {zone_type}: Projects match ({orig['total_projects']})")
            else:
                print(f"❌ {zone_type}: Projects mismatch (Original: {orig['total_projects']}, Colab: {colab['total_projects']})")
                all_match = False
        elif zone_type in original_zones:
            print(f"⚠️  {zone_type}: Only in original JSON")
            all_match = False
        else:
            print(f"⚠️  {zone_type}: Only in Colab results")
            all_match = False
    
    if all_match:
        print("\n🎉 All results match perfectly!")
    else:
        print("\n⚠️  Some differences found. Please review above.")
        
except:
    print("\n⚠️  No JSON file uploaded. Skipping comparison.")



