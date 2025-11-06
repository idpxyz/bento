"""Unit tests for InterceptorFactory.

Tests cover:
- Factory creation with configuration
- Building default chain
- Building specific interceptor chains
- Custom interceptor integration
- Configuration passing
- Convenience functions
"""

from bento.persistence.interceptor import (
    AuditInterceptor,
    InterceptorChain,
    InterceptorConfig,
    InterceptorFactory,
    OptimisticLockInterceptor,
    SoftDeleteInterceptor,
    create_default_chain,
)

# ==================== Factory Creation Tests ====================


def test_create_factory_default_config():
    """Test creating factory with default configuration."""
    factory = InterceptorFactory()
    assert factory is not None


def test_create_factory_with_config():
    """Test creating factory with custom configuration."""
    config = InterceptorConfig(
        enable_audit=True,
        enable_soft_delete=False,
        enable_optimistic_lock=True,
        actor="test@example.com",
    )
    factory = InterceptorFactory(config)
    assert factory is not None


def test_create_factory_with_none_config():
    """Test creating factory with None config uses defaults."""
    factory = InterceptorFactory(None)
    assert factory is not None


# ==================== Configuration Tests ====================


def test_config_default_values():
    """Test that InterceptorConfig has sensible defaults."""
    config = InterceptorConfig()

    assert config.enable_audit is True
    assert config.enable_soft_delete is True
    assert config.enable_optimistic_lock is True
    assert config.actor == "system"  # Default actor


def test_config_custom_values():
    """Test setting custom configuration values."""
    config = InterceptorConfig(
        enable_audit=False,
        enable_soft_delete=True,
        enable_optimistic_lock=False,
        actor="custom@example.com",
    )

    assert config.enable_audit is False
    assert config.enable_soft_delete is True
    assert config.enable_optimistic_lock is False
    assert config.actor == "custom@example.com"


def test_config_actor_none_defaults_to_system():
    """Test that None actor defaults to 'system'."""
    config = InterceptorConfig(actor=None)
    assert config.actor == "system"


# ==================== Build Chain Tests ====================


