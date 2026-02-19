# Budget Notification System - Implementation Plan

## 📋 Overview
This document outlines the complete implementation plan for a hierarchical budget notification system where:
- **Project Engineers** → Notify **Head Engineers** about budget concerns
- **Head Engineers** → Notify **Finance Managers** after review
- Automatic notifications trigger at budget thresholds (80%, 95%, 100%)

---

## 🎯 Core Requirements

### 1. **Budget Thresholds**
- **80% threshold**: Early warning (Project Engineer → Head Engineer)
- **95% threshold**: Critical alert (Project Engineer → Head Engineer, then Head → Finance)
- **100% threshold**: Over budget (Project Engineer → Head Engineer, then Head → Finance)

### 2. **User Permissions**
- **Project Engineers**: Can add costs, send manual budget alerts, **CANNOT** update budgets
- **Head Engineers**: Can add costs, receive alerts, update budgets, forward alerts to Finance
- **Finance Managers**: Can add costs, receive alerts, update budgets, view all financial data

### 3. **Notification Types**
- **Automatic**: Triggered when cost entries cross thresholds
- **Manual**: Project Engineers can proactively send budget concerns
- **Forwarded**: Head Engineers can forward alerts to Finance with their assessment

---

## 🗄️ Database Changes

### Option 1: Enhance Existing Notification Model (Recommended)
**No migration needed** - Use existing `Notification` model with enhanced message structure.

**Add to `projeng/models.py`:**
```python
# Add notification type tracking (optional enhancement)
class BudgetNotification(models.Model):
    """Track budget-related notifications for audit trail"""
    notification = models.OneToOneField(Notification, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    budget_utilization = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    threshold_type = models.CharField(max_length=20, choices=[
        ('warning', 'Warning (80%)'),
        ('critical', 'Critical (95%)'),
        ('over', 'Over Budget (100%+)'),
        ('manual', 'Manual Alert'),
    ])
    forwarded_to_finance = models.BooleanField(default=False)
    forwarded_at = models.DateTimeField(null=True, blank=True)
    forwarded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
```

**OR Option 2: Keep it Simple**
- Use existing `Notification` model only
- Include all information in the message text
- Track forwarding via message content patterns

**Recommendation**: Start with Option 2 (simpler), add Option 1 later if audit trail becomes critical.

---

## 🔧 Implementation Components

### 1. **Enhanced Budget Checking Function**

**File**: `projeng/signals.py`

**Enhance `check_budget_over_utilization()` function:**

```python
def check_budget_thresholds(project, cost_entry=None):
    """
    Check project budget against thresholds and trigger appropriate notifications.
    
    Thresholds:
    - 80%: Warning to Head Engineers
    - 95%: Critical alert to Head Engineers
    - 100%+: Over budget alert to Head Engineers
    
    Args:
        project: Project instance
        cost_entry: Optional ProjectCost instance that triggered the check
    """
    from django.db.models import Sum
    from .models import ProjectCost
    from .utils import notify_head_engineers
    
    # Only check if project has a budget set
    if not project.project_cost:
        return
    
    # Calculate total costs
    total_costs = ProjectCost.objects.filter(project=project).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Convert to float for comparison
    try:
        total_costs_float = float(total_costs)
        project_budget_float = float(project.project_cost)
    except (ValueError, TypeError):
        return
    
    # Calculate utilization percentage
    utilization_percentage = (total_costs_float / project_budget_float) * 100 if project_budget_float > 0 else 0
    
    # Format amounts
    formatted_total = f"₱{total_costs_float:,.2f}"
    formatted_budget = f"₱{project_budget_float:,.2f}"
    formatted_remaining = f"₱{max(0, project_budget_float - total_costs_float):,.2f}"
    
    project_display = format_project_display(project)
    
    # Get cost entry creator name if available
    creator_name = "System"
    if cost_entry and cost_entry.created_by:
        creator_name = cost_entry.created_by.get_full_name() or cost_entry.created_by.username
    
    # Check thresholds (only notify once per threshold level)
    # Use a flag on the project to track which thresholds have been notified
    
    # 100%+ threshold: Over budget
    if total_costs_float > project_budget_float:
        overage_amount = total_costs_float - project_budget_float
        overage_percentage = ((total_costs_float / project_budget_float) - 1) * 100
        formatted_overage = f"₱{overage_amount:,.2f}"
        
        message = (
            f"🚨 URGENT: {project_display} is OVER BUDGET by {formatted_overage} "
            f"({overage_percentage:.1f}% over). "
            f"Total spent: {formatted_total} | Budget: {formatted_budget}. "
            f"Cost entry by: {creator_name}. "
            f"Immediate review required."
        )
        notify_head_engineers(message, check_duplicates=True)
    
    # 95% threshold: Critical alert
    elif utilization_percentage >= 95:
        message = (
            f"⚠️ CRITICAL: {project_display} is at {utilization_percentage:.1f}% of budget. "
            f"Spent: {formatted_total} | Budget: {formatted_budget} | Remaining: {formatted_remaining}. "
            f"Cost entry by: {creator_name}. "
            f"Project may exceed budget soon. Review recommended."
        )
        notify_head_engineers(message, check_duplicates=True)
    
    # 80% threshold: Warning
    elif utilization_percentage >= 80:
        message = (
            f"⚠️ WARNING: {project_display} is at {utilization_percentage:.1f}% of budget. "
            f"Spent: {formatted_total} | Budget: {formatted_budget} | Remaining: {formatted_remaining}. "
            f"Cost entry by: {creator_name}. "
            f"Monitor spending closely."
        )
        notify_head_engineers(message, check_duplicates=True)
```

