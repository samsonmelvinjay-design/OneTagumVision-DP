"""
Context processors for global template context
"""
def login_success_modal(request):
    """
    Check and clear login success session flag
    Returns True if modal should be shown, then clears the flag
    """
    show_modal = request.session.get('show_login_success', False)
    if show_modal:
        # Clear the flag immediately so it only shows once
        del request.session['show_login_success']
        request.session.save()
    return {'show_login_success_modal': show_modal}

