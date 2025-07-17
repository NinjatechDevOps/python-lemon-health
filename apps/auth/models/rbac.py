from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

from apps.core.base import Base

# Many-to-many relationship between roles and permissions
role_permission = Table(
    'role_permission',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id')),
    Column('permission_id', Integer, ForeignKey('permission.id'))
)

# Many-to-many relationship between users and roles
user_role = Table(
    'user_role',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('role.id'))
)

class Permission(Base):
    """Permission model for RBAC"""
    __tablename__ = "permission"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    
    # Relationships - use string references to avoid circular imports
    roles = relationship("Role", secondary=role_permission, back_populates="permissions")

class Role(Base):
    """Role model for RBAC"""
    __tablename__ = "role"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    
    # Relationships - use string references to avoid circular imports
    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    users = relationship("apps.accounts.models.User", secondary=user_role, back_populates="roles")