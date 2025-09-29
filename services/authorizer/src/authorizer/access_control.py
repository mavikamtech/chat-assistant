"""Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC) implementation."""

import logging
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass

from mavik_common.errors import (
    AuthorizationError,
    MNPIAccessDeniedError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions for RBAC."""
    
    # General permissions
    READ_DEALS = "read_deals"
    WRITE_DEALS = "write_deals"
    DELETE_DEALS = "delete_deals"
    
    # Analysis permissions
    RUN_ANALYSIS = "run_analysis"
    VIEW_ANALYSIS = "view_analysis"
    EXPORT_ANALYSIS = "export_analysis"
    
    # Document permissions
    UPLOAD_DOCUMENTS = "upload_documents"
    VIEW_DOCUMENTS = "view_documents"
    DELETE_DOCUMENTS = "delete_documents"
    
    # Report permissions
    GENERATE_REPORTS = "generate_reports"
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    
    # Administrative permissions
    MANAGE_USERS = "manage_users"
    VIEW_SYSTEM_LOGS = "view_system_logs"
    MANAGE_SYSTEM_CONFIG = "manage_system_config"
    
    # MNPI permissions
    ACCESS_MNPI_INTERNAL = "access_mnpi_internal"
    ACCESS_MNPI_CONFIDENTIAL = "access_mnpi_confidential"
    ACCESS_MNPI_RESTRICTED = "access_mnpi_restricted"
    MANAGE_MNPI_CLASSIFICATION = "manage_mnpi_classification"


class Role(str, Enum):
    """System roles with associated permissions."""
    
    VIEWER = "viewer"
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    PORTFOLIO_MANAGER = "portfolio_manager"
    COMPLIANCE_OFFICER = "compliance_officer"
    ADMIN = "admin"
    SYSTEM = "system"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_DEALS,
        Permission.VIEW_ANALYSIS,
        Permission.VIEW_DOCUMENTS,
        Permission.VIEW_REPORTS,
    },
    Role.ANALYST: {
        Permission.READ_DEALS,
        Permission.WRITE_DEALS,
        Permission.RUN_ANALYSIS,
        Permission.VIEW_ANALYSIS,
        Permission.EXPORT_ANALYSIS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_DOCUMENTS,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.ACCESS_MNPI_INTERNAL,
    },
    Role.SENIOR_ANALYST: {
        Permission.READ_DEALS,
        Permission.WRITE_DEALS,
        Permission.DELETE_DEALS,
        Permission.RUN_ANALYSIS,
        Permission.VIEW_ANALYSIS,
        Permission.EXPORT_ANALYSIS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.ACCESS_MNPI_INTERNAL,
        Permission.ACCESS_MNPI_CONFIDENTIAL,
    },
    Role.PORTFOLIO_MANAGER: {
        Permission.READ_DEALS,
        Permission.WRITE_DEALS,
        Permission.DELETE_DEALS,
        Permission.RUN_ANALYSIS,
        Permission.VIEW_ANALYSIS,
        Permission.EXPORT_ANALYSIS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.ACCESS_MNPI_INTERNAL,
        Permission.ACCESS_MNPI_CONFIDENTIAL,
        Permission.ACCESS_MNPI_RESTRICTED,
    },
    Role.COMPLIANCE_OFFICER: {
        Permission.READ_DEALS,
        Permission.VIEW_ANALYSIS,
        Permission.EXPORT_ANALYSIS,
        Permission.VIEW_DOCUMENTS,
        Permission.VIEW_REPORTS,
        Permission.EXPORT_REPORTS,
        Permission.VIEW_SYSTEM_LOGS,
        Permission.ACCESS_MNPI_INTERNAL,
        Permission.ACCESS_MNPI_CONFIDENTIAL,
        Permission.ACCESS_MNPI_RESTRICTED,
        Permission.MANAGE_MNPI_CLASSIFICATION,
    },
    Role.ADMIN: {
        # All permissions
        *Permission.__members__.values()
    },
    Role.SYSTEM: {
        # All permissions for system-to-system communication
        *Permission.__members__.values()
    },
}


@dataclass
class AccessContext:
    """Context information for access control decisions."""
    
    user_id: str
    email: str
    roles: List[str]
    departments: List[str] = None
    location: Optional[str] = None
    security_clearance: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_time: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.departments is None:
            self.departments = []


@dataclass
class ResourceContext:
    """Context information about the resource being accessed."""
    
    resource_type: str
    resource_id: Optional[str] = None
    mnpi_classification: Optional[str] = None
    owner_id: Optional[str] = None
    department: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = {}


class AccessControlManager:
    """Manages RBAC and ABAC access control decisions."""
    
    def __init__(
        self,
        mnpi_enforcement_enabled: bool = True,
        mnpi_admin_roles: Optional[List[str]] = None,
        default_mnpi_classification: str = "public",
    ):
        """Initialize access control manager.
        
        Args:
            mnpi_enforcement_enabled: Whether to enforce MNPI access controls
            mnpi_admin_roles: Roles with MNPI administrative access
            default_mnpi_classification: Default MNPI classification for resources
        """
        self.mnpi_enforcement_enabled = mnpi_enforcement_enabled
        self.mnpi_admin_roles = mnpi_admin_roles or ["admin", "compliance_officer"]
        self.default_mnpi_classification = default_mnpi_classification
    
    def check_permission(
        self,
        access_context: AccessContext,
        permission: Permission,
        resource_context: Optional[ResourceContext] = None,
    ) -> bool:
        """Check if user has permission for a specific action.
        
        Args:
            access_context: User and request context
            permission: Required permission
            resource_context: Optional resource context for ABAC
            
        Returns:
            True if access is granted
            
        Raises:
            AuthorizationError: If access is denied
            MNPIAccessDeniedError: If MNPI access is denied
        """
        try:
            # Check RBAC permissions
            user_permissions = self._get_user_permissions(access_context.roles)
            
            if permission not in user_permissions:
                logger.warning(
                    f"RBAC denied: User {access_context.user_id} lacks permission {permission}"
                )
                raise AuthorizationError(f"Insufficient permissions: {permission}")
            
            # Check ABAC rules if resource context is provided
            if resource_context:
                self._check_abac_rules(access_context, permission, resource_context)
            
            # Check MNPI access controls
            if self.mnpi_enforcement_enabled and resource_context:
                self._check_mnpi_access(access_context, resource_context)
            
            logger.info(
                f"Access granted: User {access_context.user_id} permission {permission}"
            )
            return True
            
        except (AuthorizationError, MNPIAccessDeniedError):
            raise
        except Exception as e:
            logger.error(f"Access control error: {e}")
            raise AuthorizationError(f"Access control check failed: {e}")
    
    def _get_user_permissions(self, roles: List[str]) -> Set[Permission]:
        """Get all permissions for user roles."""
        permissions = set()
        
        for role_str in roles:
            try:
                role = Role(role_str.lower())
                role_perms = ROLE_PERMISSIONS.get(role, set())
                permissions.update(role_perms)
                
                logger.debug(f"Role {role} grants {len(role_perms)} permissions")
                
            except ValueError:
                logger.warning(f"Unknown role: {role_str}")
                continue
        
        logger.debug(f"User has {len(permissions)} total permissions")
        return permissions
    
    def _check_abac_rules(
        self,
        access_context: AccessContext,
        permission: Permission,
        resource_context: ResourceContext,
    ) -> None:
        """Check attribute-based access control rules."""
        
        # Rule 1: Users can only access their own resources (unless admin)
        if (resource_context.owner_id and 
            resource_context.owner_id != access_context.user_id and
            not self._is_admin_user(access_context.roles)):
            
            # Exception: Senior roles can access department resources
            if not self._can_access_department_resource(access_context, resource_context):
                raise AuthorizationError("Cannot access resource owned by another user")
        
        # Rule 2: Department-based access controls
        if (resource_context.department and 
            resource_context.department not in access_context.departments and
            not self._is_admin_user(access_context.roles)):
            raise AuthorizationError(f"Cannot access {resource_context.department} department resource")
        
        # Rule 3: Location-based restrictions (if implemented)
        if hasattr(self, '_check_location_restrictions'):
            self._check_location_restrictions(access_context, resource_context)
        
        logger.debug("ABAC rules passed")
    
    def _check_mnpi_access(
        self,
        access_context: AccessContext,
        resource_context: ResourceContext,
    ) -> None:
        """Check MNPI (Material Non-Public Information) access controls."""
        
        mnpi_classification = (
            resource_context.mnpi_classification or 
            self.default_mnpi_classification
        )
        
        # Public information is always accessible
        if mnpi_classification == "public":
            return
        
        # Check if user has required MNPI permission
        required_permission = self._get_mnpi_permission(mnpi_classification)
        user_permissions = self._get_user_permissions(access_context.roles)
        
        if required_permission not in user_permissions:
            logger.warning(
                f"MNPI access denied: User {access_context.user_id} "
                f"cannot access {mnpi_classification} information"
            )
            raise MNPIAccessDeniedError(
                f"Insufficient MNPI clearance for {mnpi_classification} information"
            )
        
        # Additional MNPI audit logging
        logger.info(
            f"MNPI access granted: User {access_context.user_id} "
            f"accessed {mnpi_classification} resource {resource_context.resource_id}"
        )
    
    def _get_mnpi_permission(self, classification: str) -> Permission:
        """Get required permission for MNPI classification level."""
        mapping = {
            "internal": Permission.ACCESS_MNPI_INTERNAL,
            "confidential": Permission.ACCESS_MNPI_CONFIDENTIAL,
            "restricted": Permission.ACCESS_MNPI_RESTRICTED,
        }
        
        return mapping.get(classification.lower(), Permission.ACCESS_MNPI_INTERNAL)
    
    def _is_admin_user(self, roles: List[str]) -> bool:
        """Check if user has administrative privileges."""
        admin_roles = {Role.ADMIN.value, Role.SYSTEM.value}
        return any(role.lower() in admin_roles for role in roles)
    
    def _can_access_department_resource(
        self,
        access_context: AccessContext,
        resource_context: ResourceContext,
    ) -> bool:
        """Check if user can access department resource based on seniority."""
        
        # Senior roles can access department resources
        senior_roles = {
            Role.SENIOR_ANALYST.value,
            Role.PORTFOLIO_MANAGER.value,
            Role.COMPLIANCE_OFFICER.value,
        }
        
        has_senior_role = any(role.lower() in senior_roles for role in access_context.roles)
        same_department = resource_context.department in access_context.departments
        
        return has_senior_role and same_department
    
    def get_user_context_from_token(self, token_claims: Dict[str, Any]) -> AccessContext:
        """Extract access context from JWT token claims.
        
        Args:
            token_claims: Decoded JWT token claims
            
        Returns:
            Access context for the user
            
        Raises:
            AuthorizationError: If required claims are missing
        """
        try:
            user_id = token_claims.get("sub") or token_claims.get("oid")
            email = token_claims.get("email") or token_claims.get("preferred_username")
            
            if not user_id or not email:
                raise AuthorizationError("Token missing required user identification")
            
            # Extract roles from various claim locations
            roles = []
            
            # Check standard role claims
            if "roles" in token_claims:
                roles.extend(token_claims["roles"])
            
            # Check Azure AD app roles
            if "app_roles" in token_claims:
                roles.extend(token_claims["app_roles"])
            
            # Check groups (can be mapped to roles)
            if "groups" in token_claims:
                group_roles = self._map_groups_to_roles(token_claims["groups"])
                roles.extend(group_roles)
            
            # Default role if none specified
            if not roles:
                roles = [Role.VIEWER.value]
            
            # Extract additional context
            departments = token_claims.get("department", [])
            if isinstance(departments, str):
                departments = [departments]
            
            return AccessContext(
                user_id=user_id,
                email=email,
                roles=roles,
                departments=departments,
                location=token_claims.get("location"),
                security_clearance=token_claims.get("security_clearance"),
            )
            
        except Exception as e:
            logger.error(f"Error extracting user context: {e}")
            raise AuthorizationError(f"Invalid token claims: {e}")
    
    def _map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """Map Azure AD groups to application roles."""
        
        # Example group to role mapping
        group_mapping = {
            "mavik-analysts": Role.ANALYST.value,
            "mavik-senior-analysts": Role.SENIOR_ANALYST.value,
            "mavik-portfolio-managers": Role.PORTFOLIO_MANAGER.value,
            "mavik-compliance": Role.COMPLIANCE_OFFICER.value,
            "mavik-admins": Role.ADMIN.value,
        }
        
        mapped_roles = []
        for group in groups:
            if group in group_mapping:
                mapped_roles.append(group_mapping[group])
        
        return mapped_roles
    
    def create_policy_context(
        self,
        access_context: AccessContext,
        resource_context: Optional[ResourceContext] = None,
    ) -> Dict[str, Any]:
        """Create policy context for external policy engines.
        
        Args:
            access_context: User access context
            resource_context: Optional resource context
            
        Returns:
            Policy context dictionary
        """
        context = {
            "user": {
                "id": access_context.user_id,
                "email": access_context.email,
                "roles": access_context.roles,
                "departments": access_context.departments,
                "location": access_context.location,
                "security_clearance": access_context.security_clearance,
            },
            "request": {
                "ip_address": access_context.ip_address,
                "user_agent": access_context.user_agent,
                "timestamp": access_context.request_time,
            },
        }
        
        if resource_context:
            context["resource"] = {
                "type": resource_context.resource_type,
                "id": resource_context.resource_id,
                "mnpi_classification": resource_context.mnpi_classification,
                "owner_id": resource_context.owner_id,
                "department": resource_context.department,
                "tags": resource_context.tags,
            }
        
        return context