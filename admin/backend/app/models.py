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
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index, UniqueConstraint, Float, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
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


class IntentCategory(Base):
    """
    Intent categories for organizing and configuring intent detection.

    Provides hierarchical organization of intents (e.g., control, query, rag).
    """
    __tablename__ = 'intent_categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('intent_categories.id'))
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship('IntentCategory', remote_side=[id], backref='children')
    confidence_rules = relationship('ConfidenceScoreRule', back_populates='category', cascade='all, delete-orphan')
    enhancement_rules = relationship('ResponseEnhancementRule', back_populates='category', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_intent_categories_enabled', 'enabled'),
        Index('idx_intent_categories_parent_id', 'parent_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'parent_id': self.parent_id,
            'enabled': self.enabled,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class HallucinationCheck(Base):
    """
    Anti-hallucination validation rules.

    Defines validation checks to prevent AI from generating false information.
    """
    __tablename__ = 'hallucination_checks'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    check_type = Column(String(50), nullable=False)  # 'required_elements', 'fact_checking', 'confidence_threshold', 'cross_validation'
    applies_to_categories = Column(ARRAY(String), default=[])  # Empty = all categories
    enabled = Column(Boolean, default=True)
    severity = Column(String(20), default='warning')  # 'error', 'warning', 'info'
    configuration = Column(JSONB, nullable=False)  # Flexible config for different check types
    error_message_template = Column(Text)
    auto_fix_enabled = Column(Boolean, default=False)
    auto_fix_prompt_template = Column(Text)
    require_cross_model_validation = Column(Boolean, default=False)
    confidence_threshold = Column(Float, default=0.7)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String(100))

    __table_args__ = (
        Index('idx_hallucination_checks_enabled', 'enabled'),
        Index('idx_hallucination_checks_categories', 'applies_to_categories'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'check_type': self.check_type,
            'applies_to_categories': self.applies_to_categories,
            'enabled': self.enabled,
            'severity': self.severity,
            'configuration': self.configuration,
            'error_message_template': self.error_message_template,
            'auto_fix_enabled': self.auto_fix_enabled,
            'auto_fix_prompt_template': self.auto_fix_prompt_template,
            'require_cross_model_validation': self.require_cross_model_validation,
            'confidence_threshold': self.confidence_threshold,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


class CrossValidationModel(Base):
    """
    Cross-model validation configuration.

    Configures multiple models for ensemble validation to reduce hallucinations.
    """
    __tablename__ = 'cross_validation_models'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    model_id = Column(String(100), nullable=False)  # e.g., 'phi3:mini', 'llama3.1:8b-q4'
    model_type = Column(String(50), nullable=False)  # 'primary', 'validation', 'fallback'
    endpoint_url = Column(String(500))
    enabled = Column(Boolean, default=True)
    use_for_categories = Column(ARRAY(String), default=[])
    temperature = Column(Float, default=0.1)
    max_tokens = Column(Integer, default=200)
    timeout_seconds = Column(Integer, default=30)
    weight = Column(Float, default=1.0)  # Weight for ensemble validation
    min_confidence_required = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_cross_validation_enabled', 'enabled', 'model_type'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'model_id': self.model_id,
            'model_type': self.model_type,
            'endpoint_url': self.endpoint_url,
            'enabled': self.enabled,
            'use_for_categories': self.use_for_categories,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout_seconds': self.timeout_seconds,
            'weight': self.weight,
            'min_confidence_required': self.min_confidence_required,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class MultiIntentConfig(Base):
    """
    Multi-intent processing configuration.

    Controls how queries with multiple intents are parsed and processed.
    """
    __tablename__ = 'multi_intent_config'

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=True)
    max_intents_per_query = Column(Integer, default=3)
    separators = Column(ARRAY(String), default=[' and ', ' then ', ' also ', ', then ', '; '])
    context_preservation = Column(Boolean, default=True)  # Preserve context between split intents
    parallel_processing = Column(Boolean, default=False)  # Process intents in parallel vs sequential
    combination_strategy = Column(String(50), default='concatenate')  # 'concatenate', 'summarize', 'hierarchical'
    min_words_per_intent = Column(Integer, default=2)
    context_words_to_preserve = Column(ARRAY(String), default=[])  # Words to carry forward if missing
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'enabled': self.enabled,
            'max_intents_per_query': self.max_intents_per_query,
            'separators': self.separators,
            'context_preservation': self.context_preservation,
            'parallel_processing': self.parallel_processing,
            'combination_strategy': self.combination_strategy,
            'min_words_per_intent': self.min_words_per_intent,
            'context_words_to_preserve': self.context_words_to_preserve,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class IntentChainRule(Base):
    """
    Intent chain rules for multi-step operations.

    Defines sequences of intents triggered by patterns (e.g., "goodnight" routine).
    """
    __tablename__ = 'intent_chain_rules'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, index=True)
    trigger_pattern = Column(String(500))  # Regex pattern that triggers this chain
    intent_sequence = Column(ARRAY(String), nullable=False)  # Ordered list of intents to execute
    enabled = Column(Boolean, default=True)
    description = Column(Text)
    examples = Column(ARRAY(String))
    require_all = Column(Boolean, default=False)  # Whether all intents in chain must succeed
    stop_on_error = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_chain_rules_enabled', 'enabled'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'trigger_pattern': self.trigger_pattern,
            'intent_sequence': self.intent_sequence,
            'enabled': self.enabled,
            'description': self.description,
            'examples': self.examples,
            'require_all': self.require_all,
            'stop_on_error': self.stop_on_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ValidationTestScenario(Base):
    """
    Validation test scenarios for testing anti-hallucination checks.

    Stores test cases to verify validation rules work correctly.
    """
    __tablename__ = 'validation_test_scenarios'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    test_query = Column(Text, nullable=False)
    initial_response = Column(Text, nullable=False)
    expected_validation_result = Column(String(20))  # 'pass', 'fail', 'warning'
    expected_checks_triggered = Column(ARRAY(String))
    expected_final_response = Column(Text)
    category = Column(String(50))
    enabled = Column(Boolean, default=True)
    last_run_result = Column(JSONB)
    last_run_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_validation_scenarios_enabled', 'enabled'),
        Index('idx_validation_scenarios_category', 'category'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'test_query': self.test_query,
            'initial_response': self.initial_response,
            'expected_validation_result': self.expected_validation_result,
            'expected_checks_triggered': self.expected_checks_triggered,
            'expected_final_response': self.expected_final_response,
            'category': self.category,
            'enabled': self.enabled,
            'last_run_result': self.last_run_result,
            'last_run_date': self.last_run_date.isoformat() if self.last_run_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ConfidenceScoreRule(Base):
    """
    Confidence score adjustment rules.

    Defines factors that boost or penalize confidence scores for intent classification.
    """
    __tablename__ = 'confidence_score_rules'

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('intent_categories.id', ondelete='CASCADE'))
    factor_name = Column(String(100), nullable=False)  # 'pattern_match_count', 'entity_presence', 'query_length'
    factor_type = Column(String(50), nullable=False)  # 'boost', 'penalty', 'multiplier'
    condition = Column(JSONB)  # e.g., {"min_matches": 2, "required_entities": ["room", "device"]}
    adjustment_value = Column(Float, nullable=False)  # Amount to adjust confidence by
    max_impact = Column(Float, default=0.2)  # Maximum impact this rule can have
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    category = relationship('IntentCategory', back_populates='confidence_rules')

    __table_args__ = (
        Index('idx_confidence_rules_category', 'category_id', 'enabled'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'factor_name': self.factor_name,
            'factor_type': self.factor_type,
            'condition': self.condition,
            'adjustment_value': self.adjustment_value,
            'max_impact': self.max_impact,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ResponseEnhancementRule(Base):
    """
    Response enhancement rules.

    Defines rules for enhancing AI responses with additional context or formatting.
    """
    __tablename__ = 'response_enhancement_rules'

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('intent_categories.id', ondelete='CASCADE'))
    enhancement_type = Column(String(50), nullable=False)  # 'add_context', 'format_data', 'add_suggestions', 'clarify_ambiguity'
    trigger_condition = Column(JSONB)  # When to apply this enhancement
    enhancement_template = Column(Text)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    category = relationship('IntentCategory', back_populates='enhancement_rules')

    __table_args__ = (
        Index('idx_enhancement_rules_category', 'category_id', 'enabled'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'enhancement_type': self.enhancement_type,
            'trigger_condition': self.trigger_condition,
            'enhancement_template': self.enhancement_template,
            'enabled': self.enabled,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ConversationSettings(Base):
    """
    Conversation context management settings.

    Global settings for conversation session management, history tracking,
    and context preservation between queries.
    """
    __tablename__ = 'conversation_settings'

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    use_context = Column(Boolean, nullable=False, default=True)
    max_messages = Column(Integer, nullable=False, default=20)
    timeout_seconds = Column(Integer, nullable=False, default=1800)  # 30 minutes
    cleanup_interval_seconds = Column(Integer, nullable=False, default=60)
    session_ttl_seconds = Column(Integer, nullable=False, default=3600)  # 1 hour
    max_llm_history_messages = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation settings to dictionary for API responses."""
        return {
            'id': self.id,
            'enabled': self.enabled,
            'use_context': self.use_context,
            'max_messages': self.max_messages,
            'timeout_seconds': self.timeout_seconds,
            'cleanup_interval_seconds': self.cleanup_interval_seconds,
            'session_ttl_seconds': self.session_ttl_seconds,
            'max_llm_history_messages': self.max_llm_history_messages,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ClarificationSettings(Base):
    """
    Global clarification system settings.

    Controls whether clarifying questions are enabled and global timeout values.
    """
    __tablename__ = 'clarification_settings'

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    timeout_seconds = Column(Integer, nullable=False, default=300)  # 5 minutes
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert clarification settings to dictionary for API responses."""
        return {
            'id': self.id,
            'enabled': self.enabled,
            'timeout_seconds': self.timeout_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ClarificationType(Base):
    """
    Individual clarification type configurations.

    Defines different types of clarifying questions (device, location, time, sports_team)
    with individual enable/disable controls and priority ordering.
    """
    __tablename__ = 'clarification_types'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    timeout_seconds = Column(Integer)  # Override global timeout if set
    priority = Column(Integer, nullable=False, default=0)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_clarification_types_enabled', 'enabled'),
        Index('idx_clarification_types_priority', 'priority'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert clarification type to dictionary for API responses."""
        return {
            'id': self.id,
            'type': self.type,
            'enabled': self.enabled,
            'timeout_seconds': self.timeout_seconds,
            'priority': self.priority,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SportsTeamDisambiguation(Base):
    """
    Sports team disambiguation rules.

    Maps ambiguous team names (Giants, Cardinals, etc.) to specific options
    with JSONB data containing full team information.
    """
    __tablename__ = 'sports_team_disambiguation'

    id = Column(Integer, primary_key=True)
    team_name = Column(String(100), nullable=False, index=True)
    requires_disambiguation = Column(Boolean, nullable=False, default=True)
    options = Column(JSONB, nullable=False)  # [{"id": "ny-giants", "label": "NY Giants (NFL)", "sport": "football"}]
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_sports_team_name', 'team_name'),
        Index('idx_sports_disambiguation_required', 'requires_disambiguation'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert sports team disambiguation to dictionary for API responses."""
        return {
            'id': self.id,
            'team_name': self.team_name,
            'requires_disambiguation': self.requires_disambiguation,
            'options': self.options,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DeviceDisambiguationRule(Base):
    """
    Device disambiguation rules for Home Assistant devices.

    Defines when to ask clarifying questions for device types (lights, switches, etc.)
    based on number of matching entities.
    """
    __tablename__ = 'device_disambiguation_rules'

    id = Column(Integer, primary_key=True)
    device_type = Column(String(50), nullable=False, unique=True, index=True)
    requires_disambiguation = Column(Boolean, nullable=False, default=True)
    min_entities_for_clarification = Column(Integer, nullable=False, default=2)
    include_all_option = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_device_type_enabled', 'device_type', 'requires_disambiguation'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert device disambiguation rule to dictionary for API responses."""
        return {
            'id': self.id,
            'device_type': self.device_type,
            'requires_disambiguation': self.requires_disambiguation,
            'min_entities_for_clarification': self.min_entities_for_clarification,
            'include_all_option': self.include_all_option,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationAnalytics(Base):
    """
    Analytics event tracking for conversation features.

    Records events like session creation, follow-up detection, and clarification triggers
    for monitoring and optimization.
    """
    __tablename__ = 'conversation_analytics'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_metadata = Column('metadata', JSONB)  # Maps Python attr 'event_metadata' to DB column 'metadata'
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index('idx_analytics_event_type', 'event_type'),
        Index('idx_analytics_timestamp', 'timestamp'),
        Index('idx_analytics_session_id', 'session_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation analytics to dictionary for API responses."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'event_type': self.event_type,
            'metadata': self.event_metadata,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class LLMBackend(Base):
    """
    LLM backend configuration for model routing.

    Supports per-model backend selection (Ollama, MLX, Auto) with performance
    tracking and runtime configuration. Enables hybrid deployment with multiple
    LLM backends running simultaneously.
    """
    __tablename__ = 'llm_backends'

    id = Column(Integer, primary_key=True)
    model_name = Column(String(255), unique=True, nullable=False, index=True)
    backend_type = Column(String(32), nullable=False)  # ollama, mlx, auto
    endpoint_url = Column(String(500), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100)  # Lower = higher priority for 'auto' mode

    # Performance tracking
    avg_tokens_per_sec = Column(Float)
    avg_latency_ms = Column(Float)
    total_requests = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)

    # Configuration
    max_tokens = Column(Integer, default=2048)
    temperature_default = Column(Float, default=0.7)
    timeout_seconds = Column(Integer, default=60)

    # Metadata
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey('users.id'))

    # Relationships
    creator = relationship('User')

    __table_args__ = (
        Index('idx_llm_backends_enabled', 'enabled'),
        Index('idx_llm_backends_backend_type', 'backend_type'),
        Index('idx_llm_backends_model_name', 'model_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert LLM backend to dictionary for API responses."""
        return {
            'id': self.id,
            'model_name': self.model_name,
            'backend_type': self.backend_type,
            'endpoint_url': self.endpoint_url,
            'enabled': self.enabled,
            'priority': self.priority,
            'avg_tokens_per_sec': self.avg_tokens_per_sec,
            'avg_latency_ms': self.avg_latency_ms,
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'max_tokens': self.max_tokens,
            'temperature_default': self.temperature_default,
            'timeout_seconds': self.timeout_seconds,
            'description': self.description,
            'created_by': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Feature(Base):
    """
    System feature flags for performance tracking and optimization.

    Tracks individual features in the system (intent classification, RAG services,
    caching, etc.) with enable/disable state and latency contribution.
    """
    __tablename__ = 'features'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False, index=True)  # 'processing', 'rag', 'optimization', 'integration'
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # Performance impact
    avg_latency_ms = Column(Float)  # Average latency contribution
    hit_rate = Column(Float)  # For caching features

    # Configuration
    required = Column(Boolean, default=False)  # Cannot be disabled
    priority = Column(Integer, default=100)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_features_enabled', 'enabled'),
        Index('idx_features_category', 'category'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert feature to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'enabled': self.enabled,
            'avg_latency_ms': self.avg_latency_ms,
            'hit_rate': self.hit_rate,
            'required': self.required,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class LLMPerformanceMetric(Base):
    """
    LLM performance metrics for monitoring and analysis.

    Stores detailed performance metrics for each LLM request including latency,
    token generation speed, and contextual information for debugging and optimization.
    Enables historical analysis and performance regression detection.
    """
    __tablename__ = 'llm_performance_metrics'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    backend = Column(String(50), nullable=False, index=True)
    latency_seconds = Column(Numeric(8, 3), nullable=False)
    tokens_generated = Column(Integer, nullable=False)
    tokens_per_second = Column(Numeric(10, 2), nullable=False)

    # Component latencies (milliseconds)
    gateway_latency_ms = Column(Float)
    intent_classification_latency_ms = Column(Float)
    rag_lookup_latency_ms = Column(Float)
    llm_inference_latency_ms = Column(Float)
    response_assembly_latency_ms = Column(Float)
    cache_lookup_latency_ms = Column(Float)

    # Feature flags (JSONB for flexibility)
    features_enabled = Column(JSONB)  # {"intent_classification": true, "rag": true, "caching": false}

    # Optional context fields
    prompt_tokens = Column(Integer, nullable=True)
    request_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    user_id = Column(String(100), nullable=True)
    zone = Column(String(100), nullable=True)
    intent = Column(String(100), nullable=True, index=True)

    __table_args__ = (
        Index('idx_llm_metrics_timestamp', 'timestamp'),
        Index('idx_llm_metrics_model', 'model'),
        Index('idx_llm_metrics_backend', 'backend'),
        Index('idx_llm_metrics_intent', 'intent'),
        Index('idx_llm_metrics_composite', 'timestamp', 'model', 'backend'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert LLM performance metric to dictionary for API responses."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'model': self.model,
            'backend': self.backend,
            'latency_seconds': float(self.latency_seconds) if self.latency_seconds else None,
            'gateway_latency_ms': self.gateway_latency_ms,
            'intent_classification_latency_ms': self.intent_classification_latency_ms,
            'rag_lookup_latency_ms': self.rag_lookup_latency_ms,
            'llm_inference_latency_ms': self.llm_inference_latency_ms,
            'response_assembly_latency_ms': self.response_assembly_latency_ms,
            'cache_lookup_latency_ms': self.cache_lookup_latency_ms,
            'features_enabled': self.features_enabled,
            'tokens_generated': self.tokens_generated,
            'tokens_per_second': float(self.tokens_per_second) if self.tokens_per_second else None,
            'prompt_tokens': self.prompt_tokens,
            'request_id': self.request_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'zone': self.zone,
            'intent': self.intent,
        }


class IntentPattern(Base):
    """
    Intent classification patterns for configurable routing.

    Maps keywords to intent categories with confidence weights.
    Replaces hardcoded patterns in intent_classifier.py.
    """
    __tablename__ = 'intent_patterns'

    id = Column(Integer, primary_key=True)
    intent_category = Column(String(50), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False)  # e.g., "basic", "dimming", "temperature"
    keyword = Column(String(100), nullable=False, index=True)
    confidence_weight = Column(Float, nullable=False, default=1.0)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('intent_category', 'pattern_type', 'keyword', name='uq_intent_pattern_keyword'),
        Index('idx_intent_patterns_category', 'intent_category'),
        Index('idx_intent_patterns_enabled', 'enabled'),
        Index('idx_intent_patterns_keyword', 'keyword'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent pattern to dictionary for API responses."""
        return {
            'id': self.id,
            'intent_category': self.intent_category,
            'pattern_type': self.pattern_type,
            'keyword': self.keyword,
            'confidence_weight': self.confidence_weight,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class IntentRouting(Base):
    """
    Intent routing configuration.

    Defines how each intent category should be routed:
    - To RAG services (weather, sports, etc.)
    - To web search providers
    - To LLM for processing

    Replaces hardcoded RAG_INTENTS list in provider_router.py.
    """
    __tablename__ = 'intent_routing'

    id = Column(Integer, primary_key=True)
    intent_category = Column(String(50), nullable=False, unique=True, index=True)
    use_rag = Column(Boolean, nullable=False, default=False)
    rag_service_url = Column(String(255), nullable=True)  # e.g., "http://localhost:8010"
    use_web_search = Column(Boolean, nullable=False, default=False)
    use_llm = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100, index=True)  # Higher = checked first
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('intent_category', name='uq_intent_routing_category'),
        Index('idx_intent_routing_category', 'intent_category'),
        Index('idx_intent_routing_enabled', 'enabled'),
        Index('idx_intent_routing_priority', 'priority'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent routing to dictionary for API responses."""
        return {
            'id': self.id,
            'intent_category': self.intent_category,
            'use_rag': self.use_rag,
            'rag_service_url': self.rag_service_url,
            'use_web_search': self.use_web_search,
            'use_llm': self.use_llm,
            'priority': self.priority,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProviderRouting(Base):
    """
    Web search provider routing configuration.

    Defines provider priority for each intent category.
    Replaces hardcoded INTENT_PROVIDER_SETS in provider_router.py.
    """
    __tablename__ = 'provider_routing'

    id = Column(Integer, primary_key=True)
    intent_category = Column(String(50), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False, index=True)  # e.g., "duckduckgo", "brave"
    priority = Column(Integer, nullable=False, index=True)  # 1 = first, 2 = second, etc.
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('intent_category', 'provider_name', name='uq_provider_routing_category_provider'),
        Index('idx_provider_routing_category', 'intent_category'),
        Index('idx_provider_routing_provider', 'provider_name'),
        Index('idx_provider_routing_enabled', 'enabled'),
        Index('idx_provider_routing_priority', 'priority'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert provider routing to dictionary for API responses."""
        return {
            'id': self.id,
            'intent_category': self.intent_category,
            'provider_name': self.provider_name,
            'priority': self.priority,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# Export all models for Alembic
__all__ = [
    'Base', 'User', 'Policy', 'PolicyVersion', 'Secret', 'Device', 'AuditLog',
    'ServerConfig', 'ServiceRegistry', 'RAGConnector', 'RAGStats', 'VoiceTest',
    'IntentCategory', 'HallucinationCheck', 'CrossValidationModel', 'MultiIntentConfig',
    'IntentChainRule', 'ValidationTestScenario', 'ConfidenceScoreRule', 'ResponseEnhancementRule',
    'ConversationSettings', 'ClarificationSettings', 'ClarificationType',
    'SportsTeamDisambiguation', 'DeviceDisambiguationRule', 'ConversationAnalytics',
    'LLMBackend', 'LLMPerformanceMetric', 'Feature',
    'IntentPattern', 'IntentRouting', 'ProviderRouting'
]
