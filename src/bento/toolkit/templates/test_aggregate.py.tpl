"""{{Name}} 聚合根单元测试"""
import pytest
from contexts.{{context}}.domain.{{name_lower}} import {{Name}}


class Test{{Name}}:
    """{{Name}} 聚合根单元测试

    测试聚合根的不变量、业务规则和行为。
    遵循 AAA 模式：Arrange - Act - Assert
    """

    def test_create_valid_{{name_lower}}(self):
        """测试创建有效的聚合根"""
        # Arrange & Act
        {{name_lower}} = {{Name}}(
            id="test-id-123",
            # TODO: 添加其他字段
        )

        # Assert
        assert {{name_lower}}.id == "test-id-123"
        # TODO: 验证其他字段

    def test_{{name_lower}}_invariants(self):
        """测试聚合根不变量"""
        # TODO: 测试违反不变量的场景
        # 例如：
        # with pytest.raises(ValueError, match="must not be empty"):
        #     {{Name}}(id="", name="Test")
        pass

    def test_{{name_lower}}_business_rules(self):
        """测试业务规则"""
        # TODO: 测试业务方法
        # 例如：
        # {{name_lower}} = {{Name}}(id="123", is_active=True)
        # {{name_lower}}.deactivate()
        # assert {{name_lower}}.is_active is False
        pass

    def test_{{name_lower}}_raises_domain_events(self):
        """测试领域事件发布"""
        # TODO: 测试领域事件
        # 例如：
        # {{name_lower}} = {{Name}}(id="123")
        # {{name_lower}}.some_action()
        # events = {{name_lower}}.collect_events()
        # assert len(events) == 1
        # assert isinstance(events[0], {{Name}}SomethingHappened)
        pass
