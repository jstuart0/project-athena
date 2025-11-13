"""
Database models for Athena Admin Interface.

These models represent the database schema for configuration management,
audit logging, device tracking, and user management.
"""
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model for authentication and RBAC."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    authentik_id = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    role = Column(String(32), nullable=False, default='viewer')  # owner, operator, viewer, support
    active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    policies_created = relationship('Policy', foreign_keys='Policy.created_by_id', back_populates='creator')
    audit_logs = relationship('AuditLog', back_populates='user')

    __table_args__ = (
        Index('idx_users_role', 'role'),
        Index('idx_users_active', 'active'),
    )

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission based on their role."""
        permissions = {
            'owner': {'read', 'write', 'delete', 'manage_users', 'manage_secrets', 'view_audit'},
            'operator': {'read', 'write', 'view_audit'},
            'viewer': {'read'},
            'support': {'read', 'view_audit'},
        }
        return permission in permissions.get(self.role, set())


class Policy(Base):
    """
    Policy model for storing orchestrator/RAG configuration.

    Supports both orchestrator modes (fast/medium/custom) and RAG configurations.
    Each policy change creates a new version for rollback capability.
    """
    __tablename__ = 'policies'

    id = Column(Integer, primary_key=True)
    mode = Column(String(16), nullable=False)  # 'fast', 'medium', 'custom', 'rag'
    config = Column(JSONB, nullable=False)  # Full configuration as JSON
    version = Column(Integer, nullable=False, default=1)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    description = Column(Text)

    # Relationships
    creator = relationship('User', foreign_keys=[created_by_id], back_populates='policies_created')
    versions = relationship('PolicyVersion', back_populates='policy', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', back_populates='policy')

    __table_args__ = (
        Index('idx_policies_mode', 'mode'),
        Index('idx_policies_active', 'active'),
        Index('idx_policies_created_at', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary for API responses."""
        return {
            'id': self.id,
            'mode': self.mode,
            'config': self.config,
            'version': self.version,
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'active': self.active,
            'description': self.description,
        }


class PolicyVersion(Base):
    """Version history for policy changes to support rollback."""
    __tablename__ = 'policy_versions'

    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey('policies.id'), nullable=False)
    version = Column(Integer, nullable=False)
    config = Column(JSONB, nullable=False)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    change_description = Column(Text)

    # Relationships
    policy = relationship('Policy', back_populates='versions')
    creator = relationship('User', foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint('policy_id', 'version', name='uq_policy_version'),
        Index('idx_policy_versions_policy_id', 'policy_id'),
        Index('idx_policy_versions_created_at', 'created_at'),
    )


class Secret(Base):
    """
    Secret model for encrypted API keys and credentials.

    Stores encrypted secrets for services like OpenAI, weather APIs, etc.
    Uses application-level encryption before storage.
    """
    __tablename__ = 'secrets'

    id = Column(Integer, primary_key=True)
    service_name = Column(String(255), nullable=False, unique=True, index=True)
    encrypted_value = Column(Text, nullable=False)  # Application-encrypted
    description = Column(Text)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_rotated = Column(DateTime(timezone=True))

    # Relationships
    creator = relationship('User', foreign_keys=[created_by_id])
    audit_logs = relationship('AuditLog', back_populates='secret')

    __table_args__ = (
        Index('idx_secrets_service_name', 'service_name'),
        Index('idx_secrets_last_rotated', 'last_rotated'),
    )