**Update `notify_cost_updates()` signal:**
```python
@receiver(post_save, sender=ProjectCost)
def notify_cost_updates(sender, instance, created, **kwargs):
    """Notify Head Engineers and Finance Managers about cost updates"""
    if created:
        # ... existing code ...
        
        # Replace old check_budget_over_utilization with new function
        check_budget_thresholds(instance.project, cost_entry=instance)
```

---

### 2. **Manual Notification System**

**File**: `projeng/utils.py`

**Add new function:**
```python
def notify_head_engineer_about_budget_concern(project, sender_user, message=None, utilization_percentage=None):
    """
    Allow Project Engineers to manually notify Head Engineers about budget concerns.
    
    Args:
        project: Project instance
        sender_user: User sending the notification (Project Engineer)
        message: Optional custom message
        utilization_percentage: Current budget utilization percentage
    """
    from django.db.models import Sum
    from .models import ProjectCost, Notification
    
    # Calculate current budget status if not provided
    if utilization_percentage is None:
        if not project.project_cost:
            return  # Can't calculate if no budget
        
        total_costs = ProjectCost.objects.filter(project=project).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        try:
            total_costs_float = float(total_costs)
            project_budget_float = float(project.project_cost)
            utilization_percentage = (total_costs_float / project_budget_float) * 100 if project_budget_float > 0 else 0
        except (ValueError, TypeError):
            utilization_percentage = 0
    
    project_display = format_project_display(project)
    sender_name = sender_user.get_full_name() or sender_user.username
    
    # Build notification message
    if message:
        notification_message = (
            f"📋 Budget Concern: {project_display} - {message} "
            f"(Current utilization: {utilization_percentage:.1f}%) "
            f"- Reported by {sender_name}"
        )
    else:
        notification_message = (
            f"📋 Budget Concern: {project_display} is at {utilization_percentage:.1f}% of budget. "
            f"Reported by {sender_name}. Please review."
        )
    
    # Notify all Head Engineers
    notify_head_engineers(notification_message, check_duplicates=True)
```

