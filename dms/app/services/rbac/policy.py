class Permissions:
    """Define the permissions type.
    
    Parameters:
        DOCUMENT_READ: Parameter.
        DOCUMENT_DELETE: Parameter.
        DOCUMENT_UPLOAD: Parameter.
        DOCUMENT_DOWNLOAD: Parameter.
        DOCUMENT_PREVIEW: Parameter.
        DOCUMENT_MOVE: Parameter.
        DOCUMENT_UPDATE: Parameter.
        DOCUMENT_VERSION_READ: Parameter.
        DOCUMENT_VERSION_CREATE: Parameter.
        DOCUMENT_VERSION_PREVIEW: Parameter.
        DOCUMENT_VERSION_DOWNLOAD: Parameter.
        DOCUMENT_VERSION_SET_CURRENT: Parameter.
        DOCUMENT_TAG_READ: Parameter.
        DOCUMENT_TAG_EDIT: Parameter.
        WORKFLOW_ASSIGN: Parameter.
        WORKFLOW_ADVANCE: Parameter.
        ADMIN_USERS: Parameter.
        ADMIN_ROLES: Parameter.
    """
    DOCUMENT_READ = "document.read"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DOWNLOAD = "document.download"
    DOCUMENT_PREVIEW = "document.preview"
    DOCUMENT_MOVE = "document.move"
    DOCUMENT_UPDATE = "document.update"
    DOCUMENT_VERSION_READ = "document_version.read"
    DOCUMENT_VERSION_CREATE = "document_version.create"
    DOCUMENT_VERSION_PREVIEW = "document_version.preview"
    DOCUMENT_VERSION_DOWNLOAD = "document_version.download"
    DOCUMENT_VERSION_SET_CURRENT = "document_version.set_current"
    DOCUMENT_TAG_READ = "tags.read"
    DOCUMENT_TAG_EDIT = "tags.edit"

    WORKFLOW_ASSIGN = "workflow.assign"
    WORKFLOW_ADVANCE = "workflow.advance"

    ADMIN_USERS = "admin.users"
    ADMIN_ROLES = "admin.roles"
