# 👷 Engineer Account Management - Implementation Plan

## 📋 Overview

This document outlines the plan for implementing Engineer Account Management functionality in the Head Engineer module. The Head Engineer should be able to create, view, edit, and manage Project Engineer accounts within the system.

---

## 🔍 Current State Analysis

### What Exists:
1. ✅ **Engineers Dropdown** - Sidebar dropdown showing existing engineers (Head Engineer only)
2. ✅ **API Endpoint** - `/projeng/api/engineers/` returns list of Project Engineers
3. ✅ **Project Assignment** - Engineers can be assigned to projects via ManyToMany relationship
4. ✅ **Role-Based Access** - Django Groups system (`Project Engineer`, `Head Engineer`)
5. ✅ **User Model** - Django's built-in User model with groups

### What's Missing:
1. ❌ **Engineer Management Page** - No dedicated page for managing engineers
2. ❌ **Create Engineer Account** - No UI/form to create new engineer accounts
3. ❌ **View Engineer Details** - No detailed view of engineer information
4. ❌ **Edit Engineer Account** - No ability to update engineer details
5. ❌ **Deactivate/Activate Engineers** - No ability to manage engineer account status
6. ❌ **Engineer Statistics** - No dashboard showing engineer performance/projects

---

## 🎯 Requirements

### Functional Requirements:

1. **Create New Engineer Account**
   - Head Engineer can create new Project Engineer accounts
   - Required fields: Username, Email, First Name, Last Name, Password
   - Optional fields: Phone, Department, Employee ID
   - Automatically assign to "Project Engineer" group
   - Send welcome email with login credentials (optional)

2. **View All Engineers**
   - List all Project Engineers in a table/grid
   - Show: Name, Username, Email, Status (Active/Inactive), Projects Count, Last Login
   - Search/filter functionality
   - Pagination for large lists

3. **View Engineer Details**
   - Individual engineer profile page
   - Show: Personal info, assigned projects, project statistics, activity log
   - Quick actions: Edit, Deactivate, View Projects

4. **Edit Engineer Account**
   - Update engineer information (name, email, etc.)
   - Change password (optional, can be separate action)
   - Update assigned projects (already exists in project management)

5. **Deactivate/Activate Engineers**
   - Soft delete - set `is_active = False`
   - Prevent login but keep data intact
   - Option to reactivate later

6. **Engineer Statistics Dashboard**
   - Total projects assigned
   - Active projects count
   - Completed projects count
   - Overall progress/performance metrics

### Non-Functional Requirements:

1. **Security**
   - Only Head Engineers can manage engineer accounts
   - Password validation (min length, complexity)
   - CSRF protection on all forms
   - Input validation and sanitization

2. **Performance**
   - Efficient queries (use select_related, prefetch_related)
   - Pagination for large datasets
   - Caching for frequently accessed data

3. **User Experience**
   - Intuitive UI matching existing design system
   - Responsive design (mobile-friendly)
   - Clear error messages
   - Success notifications
   - Confirmation dialogs for destructive actions

---

## 🏗️ Architecture & Design

### URL Structure:
```
/dashboard/engineers/                          # List all engineers
/dashboard/engineers/create/                   # Create new engineer
/dashboard/engineers/<id>/                     # View engineer details
/dashboard/engineers/<id>/edit/                # Edit engineer
/dashboard/engineers/<id>/deactivate/          # Deactivate engineer
/dashboard/engineers/<id>/activate/            # Activate engineer
/dashboard/engineers/<id>/projects/            # View engineer's projects
/api/engineers/                                # API endpoint (existing)
/api/engineers/create/                         # API endpoint for creation
/api/engineers/<id>/update/                    # API endpoint for updates
```

### Database Schema:
**No new models needed** - Use existing Django User model:
- `username` - Unique identifier
- `email` - Email address
- `first_name` - First name
- `last_name` - Last name
- `password` - Hashed password
- `is_active` - Account status
- `date_joined` - Account creation date
- `last_login` - Last login timestamp
- `groups` - ManyToMany to Group (Project Engineer)