**Add function for Head Engineers to forward to Finance:**
```python
def forward_budget_alert_to_finance(project, head_engineer, assessment_message=None, requested_budget_increase=None):
    """
    Allow Head Engineers to forward budget alerts to Finance Managers with their assessment.
    
    Args:
        project: Project instance
        head_engineer: Head Engineer forwarding the alert
        assessment_message: Optional assessment/recommendation from Head Engineer
        requested_budget_increase: Optional requested budget increase amount
    """
    from django.db.models import Sum
    from .models import ProjectCost
    
    # Calculate current budget status
    total_costs = ProjectCost.objects.filter(project=project).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    try:
        total_costs_float = float(total_costs)
        project_budget_float = float(project.project_cost) or 0
        utilization_percentage = (total_costs_float / project_budget_float) * 100 if project_budget_float > 0 else 0
        remaining = project_budget_float - total_costs_float
    except (ValueError, TypeError):
        return
    
    project_display = format_project_display(project)
    head_engineer_name = head_engineer.get_full_name() or head_engineer.username
    
    formatted_total = f"₱{total_costs_float:,.2f}"
    formatted_budget = f"₱{project_budget_float:,.2f}"
    formatted_remaining = f"₱{max(0, remaining):,.2f}"
    
    # Build notification message
    if requested_budget_increase:
        formatted_increase = f"₱{float(requested_budget_increase):,.2f}"
        message = (
            f"💰 Budget Review Request: {project_display} "
            f"(Utilization: {utilization_percentage:.1f}% | Spent: {formatted_total} | Budget: {formatted_budget}). "
            f"Requested budget increase: {formatted_increase}. "
            f"Assessment from {head_engineer_name}: {assessment_message or 'Please review and approve.'}"
        )
    else:
        message = (
            f"💰 Budget Review Request: {project_display} "
            f"(Utilization: {utilization_percentage:.1f}% | Spent: {formatted_total} | Budget: {formatted_budget} | Remaining: {formatted_remaining}). "
            f"Assessment from {head_engineer_name}: {assessment_message or 'Please review.'}"
        )
    
    # Notify Finance Managers
    notify_finance_managers(message, check_duplicates=True)
```

---

### 3. **Views for Manual Notifications**

**File**: `projeng/views.py` (or create new file `projeng/views/budget_notifications.py`)

**Add view for Project Engineers to send manual alerts:**
```python
@login_required
@user_passes_test(is_project_or_head_engineer, login_url='/accounts/login/')
def send_budget_alert(request, project_id):
    """
    Allow Project Engineers to manually send budget alerts to Head Engineers.
    """
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from .models import Project
    from .utils import notify_head_engineer_about_budget_concern
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has access to this project
    if is_project_engineer(request.user) and project not in request.user.assigned_projects.all():
        messages.error(request, "You don't have access to this project.")
        return redirect('projeng:projeng_dashboard')
    
    if request.method == 'POST':
        custom_message = request.POST.get('message', '').strip()
        
        # Send notification
        notify_head_engineer_about_budget_concern(
            project=project,
            sender_user=request.user,
            message=custom_message if custom_message else None
        )
        
        messages.success(request, f"Budget alert sent to Head Engineers for project '{project.name}'.")
        return redirect('projeng:project_detail', pk=project_id)
    
    # GET request - show form (or handle via AJAX)
    messages.error(request, "Invalid request method.")
    return redirect('projeng:project_detail', pk=project_id)
```

**Add view for Head Engineers to forward to Finance:**
```python
@login_required
@head_engineer_required
def forward_budget_alert_to_finance_view(request, project_id):
    """
    Allow Head Engineers to forward budget alerts to Finance Managers.
    """
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from .models import Project
    from .utils import forward_budget_alert_to_finance
    
    project = get_object_or_404(Project, pk=project_id)
    
    if request.method == 'POST':
        assessment_message = request.POST.get('assessment_message', '').strip()
        requested_increase = request.POST.get('requested_budget_increase', '').strip()
        
        try:
            requested_increase_float = float(requested_increase) if requested_increase else None
        except ValueError:
            requested_increase_float = None
        
        # Forward notification
        forward_budget_alert_to_finance(
            project=project,
            head_engineer=request.user,
            assessment_message=assessment_message if assessment_message else None,
            requested_budget_increase=requested_increase_float
        )
        
        messages.success(request, f"Budget alert forwarded to Finance Managers for project '{project.name}'.")
        return redirect('monitoring:project_detail', pk=project_id)
    
    messages.error(request, "Invalid request method.")
    return redirect('monitoring:project_detail', pk=project_id)
```

---

### 4. **Budget Update Permissions**

**File**: `projeng/views.py` (or wherever project edit views are)

