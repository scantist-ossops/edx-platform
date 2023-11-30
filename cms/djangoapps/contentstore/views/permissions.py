from bridgekeeper import permissions

from common.djangoapps.student.roles import CourseInstructorRole
from openedx.core.djangoapps.user_authn.utils import has_role


class StudioAccessPermission(permissions.BasePermission):
    """
    Custom permission to determine Studio access.
    """
    def has_permission(self, user):
        """
        Check if the user has the required role for Studio access.
        """
        # Check if the user is an instructor for any course
        if has_role(user, CourseInstructorRole):
            return True
        else:
            return False
