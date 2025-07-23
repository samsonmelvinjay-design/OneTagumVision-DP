from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from projeng.models import Project, ProjectCost
from django.db.models import Sum
from collections import defaultdict
from django.db.models.functions import TruncMonth

def is_finance_manager(user):
    return user.is_authenticated and user.groups.filter(name='Finance Manager').exists()

def is_head_engineer(user):
    return user.is_authenticated and user.groups.filter(name='Head Engineer').exists()

def is_finance_or_head_engineer(user):
    return is_finance_manager(user) or is_head_engineer(user)

@user_passes_test(is_finance_or_head_engineer, login_url='/accounts/login/')
def finance_dashboard(request):
    projects = Project.objects.all()
    total_budget = projects.aggregate(total=Sum('project_cost'))['total'] or 0
    total_spent = ProjectCost.objects.aggregate(total=Sum('amount'))['total'] or 0
    remaining = total_budget - total_spent
    # Bar Chart: Top 10 projects by budget
    project_financials = []
    for project in projects:
        spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
        project_financials.append({
            'name': project.name,
            'budget': float(project.project_cost or 0),
            'spent': float(spent),
        })
    top_projects = sorted(project_financials, key=lambda x: x['budget'], reverse=True)[:10]
    project_names = [p['name'] for p in top_projects]
    project_budgets = [p['budget'] for p in top_projects]
    project_spent = [p['spent'] for p in top_projects]
    # Pie Chart: Spending by cost type
    cost_by_type = defaultdict(float)
    for cost in ProjectCost.objects.all():
        cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
    # Line Chart: Cumulative spending over time (by month)
    monthly_spending = (
        ProjectCost.objects
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    months = [m['month'].strftime('%b %Y') for m in monthly_spending]
    monthly_totals = [float(m['total']) for m in monthly_spending]
    cumulative = []
    running = 0
    for amt in monthly_totals:
        running += amt
        cumulative.append(running)
    # Doughnut Chart: Budget utilization
    utilization_data = [float(total_spent), float(remaining)]
    context = {
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining': remaining,
        'project_names': project_names,
        'project_budgets': project_budgets,
        'project_spent': project_spent,
        'cost_by_type': dict(cost_by_type),
        'months': months,
        'cumulative': cumulative,
        'utilization_data': utilization_data,
    }
    return render(request, 'finance_manager/finance_dashboard.html', context)

@user_passes_test(is_finance_or_head_engineer, login_url='/accounts/login/')
def finance_projects(request):
    # Filters
    barangay_filter = request.GET.get('barangay')
    status_filter = request.GET.get('status')
    projects = Project.objects.all()
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    if status_filter:
        projects = projects.filter(status=status_filter)
    # List of projects with their financials
    project_financials = []
    for project in projects:
        spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
        remaining_proj = (project.project_cost or 0) - spent
        project_financials.append({
            'name': project.name,
            'barangay': project.barangay,
            'budget': project.project_cost or 0,
            'spent': spent,
            'remaining': remaining_proj,
            'status': project.status,
        })
    # Sort by budget and take top 10 for chart
    top_projects = sorted(project_financials, key=lambda x: x['budget'], reverse=True)[:10]
    project_names = [p['name'] for p in top_projects]
    project_budgets = [float(p['budget']) for p in top_projects]
    project_spent = [float(p['spent']) for p in top_projects]
    # Cost breakdown by type (for pie chart)
    cost_by_type = defaultdict(float)
    for cost in ProjectCost.objects.filter(project__in=projects):
        cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
    # Hardcoded list of 23 barangays
    all_barangays = [
        'Apokon', 'Bincungan', 'Busaon', 'Canocotan', 'Cuambogan', 'La Filipina', 'Liboganon',
        'Madaum', 'Magdum', 'Magugpo East', 'Magugpo North', 'Magugpo Poblacion', 'Magugpo South',
        'Magugpo West', 'Mankilam', 'New Balamban', 'Nueva Fuerza', 'Pagsabangan', 'Pandapan',
        'San Agustin', 'San Isidro', 'San Miguel', 'Visayan Village'
    ]
    all_statuses = [s[0] for s in Project.STATUS_CHOICES if s[0] != 'cancelled']
    context = {
        'project_financials': project_financials,
        'project_names': project_names,
        'project_budgets': project_budgets,
        'project_spent': project_spent,
        'cost_by_type': dict(cost_by_type),
        'all_barangays': all_barangays,
        'all_statuses': all_statuses,
        'selected_barangay': barangay_filter or '',
        'selected_status': status_filter or '',
    }
    return render(request, 'finance_manager/finance_projects.html', context)

@user_passes_test(is_finance_or_head_engineer, login_url='/accounts/login/')
def finance_cost_management(request):
    # Filters
    prn_filter = request.GET.get('prn')
    barangay_filter = request.GET.get('barangay')
    budget_status_filter = request.GET.get('budget_status')
    projects = Project.objects.all()
    if prn_filter:
        projects = projects.filter(prn__icontains=prn_filter)
    if barangay_filter:
        projects = projects.filter(barangay=barangay_filter)
    # Prepare financials
    project_financials = []
    over_budget_count = 0
    within_budget_count = 0
    under_budget_count = 0
    for project in projects:
        spent = ProjectCost.objects.filter(project=project).aggregate(total=Sum('amount'))['total'] or 0
        budget = project.project_cost or 0
        remaining = budget - spent
        if spent > budget:
            budget_status = 'over'
            over_budget_count += 1
        elif spent == budget:
            budget_status = 'within'
            within_budget_count += 1
        else:
            budget_status = 'under'
            under_budget_count += 1
        project_financials.append({
            'id': project.id,
            'prn': project.prn,
            'name': project.name,
            'barangay': project.barangay,
            'budget': float(budget),
            'spent': float(spent),
            'remaining': float(remaining),
            'budget_status': budget_status,
        })
    # Apply budget status filter
    if budget_status_filter:
        project_financials = [p for p in project_financials if p['budget_status'] == budget_status_filter]
    total_projects = len(project_financials)
    # For filters
    all_projects = Project.objects.all()
    all_barangays = [
        'Apokon', 'Bincungan', 'Busaon', 'Canocotan', 'Cuambogan', 'La Filipina', 'Liboganon',
        'Madaum', 'Magdum', 'Magugpo East', 'Magugpo North', 'Magugpo Poblacion', 'Magugpo South',
        'Magugpo West', 'Mankilam', 'New Balamban', 'Nueva Fuerza', 'Pagsabangan', 'Pandapan',
        'San Agustin', 'San Isidro', 'San Miguel', 'Visayan Village'
    ]
    context = {
        'project_financials': project_financials,
        'total_projects': total_projects,
        'over_budget_count': over_budget_count,
        'within_budget_count': within_budget_count,
        'under_budget_count': under_budget_count,
        'all_projects': all_projects,
        'all_barangays': all_barangays,
        'selected_prn': prn_filter or '',
        'selected_barangay': barangay_filter or '',
        'selected_budget_status': budget_status_filter or '',
    }
    return render(request, 'finance_manager/finance_cost_management.html', context)

@user_passes_test(is_finance_or_head_engineer, login_url='/accounts/login/')
def finance_notifications(request):
    return render(request, 'finance_manager/finance_notifications.html')

@user_passes_test(is_finance_or_head_engineer, login_url='/accounts/login/')
def finance_project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    costs = ProjectCost.objects.filter(project=project).order_by('-date')
    total_spent = costs.aggregate(total=Sum('amount'))['total'] or 0
    remaining = (project.project_cost or 0) - total_spent
    cost_by_type = defaultdict(float)
    for cost in costs:
        cost_by_type[cost.get_cost_type_display()] += float(cost.amount)
    context = {
        'project': project,
        'costs': costs,
        'total_spent': total_spent,
        'remaining': remaining,
        'cost_by_type': dict(cost_by_type),
    }
    return render(request, 'finance_manager/finance_project_detail.html', context) 