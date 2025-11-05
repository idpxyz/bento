"""配置管理器

提供统一的配置管理接口，支持：
1. 多提供器配置加载和合并
2. Pydantic模型验证
3. 配置热重载
4. 配置变更通知
5. 配置值加密/解密
"""

import logging
from copy import deepcopy
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from idp.framework.infrastructure.config.core.base import (
    ConfigSection,
    ConfigurationError,
    InvalidConfigurationError,
)
from idp.framework.infrastructure.config.core.provider import (
    ConfigProvider,
    ProviderRegistry,
)
from idp.framework.shared.utils.dict import DictUtils

T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """配置错误基类"""
    pass


class ConfigValidationError(ConfigurationError):
    """配置验证错误"""
    pass


class ConfigLoadError(ConfigurationError):
    """配置加载错误"""
    pass


class ConfigRegistry:
    """配置注册表，管理配置段"""

    def __init__(self):
        self._sections: Dict[str, ConfigSection] = {}

    def register(self, name: str, schema_class: Type[BaseModel]) -> ConfigSection:
        """注册配置段

        Args:
            name: 配置名称
            schema_class: 配置模式类

        Returns:
            ConfigSection: 配置段实例
        """
        section = ConfigSection(schema_class)
        self._sections[name] = section
        return section

    def get_section(self, name: str) -> Optional[ConfigSection]:
        """获取配置段

        Args:
            name: 配置名称

        Returns:
            Optional[ConfigSection]: 配置段实例，如果不存在则返回None
        """
        return self._sections.get(name)

    def get_sections(self) -> List[str]:
        """获取所有配置段名称

        Returns:
            List[str]: 配置段名称列表
        """
        return list(self._sections.keys())


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self._sections: Dict[str, Type[BaseModel]] = {}
        self._providers: Dict[str, List[ConfigProvider]] = {}
        self._configs: Dict[str, BaseModel] = {}
        self._initialized = False
        self._loaded_sections = set()  # 跟踪已加载的配置段
        self._cached_configs: Dict[str, Dict[str, Any]] = {}
        self._change_listeners: Dict[str,
                                     List[Callable[[Dict[str, Any]], None]]] = {}
        self._registry = ConfigRegistry()
        self._provider_registry = ProviderRegistry()

    def register_section(self, section_name: str, model: Type[BaseModel]) -> None:
        """注册配置段

        Args:
            section_name: 配置段名称
            model: 配置模型类
        """
        self._sections[section_name] = model
        self._providers[section_name] = []
        self._loaded_sections.discard(section_name)  # 重置加载状态

    def register_provider(self, section_name: str, provider: ConfigProvider) -> None:
        """注册配置提供者

        Args:
            section_name: 配置段名称
            provider: 配置提供者
        """
        if section_name not in self._providers:
            self._providers[section_name] = []
        self._providers[section_name].append(provider)
        self._loaded_sections.discard(section_name)  # 重置加载状态

    async def register_and_merge(
        self,
        first_arg,
        model: Optional[Type[BaseModel]] = None,
        namespace: Optional[str] = None,
        cache: bool = True
    ) -> Dict[str, Any] | BaseModel:
        """注册配置提供器并合并配置（支持两种调用方式）。

        1. 新式调用（推荐）：

           await register_and_merge([
               YamlProvider(...),
               EnvProvider(...)
           ], model=MyConfigSchema)

        2. 旧式调用（仅 section -> providers 已预注册）：

           await register_and_merge("logger", MyConfigSchema)

        为了兼容旧代码，我们根据 *first_arg* 的类型自动分支处理：
        - 如果是 list 视为"提供器列表"
        - 否则视为"section 名称"
        """

        # --- 分支 1: 新式（列表参数） --------------------------------------------------
        if isinstance(first_arg, list):
            # type: ignore[arg-type]
            providers: List[ConfigProvider] = first_arg

            if not providers:
                raise ConfigurationError("至少需要一个配置提供器")

            ns = namespace or providers[0].get_namespace()

            # 校验命名空间一致性
            if not all(p.get_namespace() == ns for p in providers):
                raise ConfigurationError("所有配置提供器必须使用相同的命名空间")

            # 缓存命中
            if cache and ns in self._cached_configs:
                return self._cached_configs[ns]

            # 注册 section & provider 列表
            if model is None:
                raise ConfigurationError("基于提供器调用模式必须显式传入 model 参数")

            self.register_section(ns, model)
            self._providers[ns] = providers  # 覆盖当前 providers 列表

            # 使用内部合并逻辑，处理 default + 环境配置展开
            try:
                merged_config: Dict[str, Any] = self._merge_configs(providers)
            except Exception as e:
                logger.error(f"合并配置失败: {e}")
                raise

            # 如果提供了 Pydantic 模型进行验证
            if model is not None:
                validated = model.model_validate(
                    merged_config)  # type: ignore[arg-type]
                merged_config = validated.model_dump(
                    exclude_none=True)  # type: ignore[assignment]

            # 写入缓存
            if cache:
                self._cached_configs[ns] = merged_config

            # 保存到 _configs
            self._configs[ns] = merged_config  # type: ignore[assignment]
            self._loaded_sections.add(ns)

            return merged_config

        # --- 分支 2: 旧式（section 名称 + model） --------------------------------------
        section_name: str = first_arg  # type: ignore[assignment]

        if model is None:
            raise ConfigurationError("旧式调用模式必须同时提供 model 参数")

        # 如果配置段已经加载过，直接返回缓存的配置
        if section_name in self._loaded_sections and section_name in self._configs:
            return self._configs[section_name]

        # 注册配置段
        self.register_section(section_name, model)

        providers = self._providers.get(section_name, [])

        # 没有注册 provider，返回模型默认值
        if not providers:
            config = model()  # type: ignore[call-arg]
            self._configs[section_name] = config
            self._loaded_sections.add(section_name)
            return config

        try:
            merged_config = self._merge_configs(providers)
        except Exception as e:
            logger.error(f"合并配置失败: {e}")
            raise

        # 验证并转换
        config_obj = model.model_validate(merged_config)
        self._configs[section_name] = config_obj
        self._loaded_sections.add(section_name)

        return config_obj

    def initialize(self, env_name: Optional[str] = None) -> None:
        """初始化配置系统

        Args:
            env_name: 环境名称，用于加载对应的环境配置

        Raises:
            ConfigurationError: 配置初始化失败
        """
        if self._initialized:
            return

        try:
            # 打印已注册的配置段和提供器
            self.print_registry_info()

            print(f"🚀 [ConfigManager] 正在初始化配置...")

            # 如果需要对环境特有的逻辑，应该由用户自行处理，不应在此处创建提供器

            # 加载所有提供器的配置
            for provider in self._provider_registry.get_providers():
                namespace = provider.get_namespace()
                print(
                    f"🔄 [ConfigManager] 加载提供器 {provider.__class__.__name__} 的配置 (命名空间: {namespace})")
                config_data = provider.load()

                # 更新对应的配置段
                section = self._registry.get_section(namespace)
                if section:
                    print(f"📝 [ConfigManager] 更新配置段 {namespace}")
                    try:
                        section.update(config_data)
                    except InvalidConfigurationError as e:
                        # 为验证错误提供更丰富的上下文信息
                        print(f"❌ [ConfigManager] 配置验证失败: {namespace}")
                        print(f"\n{'='*60}\n🚨 配置错误: {e}\n{'='*60}\n")
                        raise
                else:
                    print(f"⚠️ [ConfigManager] 没有找到对应的配置段: {namespace}")

            self._initialized = True
            print(f"✅ [ConfigManager] 配置初始化完成")
        except InvalidConfigurationError as e:
            # 已经在上面打印了详细错误，这里只需传递异常
            raise ConfigurationError(f"配置验证失败，请查看上方详细错误信息")
        except Exception as e:
            print(f"❌ [ConfigManager] 配置初始化失败: {e}")
            raise ConfigurationError(f"配置初始化失败: {e}")

    def reload(self) -> None:
        """重新加载所有配置

        Raises:
            ConfigurationError: 配置重载失败
        """
        try:
            print(f"🔄 [ConfigManager] 正在重新加载配置...")

            # 重新加载所有提供器的配置
            for provider in self._provider_registry.get_providers():
                namespace = provider.get_namespace()
                print(
                    f"🔄 [ConfigManager] 重新加载提供器 {provider.__class__.__name__} 的配置 (命名空间: {namespace})")
                config_data = provider.load()

                # 更新对应的配置段
                section = self._registry.get_section(namespace)
                if section:
                    print(f"📝 [ConfigManager] 更新配置段 {namespace}")
                    try:
                        section.update(config_data)
                    except InvalidConfigurationError as e:
                        # 为验证错误提供更丰富的上下文信息
                        print(f"❌ [ConfigManager] 配置验证失败: {namespace}")
                        print(f"\n{'='*60}\n🚨 配置错误: {e}\n{'='*60}\n")
                        raise
                else:
                    print(f"⚠️ [ConfigManager] 没有找到对应的配置段: {namespace}")

            print(f"✅ [ConfigManager] 配置重新加载完成")
        except InvalidConfigurationError as e:
            # 已经在上面打印了详细错误，这里只需传递异常
            raise ConfigurationError(f"配置验证失败，请查看上方详细错误信息")
        except Exception as e:
            print(f"❌ [ConfigManager] 配置重载失败: {e}")
            raise ConfigurationError(f"配置重载失败: {e}")

    def get_config(self, name: str, model_class: Optional[Type[T]] = None) -> Any:
        """获取指定名称的配置

        Args:
            name: 配置名称
            model_class: 配置模型类，用于类型检查（可选）

        Returns:
            Any: 配置实例

        Raises:
            ConfigurationError: 配置不存在或类型不匹配
        """
        if not self._initialized:
            self.initialize()

        section = self._registry.get_section(name)
        if not section:
            print(f"❌ [ConfigManager] 配置不存在: {name}")
            raise ConfigurationError(f"配置不存在: {name}")

        config = section.get()

        # 类型检查
        if model_class and not isinstance(config, model_class):
            print(
                f"❌ [ConfigManager] 配置类型不匹配: {name}, 期望 {model_class.__name__}, 实际 {type(config).__name__}")
            raise ConfigurationError(
                f"配置类型不匹配: {name}, 期望 {model_class.__name__}, 实际 {type(config).__name__}")

        if model_class:
            return cast(model_class, config)
        return config

    def get_raw_config(self, name: str) -> Dict[str, Any]:
        """获取指定配置段的原始配置数据

        Args:
            name: 配置段名称

        Returns:
            Dict[str, Any]: 原始配置数据

        Raises:
            ConfigurationError: 配置不存在
        """
        if not self._initialized:
            self.initialize()

        section = self._registry.get_section(name)
        if not section:
            print(f"❌ [ConfigManager] 配置不存在: {name}")
            raise ConfigurationError(f"配置不存在: {name}")

        return section.get_raw_data()

    def get_config_by_path(self, name: str, path: str, default: Any = None) -> Any:
        """通过路径获取配置值

        Args:
            name: 配置段名称
            path: 配置路径，以点分隔，如 "connection.pool.min_size"
            default: 如果路径不存在，返回的默认值

        Returns:
            Any: 配置值

        Raises:
            ConfigurationError: 配置不存在
        """
        raw_config = self.get_raw_config(name)
        value = self._get_by_path(raw_config, path, default)

        if value == default and path:
            print(
                f"⚠️ [ConfigManager] 配置路径不存在: {name}.{path}, 使用默认值: {default}")

        return value

    def _get_by_path(self, config_dict: Dict[str, Any], path: str, default: Any = None) -> Any:
        """从嵌套字典中根据路径获取值

        Args:
            config_dict: 配置字典
            path: 路径，以点分隔，如 "connection.pool.min_size"
            default: 默认值

        Returns:
            Any: 配置值或默认值
        """
        if not path:
            return config_dict

        parts = path.split('.')
        current = config_dict

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def get_config_with_fallback(self, name: str, env: str, path: str, default: Any = None,
                                 fallback_env: str = "default") -> Any:
        """通过路径获取配置值，支持环境回退

        先尝试从指定环境中获取配置，如果不存在则从fallback环境中获取，
        最后如果都不存在则返回默认值。这对于有共享基础配置和环境特定配置的情况非常有用。

        Args:
            name: 配置段名称
            env: 当前环境名称
            path: 配置路径，不包含环境前缀
            default: 如果都不存在，返回的默认值
            fallback_env: 回退环境名称，默认为"default"

        Returns:
            Any: 配置值
        """
        # 构建完整路径
        env_path = f"{env}.{path}"

        # 先尝试从指定环境获取
        value = self.get_config_by_path(name, env_path, None)

        # 如果指定环境中不存在，则从fallback环境获取
        if value is None and fallback_env:
            fallback_path = f"{fallback_env}.{path}"
            value = self.get_config_by_path(name, fallback_path, default)
        elif value is None:
            value = default

        return value

    def register_yaml_config(self, namespace: str, file_paths: List[str], required: bool = False) -> None:
        """注册YAML配置

        Args:
            namespace: 配置命名空间
            file_paths: YAML文件路径列表
            required: 是否必须存在配置文件
        """
        from idp.framework.infrastructure.config.providers.yaml import YamlProvider

        yaml_provider = YamlProvider(namespace, file_paths, required)
        self.register_provider(namespace, yaml_provider)

    def register_json_config(self, namespace: str, file_paths: List[str], required: bool = False) -> None:
        """注册JSON配置

        Args:
            namespace: 配置命名空间
            file_paths: JSON文件路径列表
            required: 是否必须存在配置文件
        """
        from idp.framework.infrastructure.config.providers.json import JsonProvider

        json_provider = JsonProvider(namespace, file_paths, required)
        self.register_provider(namespace, json_provider)

    def print_registry_info(self) -> None:
        """打印配置注册表信息"""
        print("\n📋 [ConfigManager] 配置注册表信息:")

        # 打印所有配置段
        sections = self._registry.get_sections()
        print(f"📑 注册的配置段 ({len(sections)}):")
        for name in sections:
            section = self._registry.get_section(name)
            print(f"  - {name} (类型: {section.schema_class.__name__})")

        # 打印所有提供器
        providers = self._provider_registry.get_providers()
        print(f"🔌 注册的配置提供器 ({len(providers)}):")
        for provider in providers:
            print(
                f"  - {provider.__class__.__name__} (命名空间: {provider.get_namespace()})")

        print("")

    def merge_configs(self, namespace: str, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个配置字典到一个命名空间

        按照configs列表的顺序依次合并配置，后面的配置会覆盖前面的配置（当出现相同键时）

        Args:
            namespace: 目标命名空间
            configs: 配置字典列表，按优先级从低到高排序

        Returns:
            Dict[str, Any]: 合并后的配置字典

        Raises:
            ConfigurationError: 如果合并过程中出现错误
        """
        if not configs:
            print(f"⚠️ [ConfigManager] 没有提供任何配置进行合并")
            return {}

        try:
            # 从第一个配置开始
            merged_config = deepcopy(configs[0])

            # 依次合并后续配置
            for config in configs[1:]:
                DictUtils.deep_merge(merged_config, config)

            # 获取对应的配置段
            section = self._registry.get_section(namespace)
            if section:
                try:
                    # 更新配置段
                    section.update(merged_config)
                    print(f"✅ [ConfigManager] 成功合并配置到命名空间 '{namespace}'")
                except InvalidConfigurationError as e:
                    print(f"❌ [ConfigManager] 配置验证失败: {namespace}")
                    print(f"\n{'='*60}\n🚨 配置错误: {e}\n{'='*60}\n")
                    raise
            else:
                print(f"⚠️ [ConfigManager] 没有找到对应的配置段: {namespace}")

            return merged_config

        except Exception as e:
            error_msg = f"合并配置失败: {str(e)}"
            print(f"❌ [ConfigManager] {error_msg}")
            raise ConfigurationError(error_msg)

    def add_change_listener(
        self,
        namespace: str,
        listener: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """添加配置变更监听器

        Args:
            namespace: 配置命名空间
            listener: 配置变更回调函数
        """
        if namespace not in self._change_listeners:
            self._change_listeners[namespace] = []

        if listener is not None:
            self._change_listeners[namespace].append(listener)

    def remove_change_listener(
        self,
        namespace: str,
        listener: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """移除配置变更监听器

        Args:
            namespace: 配置命名空间
            listener: 配置变更回调函数
        """
        if namespace in self._change_listeners:
            self._change_listeners[namespace].remove(listener)

    def _notify_change_listeners(self, namespace: str, config: Dict[str, Any]) -> None:
        """通知配置变更监听器

        Args:
            namespace: 配置命名空间
            config: 新的配置
        """
        if namespace in self._change_listeners and self._change_listeners[namespace]:  # 确保命名空间存在且有监听器
            for listener in self._change_listeners[namespace]:
                try:
                    listener(config)
                except Exception as e:
                    logger.error(f"配置变更监听器执行失败: {str(e)}")

    def reload_namespace(self, namespace: str) -> Dict[str, Any]:
        """重新加载指定命名空间的配置

        Args:
            namespace: 配置命名空间

        Returns:
            Dict[str, Any]: 重新加载的配置

        Raises:
            ConfigurationError: 如果命名空间不存在
        """
        if namespace not in self._providers:
            raise ConfigurationError(f"命名空间不存在: {namespace}")

        # 清除缓存
        self._cached_configs.pop(namespace, None)

        # 重新加载配置
        providers = self._providers[namespace]
        return self.register_and_merge(namespace, providers[0].schema_class)

    def clear_cache(self) -> None:
        """清除所有配置缓存"""
        self._cached_configs.clear()

    def get_namespaces(self) -> List[str]:
        """获取所有已注册的命名空间

        Returns:
            List[str]: 命名空间列表
        """
        return list(self._providers.keys())

    # ---------------------------------------------------------------------
    # 内部工具方法
    # ---------------------------------------------------------------------
    # _merge_configs 处理 provider ➜ dict
    # merge_configs 处理 dicts ➜ section
    def _merge_configs(self, providers: List[ConfigProvider]) -> Dict[str, Any]:
        """合并多个配置提供器的配置数据。

        逻辑：
        1. 先合并各 provider 的 `default` 段。
        2. 再根据 env_name（取自 provider.env_name，如果没有默认为 "default"）合并对应环境段。

        Args:
            providers: 配置提供器列表

        Returns:
            Dict[str, Any]: 合并后的配置字典（扁平结构，不含 default / env 层级）。
        """
        merged: Dict[str, Any] = {}
        env_name: Optional[str] = None

        # 1️⃣ 合并 default 段
        for p in providers:
            data = p.load()
            env_name = getattr(p, "_env_name", None) or env_name or "default"
            default_cfg = data.get(
                "default", {}) if isinstance(data, dict) else {}
            DictUtils.deep_merge(merged, default_cfg)

        # 2️⃣ 合并环境特定段
        if env_name and env_name != "default":
            for p in providers:
                data = p.load()
                env_cfg = data.get(env_name, {}) if isinstance(
                    data, dict) else {}
                DictUtils.deep_merge(merged, env_cfg)

        return merged


# 创建全局配置管理器实例
config_manager = ConfigManager()

# 移除默认的框架配置提供器，由用户自行创建和注册提供器