def test_build_chain_all_enabled():
    """Test building chain with all interceptors enabled."""
    config = InterceptorConfig(
        enable_audit=True,
        enable_soft_delete=True,
        enable_optimistic_lock=True,
        actor="test@example.com",
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    assert isinstance(chain, InterceptorChain)
    # Check that chain has interceptors
    assert len(chain._interceptors) == 3

    # Check types (order may vary based on priority)
    interceptor_types = {type(i) for i in chain._interceptors}
    assert AuditInterceptor in interceptor_types
    assert SoftDeleteInterceptor in interceptor_types
    assert OptimisticLockInterceptor in interceptor_types


def test_build_chain_only_audit():
    """Test building chain with only audit enabled."""
    config = InterceptorConfig(
        enable_audit=True,
        enable_soft_delete=False,
        enable_optimistic_lock=False,
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    assert len(chain._interceptors) == 1
    assert isinstance(chain._interceptors[0], AuditInterceptor)


def test_build_chain_only_soft_delete():
    """Test building chain with only soft delete enabled."""
    config = InterceptorConfig(
        enable_audit=False,
        enable_soft_delete=True,
        enable_optimistic_lock=False,
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    assert len(chain._interceptors) == 1
    assert isinstance(chain._interceptors[0], SoftDeleteInterceptor)


def test_build_chain_only_optimistic_lock():
    """Test building chain with only optimistic lock enabled."""
    config = InterceptorConfig(
        enable_audit=False,
        enable_soft_delete=False,
        enable_optimistic_lock=True,
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    assert len(chain._interceptors) == 1
    assert isinstance(chain._interceptors[0], OptimisticLockInterceptor)


def test_build_chain_all_disabled():
    """Test building chain with all interceptors disabled."""
    config = InterceptorConfig(
        enable_audit=False,
        enable_soft_delete=False,
        enable_optimistic_lock=False,
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    assert len(chain._interceptors) == 0


def test_build_chain_with_additional_interceptors():
    """Test building chain with additional custom interceptors."""
    from bento.persistence.interceptor import Interceptor, InterceptorPriority

    class CustomInterceptor(Interceptor):
        @property
        def priority(self):
            return InterceptorPriority.NORMAL

    config = InterceptorConfig(
        enable_audit=True,
        enable_soft_delete=False,
        enable_optimistic_lock=False,
    )
    factory = InterceptorFactory(config)

    custom = CustomInterceptor()
    chain = factory.build_chain(additional_interceptors=[custom])

    assert len(chain._interceptors) == 2
    interceptor_types = {type(i) for i in chain._interceptors}
    assert AuditInterceptor in interceptor_types
    assert CustomInterceptor in interceptor_types


def test_build_chain_with_multiple_additional_interceptors():
    """Test building chain with multiple additional interceptors."""
    from bento.persistence.interceptor import Interceptor, InterceptorPriority

    class CustomInterceptor1(Interceptor):
        @property
        def priority(self):
            return InterceptorPriority.HIGH

    class CustomInterceptor2(Interceptor):
        @property
        def priority(self):
            return InterceptorPriority.LOW

    config = InterceptorConfig(
        enable_audit=True, enable_soft_delete=False, enable_optimistic_lock=False
    )
    factory = InterceptorFactory(config)

    custom1 = CustomInterceptor1()
    custom2 = CustomInterceptor2()
    chain = factory.build_chain(additional_interceptors=[custom1, custom2])

    assert len(chain._interceptors) == 3


# ==================== Build Specific Chain Tests ====================


def test_build_audit_chain():
    """Test building chain with only audit interceptor."""
    config = InterceptorConfig(actor="test@example.com")
    factory = InterceptorFactory(config)

    chain = factory.build_audit_chain()

    assert len(chain._interceptors) == 1
    assert isinstance(chain._interceptors[0], AuditInterceptor)


def test_build_soft_delete_chain():
    """Test building chain with only soft delete interceptor."""
    config = InterceptorConfig(actor="test@example.com")
    factory = InterceptorFactory(config)

    chain = factory.build_soft_delete_chain()

    assert len(chain._interceptors) == 1
    assert isinstance(chain._interceptors[0], SoftDeleteInterceptor)


def test_build_optimistic_lock_chain():
    """Test building chain with only optimistic lock interceptor."""
    config = InterceptorConfig(actor="test@example.com")
    factory = InterceptorFactory(config)

    chain = factory.build_optimistic_lock_chain()

    assert len(chain._interceptors) == 1
    assert isinstance(chain._interceptors[0], OptimisticLockInterceptor)


def test_create_custom_chain():
    """Test creating fully custom chain."""
    from bento.persistence.interceptor import Interceptor, InterceptorPriority

    class CustomInterceptor(Interceptor):
        @property
        def priority(self):
            return InterceptorPriority.NORMAL

    factory = InterceptorFactory()

    custom1 = CustomInterceptor()
    custom2 = CustomInterceptor()
    chain = factory.create_custom_chain([custom1, custom2])

    assert len(chain._interceptors) == 2
    assert chain._interceptors[0] is custom1 or chain._interceptors[0] is custom2


# ==================== Actor Propagation Tests ====================


def test_audit_interceptor_receives_actor():
    """Test that AuditInterceptor receives actor from config."""
    config = InterceptorConfig(
        enable_audit=True,
        enable_soft_delete=False,
        enable_optimistic_lock=False,
        actor="custom@example.com",
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    audit_interceptor = chain._interceptors[0]
    assert isinstance(audit_interceptor, AuditInterceptor)
    assert audit_interceptor._actor == "custom@example.com"


def test_soft_delete_interceptor_receives_actor():
    """Test that SoftDeleteInterceptor receives actor from config."""
    config = InterceptorConfig(
        enable_audit=False,
        enable_soft_delete=True,
        enable_optimistic_lock=False,
        actor="custom@example.com",
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    soft_delete_interceptor = chain._interceptors[0]
    assert isinstance(soft_delete_interceptor, SoftDeleteInterceptor)
    assert soft_delete_interceptor._actor == "custom@example.com"


def test_optimistic_lock_interceptor_receives_config():
    """Test that OptimisticLockInterceptor receives config."""
    config = InterceptorConfig(
        enable_audit=False,
        enable_soft_delete=False,
        enable_optimistic_lock=True,
    )
    factory = InterceptorFactory(config)

    chain = factory.build_chain()

    lock_interceptor = chain._interceptors[0]
    assert isinstance(lock_interceptor, OptimisticLockInterceptor)
    # Interceptor should be enabled
    assert lock_interceptor.enabled is True


# ==================== Convenience Function Tests ====================


def test_create_default_chain_function():
    """Test create_default_chain convenience function."""
    chain = create_default_chain()

    assert isinstance(chain, InterceptorChain)
    # Should have all three standard interceptors
    assert len(chain._interceptors) == 3


def test_create_default_chain_with_actor():
    """Test create_default_chain with custom actor."""
    chain = create_default_chain(actor="custom@example.com")

    assert isinstance(chain, InterceptorChain)

    # Find audit interceptor and check actor
    audit_interceptor = next(i for i in chain._interceptors if isinstance(i, AuditInterceptor))
    assert audit_interceptor._actor == "custom@example.com"


def test_create_default_chain_with_none_actor():
    """Test create_default_chain with None actor."""
    chain = create_default_chain(actor=None)

    assert isinstance(chain, InterceptorChain)

    # Should use default 'system' actor
    audit_interceptor = next(i for i in chain._interceptors if isinstance(i, AuditInterceptor))
    assert audit_interceptor._actor == "system"


# ==================== Priority Ordering Tests ====================


def test_chain_has_correct_priority_order():
    """Test that built chain has interceptors in correct priority order."""
    factory = InterceptorFactory()
    chain = factory.build_chain()

    # Get priorities
    priorities = [i.priority for i in chain._interceptors]

    # Should be in ascending order (lower number = higher priority)
    assert priorities == sorted(priorities)


def test_optimistic_lock_higher_priority_than_audit():
    """Test that OptimisticLock has higher priority than Audit."""
    factory = InterceptorFactory()
    chain = factory.build_chain()

    lock_index = next(
        i
        for i, interceptor in enumerate(chain._interceptors)
        if isinstance(interceptor, OptimisticLockInterceptor)
    )
    audit_index = next(
        i
        for i, interceptor in enumerate(chain._interceptors)
        if isinstance(interceptor, AuditInterceptor)
    )

    # Lock should come before audit (lower index = higher priority)
    assert lock_index < audit_index


# ==================== Edge Cases ====================


def test_build_chain_multiple_times_creates_new_chains():
    """Test that building chain multiple times creates independent chains."""
    factory = InterceptorFactory()

    chain1 = factory.build_chain()
    chain2 = factory.build_chain()

    # Should be different instances
    assert chain1 is not chain2
    assert chain1._interceptors is not chain2._interceptors


def test_factory_with_empty_additional_interceptors():
    """Test building chain with empty additional interceptors list."""
    factory = InterceptorFactory()
    chain = factory.build_chain(additional_interceptors=[])

    # Should still have standard interceptors
    assert len(chain._interceptors) == 3


def test_factory_with_none_additional_interceptors():
    """Test building chain with None additional interceptors."""
    factory = InterceptorFactory()
    chain = factory.build_chain(additional_interceptors=None)

    # Should still have standard interceptors
    assert len(chain._interceptors) == 3