**Add permission check to budget update views:**
```python
def can_update_budget(user, project):
    """
    Check if user can update project budget.
    
    Rules:
    - Finance Managers: Can update any project budget
    - Head Engineers: Can update any project budget
    - Project Engineers: Cannot update budgets
    """
    from gistagum.access_control import is_finance_manager, is_head_engineer
    
    return is_finance_manager(user) or is_head_engineer(user)

# In project update view:
if 'project_cost' in request.POST:
    if not can_update_budget(request.user, project):
        messages.error(request, "You don't have permission to update project budgets.")
        return redirect(...)
    
    # Update budget with notification
    old_budget = project.project_cost
    new_budget = request.POST.get('project_cost')
    # ... update logic ...
    
    # Notify Finance if budget increased significantly
    if new_budget and old_budget:
        try:
            increase = float(new_budget) - float(old_budget)
            if increase > 0 and increase > (float(old_budget) * 0.1):  # >10% increase
                from .utils import notify_finance_managers
                message = f"Budget increased for {project.name}: ₱{old_budget:,.2f} → ₱{new_budget:,.2f} (Increase: ₱{increase:,.2f})"
                notify_finance_managers(message)
        except (ValueError, TypeError):
            pass
```

---

### 5. **UI Components**

#### A. **Project Detail Page - Budget Alert Button (Project Engineers)**
**File**: `templates/projeng/project_management.html`

Add button in budget section:
```html
<!-- Budget Alert Button (for Project Engineers) -->
{% if user|is_project_engineer %}
<div class="mt-4">
    <button type="button" 
            onclick="showBudgetAlertModal()"
            class="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg">
        📋 Send Budget Alert to Head Engineer
    </button>
</div>

<!-- Budget Alert Modal -->
<div id="budgetAlertModal" class="hidden fixed inset-0 bg-black bg-opacity-50 z-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 class="text-xl font-semibold mb-4">Send Budget Alert</h3>
            <form method="post" action="{% url 'projeng:send_budget_alert' project.pk %}">
                {% csrf_token %}
                <textarea name="message" 
                          rows="4" 
                          placeholder="Describe your budget concern (optional)..."
                          class="w-full border rounded p-2 mb-4"></textarea>
                <div class="flex gap-2">
                    <button type="submit" class="bg-yellow-500 text-white px-4 py-2 rounded">
                        Send Alert
                    </button>
                    <button type="button" 
                            onclick="hideBudgetAlertModal()"
                            class="bg-gray-300 text-gray-700 px-4 py-2 rounded">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

#### B. **Head Engineer Dashboard - Forward to Finance Button**
**File**: `templates/monitoring/project_detail.html` (or similar)

Add button in notifications/budget section:
```html
<!-- Forward to Finance Button (for Head Engineers) -->
{% if user|is_head_engineer %}
<div class="mt-4">
    <button type="button" 
            onclick="showForwardToFinanceModal()"
            class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg">
        💰 Forward Budget Alert to Finance
    </button>
</div>

<!-- Forward to Finance Modal -->
<div id="forwardToFinanceModal" class="hidden fixed inset-0 bg-black bg-opacity-50 z-50">
    <div class="flex items-center justify-center min-h-screen">
        <div class="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 class="text-xl font-semibold mb-4">Forward to Finance</h3>
            <form method="post" action="{% url 'monitoring:forward_budget_alert' project.pk %}">
                {% csrf_token %}
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-2">Your Assessment:</label>
                    <textarea name="assessment_message" 
                              rows="4" 
                              placeholder="Provide your assessment and recommendation..."
                              class="w-full border rounded p-2"></textarea>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-2">Requested Budget Increase (optional):</label>
                    <input type="number" 
                           name="requested_budget_increase" 
                           step="0.01" 
                           min="0"
                           placeholder="0.00"
                           class="w-full border rounded p-2">
                </div>
                <div class="flex gap-2">
                    <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded">
                        Forward to Finance
                    </button>
                    <button type="button" 
                            onclick="hideForwardToFinanceModal()"
                            class="bg-gray-300 text-gray-700 px-4 py-2 rounded">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

