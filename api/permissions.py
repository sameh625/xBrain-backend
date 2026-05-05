from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrReadOnly(BasePermission):
    """Read for anyone (subject to view-level auth); write only for the object's author."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author_id == request.user.id


class IsQuestionAuthor(BasePermission):
    """Only the question's author can call this action (e.g. resolve / unresolve)."""

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id