class Device(Base):
    """
    Device model for tracking voice devices and services.

    Tracks Wyoming devices, jetson units, and other hardware in the system.
    """
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True)
    device_type = Column(String(32), nullable=False)  # 'wyoming', 'jetson', 'service'
    name = Column(String(255), nullable=False, unique=True, index=True)
    hostname = Column(String(255))
    ip_address = Column(String(45))  # IPv6-compatible
    port = Column(Integer)
    zone = Column(String(255))  # Physical location (e.g., 'office', 'kitchen')
    status = Column(String(32), default='unknown')  # 'online', 'offline', 'degraded', 'unknown'
    last_seen = Column(DateTime(timezone=True))
    config = Column(JSONB)  # Device-specific configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    audit_logs = relationship('AuditLog', back_populates='device')

    __table_args__ = (
        Index('idx_devices_type', 'device_type'),
        Index('idx_devices_status', 'status'),
        Index('idx_devices_zone', 'zone'),
        Index('idx_devices_last_seen', 'last_seen'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary for API responses."""
        return {
            'id': self.id,
            'device_type': self.device_type,
            'name': self.name,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'port': self.port,
            'zone': self.zone,
            'status': self.status,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'config': self.config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(Base):
    """
    Audit log for all configuration changes and sensitive operations.

    Provides tamper-evident logging using HMAC signatures.
    Immutable records for compliance and security.
    """
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(64), nullable=False)  # 'create', 'update', 'delete', 'view', etc.
    resource_type = Column(String(64), nullable=False)  # 'policy', 'secret', 'device', etc.
    resource_id = Column(Integer)  # ID of the affected resource
    old_value = Column(JSONB)  # Previous state (for updates/deletes)
    new_value = Column(JSONB)  # New state (for creates/updates)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text)
    signature = Column(String(128))  # HMAC signature for tamper detection

    # Foreign key relationships (optional, for easier queries)
    policy_id = Column(Integer, ForeignKey('policies.id'))
    secret_id = Column(Integer, ForeignKey('secrets.id'))
    device_id = Column(Integer, ForeignKey('devices.id'))

    # Relationships
    user = relationship('User', back_populates='audit_logs')
    policy = relationship('Policy', back_populates='audit_logs')
    secret = relationship('Secret', back_populates='audit_logs')
    device = relationship('Device', back_populates='audit_logs')

    __table_args__ = (
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_resource_type', 'resource_type'),
        Index('idx_audit_logs_resource_composite', 'resource_type', 'resource_id'),
    )

    def compute_signature(self, secret_key: str) -> str:
        """
        Compute HMAC signature for tamper detection.

        Args:
            secret_key: Secret key for HMAC computation

        Returns:
            Hex-encoded HMAC signature
        """
        message = f"{self.id}:{self.timestamp}:{self.user_id}:{self.action}:{self.resource_type}:{self.resource_id}"
        return hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, secret_key: str) -> bool:
        """
        Verify HMAC signature to detect tampering.

        Args:
            secret_key: Secret key for HMAC computation

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.signature:
            return False
        expected_signature = self.compute_signature(secret_key)
        return hmac.compare_digest(self.signature, expected_signature)

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary for API responses."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user': self.user.username if self.user else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'ip_address': self.ip_address,
            'success': self.success,
            'error_message': self.error_message,
        }


class ServerConfig(Base):
    """
    Server configuration model for tracking compute nodes.

    Tracks Mac Studio, Mac mini, Home Assistant, and other servers in the system.
    """
    __tablename__ = 'server_configs'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    hostname = Column(String(128))
    ip_address = Column(String(15), nullable=False)
    role = Column(String(32))  # "compute", "storage", "integration", "orchestration"
    status = Column(String(16), default='unknown')  # online, offline, degraded, unknown
    config = Column(JSONB)  # Flexible JSON config (ssh_user, docker_enabled, etc.)
    last_checked = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    services = relationship('ServiceRegistry', back_populates='server', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_server_configs_name', 'name'),
        Index('idx_server_configs_status', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert server config to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'role': self.role,
            'status': self.status,
            'config': self.config,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceRegistry(Base):
    """
    Service registry for tracking all services across servers.

    Links services to their host servers and tracks health status.
    """
    __tablename__ = 'service_registry'

    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('server_configs.id'), nullable=False)
    service_name = Column(String(64), nullable=False)
    port = Column(Integer, nullable=False)
    health_endpoint = Column(String(256))  # "/health", "/api/health", etc.
    protocol = Column(String(8), default='http')  # http, https, tcp
    status = Column(String(16), default='unknown')
    last_response_time = Column(Integer)  # milliseconds
    last_checked = Column(DateTime(timezone=True))

    # Relationships
    server = relationship('ServerConfig', back_populates='services')
    rag_connectors = relationship('RAGConnector', back_populates='service')

    __table_args__ = (
        UniqueConstraint('server_id', 'service_name', 'port', name='uq_service_registry'),
        Index('idx_service_registry_server_id', 'server_id'),
        Index('idx_service_registry_status', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert service registry entry to dictionary for API responses."""
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_name': self.server.name if self.server else None,
            'ip_address': self.server.ip_address if self.server else None,
            'service_name': self.service_name,
            'port': self.port,
            'health_endpoint': self.health_endpoint,
            'protocol': self.protocol,
            'status': self.status,
            'last_response_time': self.last_response_time,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
        }


class RAGConnector(Base):
    """
    RAG connector configuration for external data sources.

    Manages configuration for weather, airports, sports, and custom RAG connectors.
    """
    __tablename__ = 'rag_connectors'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    connector_type = Column(String(32), nullable=False)  # "external_api", "vector_db", "cache", "custom"
    service_id = Column(Integer, ForeignKey('service_registry.id'))
    enabled = Column(Boolean, default=True)
    config = Column(JSONB)  # Connector-specific config (API endpoints, parameters, etc.)
    cache_config = Column(JSONB)  # Cache settings (TTL, size limits, eviction policy)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    service = relationship('ServiceRegistry', back_populates='rag_connectors')
    creator = relationship('User')
    stats = relationship('RAGStats', back_populates='connector', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_rag_connectors_name', 'name'),
        Index('idx_rag_connectors_enabled', 'enabled'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert RAG connector to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'connector_type': self.connector_type,
            'service_id': self.service_id,
            'service_name': self.service.service_name if self.service else None,
            'enabled': self.enabled,
            'config': self.config,
            'cache_config': self.cache_config,
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class RAGStats(Base):
    """
    Statistics tracking for RAG connectors.

    Records usage metrics, cache performance, and errors for monitoring.
    """
    __tablename__ = 'rag_stats'

    id = Column(Integer, primary_key=True)
    connector_id = Column(Integer, ForeignKey('rag_connectors.id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    requests_count = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    avg_response_time = Column(Integer)  # milliseconds
    error_count = Column(Integer, default=0)

    # Relationships
    connector = relationship('RAGConnector', back_populates='stats')

    __table_args__ = (
        Index('idx_rag_stats_connector_id', 'connector_id'),
        Index('idx_rag_stats_timestamp', 'timestamp'),
    )


class VoiceTest(Base):
    """
    Voice testing results storage.

    Stores test results for STT, TTS, LLM, RAG queries, and full pipeline tests.
    """
    __tablename__ = 'voice_tests'

    id = Column(Integer, primary_key=True)
    test_type = Column(String(32), nullable=False)  # "stt", "tts", "llm", "full_pipeline", "rag_query"
    test_input = Column(Text)  # Audio file path, text query, prompt, etc.
    test_config = Column(JSONB)  # Test parameters (model, voice, threshold, etc.)
    result = Column(JSONB)  # Test results with timing, response, errors
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    executed_by_id = Column(Integer, ForeignKey('users.id'))
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    executor = relationship('User')

    __table_args__ = (
        Index('idx_voice_tests_test_type', 'test_type'),
        Index('idx_voice_tests_success', 'success'),
        Index('idx_voice_tests_executed_at', 'executed_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert voice test to dictionary for API responses."""
        return {
            'id': self.id,
            'test_type': self.test_type,
            'test_input': self.test_input,
            'test_config': self.test_config,
            'result': self.result,
            'success': self.success,
            'error_message': self.error_message,
            'executed_by': self.executor.username if self.executor else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
        }


# Export all models for Alembic
__all__ = [
    'Base', 'User', 'Policy', 'PolicyVersion', 'Secret', 'Device', 'AuditLog',
    'ServerConfig', 'ServiceRegistry', 'RAGConnector', 'RAGStats', 'VoiceTest'
]
