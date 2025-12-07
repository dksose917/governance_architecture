"""Layer 3: Role-Based Access Control (RBAC) for the governance framework."""

import logging
from typing import Optional
from collections import defaultdict

from app.models.base import AgentType, UserRole
from app.models.governance import RBACPermission, User

logger = logging.getLogger(__name__)


class RBACManager:
    """Manages Role-Based Access Control for the healthcare agent system.
    
    Permission Matrix:
    - System Admin: Full access to all agents and functions
    - Clinical Director: Full clinical access + overrides
    - Nurse Manager: Patient care data access
    - Care Coordinator: Scheduling + communication access
    - Billing Staff: Billing data only
    - Family Portal: Limited patient view
    """
    
    def __init__(self):
        self.users: dict[str, User] = {}
        self.permissions: dict[str, RBACPermission] = {}
        self._permission_cache: dict[tuple[UserRole, AgentType], RBACPermission] = {}
        self._initialize_default_permissions()
    
    def _initialize_default_permissions(self):
        """Initialize default RBAC permissions for all roles."""
        permission_matrix = {
            UserRole.SYSTEM_ADMIN: {
                "agents": list(AgentType),
                "read": True, "write": True, "approve": True, "admin": True,
                "actions": ["*"]
            },
            UserRole.CLINICAL_DIRECTOR: {
                "agents": [
                    AgentType.ORCHESTRATOR, AgentType.INTAKE, AgentType.CARE_PLANNING,
                    AgentType.MEDICATION, AgentType.DOCUMENTATION, AgentType.COMPLIANCE,
                    AgentType.FAMILY_COMMUNICATION, AgentType.SCHEDULING
                ],
                "read": True, "write": True, "approve": True, "admin": False,
                "actions": ["*"]
            },
            UserRole.NURSE_MANAGER: {
                "agents": [
                    AgentType.INTAKE, AgentType.CARE_PLANNING, AgentType.DOCUMENTATION,
                    AgentType.FAMILY_COMMUNICATION, AgentType.SCHEDULING
                ],
                "read": True, "write": True, "approve": False, "admin": False,
                "actions": [
                    "view_patient", "update_care_plan", "create_documentation",
                    "send_communication", "schedule_appointment"
                ]
            },
            UserRole.CARE_COORDINATOR: {
                "agents": [
                    AgentType.FAMILY_COMMUNICATION, AgentType.SCHEDULING
                ],
                "read": True, "write": True, "approve": False, "admin": False,
                "actions": [
                    "view_schedule", "create_appointment", "send_reminder",
                    "contact_family", "update_contact_info"
                ]
            },
            UserRole.BILLING_STAFF: {
                "agents": [AgentType.BILLING],
                "read": True, "write": True, "approve": False, "admin": False,
                "actions": [
                    "view_claims", "submit_claim", "process_payment",
                    "generate_invoice", "view_documentation"
                ]
            },
            UserRole.FAMILY_PORTAL: {
                "agents": [AgentType.FAMILY_COMMUNICATION, AgentType.SCHEDULING],
                "read": True, "write": False, "approve": False, "admin": False,
                "actions": [
                    "view_appointments", "view_care_updates", "send_message"
                ]
            }
        }
        
        for role, config in permission_matrix.items():
            for agent_type in config["agents"]:
                perm = RBACPermission(
                    role=role,
                    agent_type=agent_type,
                    allowed_actions=config["actions"],
                    read_access=config["read"],
                    write_access=config["write"],
                    approve_access=config["approve"],
                    admin_access=config["admin"]
                )
                self.permissions[perm.permission_id] = perm
                self._permission_cache[(role, agent_type)] = perm
    
    def register_user(self, user: User) -> str:
        """Register a new user in the system."""
        self.users[user.user_id] = user
        logger.info(f"User registered: {user.username} with role {user.role.value}")
        return user.user_id
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def check_permission(
        self,
        user_id: str,
        agent_type: AgentType,
        action: str,
        require_write: bool = False,
        require_approve: bool = False
    ) -> tuple[bool, str]:
        """Check if a user has permission to perform an action.
        
        Returns:
            tuple: (has_permission, reason)
        """
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        if not user.is_active:
            return False, "User account is inactive"
        
        if action in user.permissions_override:
            return True, "Permission granted via override"
        
        permission = self._permission_cache.get((user.role, agent_type))
        if not permission:
            return False, f"No permission defined for {user.role.value} on {agent_type.value}"
        
        if not permission.read_access:
            return False, "No read access to this agent"
        
        if require_write and not permission.write_access:
            return False, "Write access required but not granted"
        
        if require_approve and not permission.approve_access:
            return False, "Approval access required but not granted"
        
        if "*" not in permission.allowed_actions and action not in permission.allowed_actions:
            return False, f"Action '{action}' not in allowed actions"
        
        return True, "Permission granted"
    
    def check_patient_access(
        self,
        user_id: str,
        patient_id: str,
        access_type: str = "VIEW"
    ) -> tuple[bool, str]:
        """Check if a user can access a specific patient's data.
        
        This is a simplified implementation. In production, this would
        check care team assignments, department restrictions, etc.
        """
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        if not user.is_active:
            return False, "User account is inactive"
        
        if user.role == UserRole.SYSTEM_ADMIN:
            return True, "Admin access"
        
        if user.role == UserRole.CLINICAL_DIRECTOR:
            return True, "Clinical director access"
        
        if user.role in [UserRole.NURSE_MANAGER, UserRole.CARE_COORDINATOR]:
            return True, "Care team access"
        
        if user.role == UserRole.BILLING_STAFF:
            if access_type in ["VIEW", "BILLING"]:
                return True, "Billing access for claims processing"
            return False, "Billing staff limited to billing-related access"
        
        if user.role == UserRole.FAMILY_PORTAL:
            return True, "Family portal access (limited view)"
        
        return False, "Access denied"
    
    def get_user_permissions(self, user_id: str) -> dict:
        """Get all permissions for a user."""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}
        
        permissions = {}
        for agent_type in AgentType:
            perm = self._permission_cache.get((user.role, agent_type))
            if perm:
                permissions[agent_type.value] = {
                    "read": perm.read_access,
                    "write": perm.write_access,
                    "approve": perm.approve_access,
                    "admin": perm.admin_access,
                    "allowed_actions": perm.allowed_actions
                }
        
        return {
            "user_id": user_id,
            "username": user.username,
            "role": user.role.value,
            "permissions": permissions,
            "overrides": user.permissions_override
        }
    
    def grant_permission_override(
        self,
        user_id: str,
        action: str,
        granted_by: str
    ) -> bool:
        """Grant a specific permission override to a user."""
        user = self.users.get(user_id)
        granter = self.users.get(granted_by)
        
        if not user or not granter:
            return False
        
        if granter.role not in [UserRole.SYSTEM_ADMIN, UserRole.CLINICAL_DIRECTOR]:
            logger.warning(f"User {granted_by} not authorized to grant overrides")
            return False
        
        if action not in user.permissions_override:
            user.permissions_override.append(action)
            logger.info(f"Permission override '{action}' granted to {user.username} by {granter.username}")
        
        return True
    
    def revoke_permission_override(self, user_id: str, action: str) -> bool:
        """Revoke a permission override from a user."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        if action in user.permissions_override:
            user.permissions_override.remove(action)
            logger.info(f"Permission override '{action}' revoked from {user.username}")
            return True
        
        return False
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.is_active = False
        logger.info(f"User {user.username} deactivated")
        return True
    
    def activate_user(self, user_id: str) -> bool:
        """Activate a user account."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.is_active = True
        logger.info(f"User {user.username} activated")
        return True
    
    def get_users_by_role(self, role: UserRole) -> list[User]:
        """Get all users with a specific role."""
        return [u for u in self.users.values() if u.role == role]
    
    def get_approvers_for_agent(self, agent_type: AgentType) -> list[User]:
        """Get all users who can approve actions for a specific agent."""
        approvers = []
        for user in self.users.values():
            if not user.is_active:
                continue
            perm = self._permission_cache.get((user.role, agent_type))
            if perm and perm.approve_access:
                approvers.append(user)
        return approvers
