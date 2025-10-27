from functools import wraps
from flask import session, redirect, url_for, request, abort, g
from models import Users, Organization
from database import db

def organization_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'org_id' not in session:
            return redirect(url_for('auth.login'))

        g.org_id = session.get('org_id')
        g.user_id = session.get('uid')

        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role')
            if user_role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_organization_context():
    org_id = session.get('org_id')
    if org_id:
        return Organization.query.get(org_id)
    return None


def filter_by_organization(query, model):
    org_id = session.get('org_id')
    if org_id and hasattr(model, 'OrgID'):
        return query.filter_by(OrgID=org_id)
    return query


# ==================== Organization Limits Check ====================
# NOTE: Subscription limits have been REMOVED
# This function now always returns True for unlimited access

def check_organization_limits(org_id, resource_type='users'):
    """
    Check if an organization can add more resources (users or projects).
    
    IMPORTANT CHANGE: This function has been modified to allow UNLIMITED access.
    Previous implementation checked MaxUsers and MaxProjects from the Organization model.
    Now it always returns (True, "OK") to remove all subscription-based restrictions.
    
    Args:
        org_id (int): Organization ID to check
        resource_type (str): Type of resource ('users' or 'projects')
        
    Returns:
        tuple: (success: bool, message: str)
            - (True, "OK") = unlimited access allowed
            - (False, message) = only if org not found
    """
    # Verify organization exists
    org = Organization.query.get(org_id)
    if not org:
        return False, "Organization not found"

    # Return unlimited access - no restrictions
    # Previously this function checked subscription limits
    return True, "OK"


class OrganizationContext:

    def __init__(self, org_id):
        self.org_id = org_id
        self.previous_org_id = None

    def __enter__(self):
        self.previous_org_id = session.get('org_id')
        session['org_id'] = self.org_id
        g.org_id = self.org_id
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_org_id:
            session['org_id'] = self.previous_org_id
            g.org_id = self.previous_org_id
        else:
            session.pop('org_id', None)
            g.org_id = None


def audit_log(action, resource_type, resource_id, details=None):
    from models import AuditLog
    from datetime import datetime

    log_entry = AuditLog(
        OrgID=session.get('org_id'),
        UserID=session.get('uid'),
        Action=action,
        ResourceType=resource_type,
        ResourceID=resource_id,
        Details=details,
        IPAddress=request.remote_addr,
        UserAgent=request.headers.get('User-Agent'),
        Timestamp=datetime.utcnow()
    )

    db.session.add(log_entry)
    db.session.commit()