#### C. **Budget Status Indicators**
Add visual indicators showing budget utilization:
```html
<!-- Budget Status Bar -->
<div class="mb-4">
    <div class="flex justify-between text-sm mb-1">
        <span>Budget Utilization</span>
        <span>{{ utilization_percentage|floatformat:1 }}%</span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-4">
        <div class="h-4 rounded-full {% if utilization_percentage >= 100 %}bg-red-500{% elif utilization_percentage >= 95 %}bg-orange-500{% elif utilization_percentage >= 80 %}bg-yellow-500{% else %}bg-green-500{% endif %}" 
             style="width: {{ utilization_percentage|clamp:0:100 }}%">
        </div>
    </div>
    <div class="flex justify-between text-xs text-gray-600 mt-1">
        <span>Spent: ₱{{ total_spent|floatformat:2 }}</span>
        <span>Budget: ₱{{ project.project_cost|floatformat:2 }}</span>
    </div>
</div>
```

---

### 6. **URL Routing**

**File**: `projeng/urls.py`

Add new routes:
```python
urlpatterns = [
    # ... existing patterns ...
    path('project/<int:project_id>/send-budget-alert/', views.send_budget_alert, name='send_budget_alert'),
]
```

**File**: `monitoring/urls.py` (or wherever Head Engineer routes are)

Add route:
```python
urlpatterns = [
    # ... existing patterns ...
    path('project/<int:project_id>/forward-budget-alert/', views.forward_budget_alert_to_finance_view, name='forward_budget_alert'),
]
```

---

## 📊 Notification Flow Diagram

```
Cost Entry Added
    ↓
Check Budget Thresholds
    ↓
    ├─ 80% → Notify Head Engineers (Warning)
    ├─ 95% → Notify Head Engineers (Critical)
    └─ 100%+ → Notify Head Engineers (Over Budget)
    
Project Engineer Manual Alert
    ↓
Notify Head Engineers
    
Head Engineer Reviews
    ↓
    ├─ Can Update Budget (if authorized)
    └─ Forward to Finance (with assessment)
        ↓
        Notify Finance Managers
```

---

## ✅ Testing Checklist

### Automatic Notifications
- [ ] Cost entry pushes project to 80% → Head Engineers notified
- [ ] Cost entry pushes project to 95% → Head Engineers notified
- [ ] Cost entry pushes project over 100% → Head Engineers notified
- [ ] Duplicate notifications prevented (same threshold, same project)

### Manual Notifications
- [ ] Project Engineer can send manual budget alert
- [ ] Head Engineer receives manual alert
- [ ] Head Engineer can forward alert to Finance
- [ ] Finance Manager receives forwarded alert

### Permissions
- [ ] Project Engineer cannot update budget
- [ ] Head Engineer can update budget
- [ ] Finance Manager can update budget
- [ ] Budget update notifications sent appropriately

### UI/UX
- [ ] Budget status indicators display correctly
- [ ] Alert buttons visible to appropriate users
- [ ] Modals work correctly
- [ ] Notifications appear in notification center

---

## 🚀 Implementation Order

1. **Phase 1: Core Functionality**
   - Enhance `check_budget_thresholds()` function
   - Update `notify_cost_updates()` signal
   - Test automatic notifications

2. **Phase 2: Manual Notifications**
   - Add utility functions for manual alerts
   - Create views for sending/forwarding alerts
   - Add URL routes

3. **Phase 3: UI Components**
   - Add budget alert buttons
   - Add modals for manual alerts
   - Add budget status indicators

4. **Phase 4: Permissions & Polish**
   - Add budget update permission checks
   - Test all workflows
   - Add error handling and edge cases

---

## 📝 Notes

- **Duplicate Prevention**: Use `check_duplicates=True` in notification functions to prevent spam
- **Threshold Tracking**: Consider adding a model field to track which thresholds have been notified (optional)
- **Notification History**: All notifications are stored in `Notification` model for audit trail
- **Real-time Updates**: Existing WebSocket/SSE infrastructure will broadcast notifications automatically

---

## 🔄 Future Enhancements (Optional)

1. **Budget Adjustment Request Workflow**
   - Formal approval process for budget increases
   - Approval/rejection tracking

2. **Budget Forecasting**
   - Predict when project will exceed budget based on spending rate
   - Early warning before thresholds are hit

3. **Budget Categories**
   - Track budget by cost type (material, labor, etc.)
   - Set thresholds per category

4. **Email Notifications**
   - Send email alerts in addition to in-app notifications
   - Configurable email preferences

---

**Ready for Implementation!** 🎉

