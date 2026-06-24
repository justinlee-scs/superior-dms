export const PERMISSION_LABELS: Record<string, string> = {
  "document.read": "View Documents",
  "document.upload": "Create Documents",
  "document.update": "Edit Documents",
  "document.delete": "Delete Documents",
  "document.download": "Download Documents",
  "document.preview": "Preview Documents",
  "document.move": "Move Documents",
  "document.project_move": "Move Projects",
  "document.due_payments": "View Upcoming Payments",
  "document_version.read": "View Versions",
  "document_version.create": "Create Versions",
  "document_version.preview": "Preview Versions",
  "document_version.download": "Download Versions",
  "document_version.set_current": "Set Current Version",
  "document_version.delete": "Delete Versions",
  "document_version.stamp_access": "Use PDF Stamps",
  "document_version.stamp_label_create": "Create Stamp Labels",
  "document_version.text_box_access": "Use PDF Text Boxes",
  "workflow.advance": "View Workflows",
  "workflow.assign": "Edit Workflows",
  "admin.users": "Manage Users",
  "admin.roles": "Manage Roles",
  "admin.training": "Manage Training",
  "tags.read": "View Tags",
  "tags.edit": "Edit Tags",
  "tags.delete": "Delete Tag Pool Tags",
};

export const PERMISSION_DESCRIPTIONS: Record<string, string> = {
  "document.read": "Can open the document list and view document details.",
  "document.upload": "Can upload new documents into the system.",
  "document.update": "Can change document metadata such as title or type.",
  "document.delete": "Can permanently delete documents.",
  "document.download": "Can download document files.",
  "document.preview": "Can preview documents in the browser.",
  "document.move": "Can move documents between locations or workflows.",
  "document.project_move": "Can move documents into another project bucket.",
  "document.due_payments": "Can view the due payment queue and related invoices.",
  "document_version.read": "Can view a document's version history.",
  "document_version.create": "Can upload a new version of a document.",
  "document_version.preview": "Can preview saved document versions.",
  "document_version.download": "Can download saved document versions.",
  "document_version.set_current": "Can switch which version is the current active version.",
  "document_version.delete": "Can delete individual document versions.",
  "document_version.stamp_access": "Can place stamps on PDF annotations.",
  "document_version.stamp_label_create": "Can create, rename, and remove custom stamp labels for all users.",
  "document_version.text_box_access": "Can add comment text boxes to PDF annotations.",
  "workflow.advance": "Can view workflow progress and advance items through stages.",
  "workflow.assign": "Can assign or update workflow state and ownership.",
  "admin.users": "Can create, edit, activate, and deactivate users.",
  "admin.roles": "Can create and edit roles, including their permissions.",
  "admin.training": "Can manage the retraining schedule and training controls.",
  "tags.read": "Can view the tag pool and existing document tags.",
  "tags.edit": "Can add, update, or replace document tags.",
  "tags.delete": "Can delete tags from the global tag pool.",
};

export function permissionGroup(permissionKey: string): string {
  if (permissionKey.startsWith("document_version.")) return "Versioning";
  if (permissionKey.startsWith("document.")) return "Documents";
  if (permissionKey.startsWith("tags.")) return "Tags";
  if (permissionKey.startsWith("workflow.")) return "Workflows";
  if (permissionKey.startsWith("admin.")) return "Administration";
  return "Other";
}

export function titleCaseFromKey(permissionKey: string): string {
  const base = permissionKey.split(".").pop() ?? permissionKey;
  return base.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