**Optional Enhancement:**
Consider creating an `EngineerProfile` model for additional fields:
```python
class EngineerProfile(models.Model):
    user = OneToOneField(User, on_delete=models.CASCADE)
    phone = CharField(max_length=20, blank=True)
    department = CharField(max_length=100, blank=True)
    employee_id = CharField(max_length=50, blank=True)
    bio = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Views Structure:
```python
# monitoring/views/engineer_management.py
- engineer_list_view()          # List all engineers
- engineer_create_view()        # Create new engineer
- engineer_detail_view()        # View engineer details
- engineer_edit_view()          # Edit engineer
- engineer_deactivate_view()    # Deactivate engineer
- engineer_activate_view()      # Activate engineer
- engineer_projects_view()      # View engineer's projects
```

### Forms:
```python
# monitoring/forms.py (add)
- EngineerCreateForm           # Create new engineer
- EngineerEditForm             # Edit engineer
- EngineerPasswordChangeForm   # Change password (optional)
```

---

## 📱 UI/UX Design

### 1. Engineers Management Page (`/dashboard/engineers/`)

**Layout:**
- Header: "Engineer Management" with "Add New Engineer" button
- Search bar: Filter by name, username, email
- Table/Grid showing engineers:
  - Avatar/Initials
  - Full Name
  - Username
  - Email
  - Status (Active/Inactive badge)
  - Projects Count
  - Last Login
  - Actions (View, Edit, Deactivate/Activate)

**Design Elements:**
- Match existing dashboard design (blue sidebar, white content area)
- Use Tailwind CSS classes consistent with project
- Responsive table (scrollable on mobile)
- Status badges (green for active, gray for inactive)

### 2. Create Engineer Form (`/dashboard/engineers/create/`)

**Form Fields:**
- Username (required, unique)
- Email (required, unique, validated)
- First Name (required)
- Last Name (required)
- Password (required, with strength indicator)
- Confirm Password (required)
- Phone (optional)
- Department (optional)
- Employee ID (optional)

**Design:**
- Modal or dedicated page
- Clear field labels
- Validation messages
- Submit and Cancel buttons

### 3. Engineer Detail Page (`/dashboard/engineers/<id>/`)

**Sections:**
1. **Profile Information**
   - Avatar/Initials
   - Name, Username, Email
   - Status, Date Joined, Last Login
   - Quick Actions (Edit, Deactivate/Activate)

2. **Project Statistics**
   - Total Projects
   - Active Projects
   - Completed Projects
   - In Progress Projects
   - Overall Progress (chart/graph)

3. **Assigned Projects Table**
   - Project Name
   - Status
   - Progress
   - Start Date
   - End Date
   - Actions (View Project)

### 4. Edit Engineer Form (`/dashboard/engineers/<id>/edit/`)

**Similar to Create Form but:**
- Pre-filled with existing data
- Password field optional (separate change password option)
- Cannot change username (or with warning)

---

## 🔒 Security Considerations

1. **Access Control**
   - All views protected with `@head_engineer_required` decorator
   - API endpoints check Head Engineer permission
   - Prevent Head Engineers from deactivating themselves

2. **Password Security**
   - Enforce password complexity (min 8 characters, mix of letters/numbers)
   - Hash passwords using Django's password hashers
   - Never display passwords in UI
   - Option to generate random passwords

3. **Input Validation**
   - Validate email format
   - Check username uniqueness
   - Sanitize all user inputs
   - Prevent SQL injection (Django ORM handles this)

4. **CSRF Protection**
   - All forms include CSRF tokens
   - API endpoints use CSRF exemption only when necessary

5. **Audit Logging**
   - Log all engineer account changes (create, edit, deactivate)
   - Track who made the change and when
   - Consider adding to notification system

---

## 📝 Implementation Steps

### Phase 1: Core Functionality (Priority 1)
1. ✅ Create URL patterns in `monitoring/urls.py`
2. ✅ Create views in `monitoring/views/engineer_management.py`
3. ✅ Create forms in `monitoring/forms.py`
4. ✅ Create templates for engineer management
5. ✅ Add "Engineers" link to sidebar (replace dropdown with direct link)
6. ✅ Test create, view, list functionality

### Phase 2: Enhanced Features (Priority 2)
1. ✅ Add edit functionality
2. ✅ Add deactivate/activate functionality
3. ✅ Add engineer detail page with statistics
4. ✅ Add search/filter functionality
5. ✅ Add pagination

### Phase 3: Polish & Optimization (Priority 3)
1. ✅ Add engineer statistics dashboard
2. ✅ Add activity logging
3. ✅ Add email notifications (optional)
4. ✅ Add bulk operations (optional)
5. ✅ Performance optimization

---

## 🧪 Testing Plan

### Unit Tests:
- Test engineer creation
- Test engineer editing
- Test engineer deactivation
- Test access control (only Head Engineers)
- Test form validation

### Integration Tests:
- Test engineer assignment to projects
- Test engineer statistics calculation
- Test search/filter functionality

### Manual Testing:
- Test UI responsiveness
- Test error handling
- Test user experience flow
- Test security (try accessing as Project Engineer)

---

## 📊 Success Criteria

1. ✅ Head Engineer can create new engineer accounts
2. ✅ Head Engineer can view all engineers in a list
3. ✅ Head Engineer can view engineer details
4. ✅ Head Engineer can edit engineer information
5. ✅ Head Engineer can deactivate/activate engineers
6. ✅ All actions are secure and properly authorized
7. ✅ UI is intuitive and matches existing design
8. ✅ System handles errors gracefully

---

## 🚀 Future Enhancements (Optional)

1. **Email Notifications**
   - Send welcome email when engineer account is created
   - Notify engineer when account is deactivated
   - Password reset emails

2. **Bulk Operations**
   - Bulk import engineers from CSV
   - Bulk activate/deactivate
   - Bulk assign to projects

3. **Advanced Statistics**
   - Engineer performance metrics
   - Project completion rates
   - Time tracking
   - Activity heatmaps

4. **Engineer Profile Extensions**
   - Profile pictures
   - Bio/Description
   - Skills/Specializations
   - Certification tracking

5. **Permission Granularity**
   - Custom permissions per engineer
   - Project-specific permissions
   - Feature access control

---

## 📅 Estimated Timeline

- **Phase 1 (Core)**: 2-3 days
- **Phase 2 (Enhanced)**: 1-2 days
- **Phase 3 (Polish)**: 1-2 days
- **Total**: 4-7 days

---

## 🎯 Next Steps

1. Review and approve this plan
2. Start with Phase 1 implementation
3. Create engineer management views
4. Create engineer management templates
5. Update sidebar navigation
6. Test functionality
7. Deploy to production

---

## 📝 Notes

- Consider adding engineer profile model if additional fields are needed
- Keep existing API endpoint `/projeng/api/engineers/` for backward compatibility
- Ensure mobile responsiveness for all new pages
- Follow existing code style and patterns
- Document any new functions/classes

