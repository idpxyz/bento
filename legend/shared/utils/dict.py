"""字典工具模块

提供字典操作的通用工具类和函数，包括深度合并、路径访问、扁平化等功能。
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast

T = TypeVar('T')


class DictUtils:
    """字典工具类
    
    提供字典操作的静态方法集合，包括：
    - 深度合并
    - 路径访问和设置
    - 字典扁平化
    - 字典比较
    - 路径转换
    """
    
    @staticmethod
    def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典
        
        将source字典中的内容合并到target字典中，如果有嵌套字典，则递归合并
        
        Args:
            target: 目标字典（会被修改）
            source: 源字典（保持不变）
            
        Returns:
            Dict[str, Any]: 合并后的字典（与target相同）
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                DictUtils.deep_merge(target[key], value)
            else:
                # 直接覆盖或添加
                target[key] = value
        return target

    @staticmethod
    def get_by_path(d: Dict[str, Any], path: str, default: Optional[T] = None, 
                    delimiter: str = '.') -> Optional[T]:
        """使用路径获取字典中的值
        
        Args:
            d: 目标字典
            path: 以分隔符分隔的路径，如 "a.b.c"
            default: 如果路径不存在，返回此默认值
            delimiter: 路径分隔符
            
        Returns:
            路径对应的值或默认值
            
        Examples:
            >>> d = {'a': {'b': {'c': 1}}}
            >>> DictUtils.get_by_path(d, 'a.b.c')
            1
            >>> DictUtils.get_by_path(d, 'x.y.z', default='not found')
            'not found'
        """
        if not path:
            return default
            
        current = d
        for part in path.split(delimiter):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    @staticmethod
    def set_by_path(d: Dict[str, Any], path: str, value: Any, 
                    delimiter: str = '.', create_missing: bool = True) -> None:
        """使用路径在字典中设置值
        
        Args:
            d: 目标字典
            path: 以分隔符分隔的路径，如 "a.b.c"
            value: 要设置的值
            delimiter: 路径分隔符
            create_missing: 是否创建不存在的中间节点
            
        Raises:
            KeyError: 如果路径中的某个部分不存在且create_missing为False
            TypeError: 如果路径中的某个部分存在但不是字典
            
        Examples:
            >>> d = {}
            >>> DictUtils.set_by_path(d, 'a.b.c', 1)
            >>> d
            {'a': {'b': {'c': 1}}}
        """
        if not path:
            return
            
        parts = path.split(delimiter)
        current = d
        
        # 处理中间节点
        for part in parts[:-1]:
            if create_missing:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
            elif part not in current:
                raise KeyError(f"路径不存在: {part}")
            elif not isinstance(current[part], dict):
                raise TypeError(f"路径 {part} 指向的不是字典")
            current = current[part]
            
        # 设置最终值
        current[parts[-1]] = value

    @staticmethod
    def flatten_dict(
        d: Dict[str, Any], 
        parent_key: str = '', 
        separator: str = '.'
    ) -> Dict[str, Any]:
        """将嵌套字典平铺为单层字典
        
        例如：{'a': {'b': 1}} -> {'a.b': 1}
        
        Args:
            d: 要平铺的字典
            parent_key: 父键前缀
            separator: 键层级分隔符
            
        Returns:
            Dict[str, Any]: 平铺后的字典
        """
        items: List[tuple] = []
        for key, value in d.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict):
                # 递归平铺
                items.extend(
                    DictUtils.flatten_dict(value, new_key, separator).items()
                )
            else:
                items.append((new_key, value))
        return dict(items)

    @staticmethod
    def unflatten(d: Dict[str, Any], delimiter: str = '.') -> Dict[str, Any]:
        """将扁平化的字典还原为嵌套字典
        
        Args:
            d: 扁平化的字典
            delimiter: 键名分隔符
            
        Returns:
            还原后的嵌套字典
            
        Examples:
            >>> d = {'a.b': 1, 'a.c.d': 2, 'e': 3}
            >>> DictUtils.unflatten(d)
            {'a': {'b': 1, 'c': {'d': 2}}, 'e': 3}
        """
        result = {}
        for key, value in d.items():
            DictUtils.set_by_path(result, key, value, delimiter)
        return result

    @staticmethod
    def compare(dict1: Dict[str, Any], dict2: Dict[str, Any], 
                flatten: bool = True) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
        """比较两个字典的差异
        
        Args:
            dict1: 第一个字典
            dict2: 第二个字典
            flatten: 是否扁平化后比较
            
        Returns:
            四元组 (added, removed, modified, same)，分别表示：
            - added: 在dict2中新增的键
            - removed: 从dict1中删除的键
            - modified: 值被修改的键
            - same: 值相同的键
            
        Examples:
            >>> d1 = {'a': 1, 'b': 2}
            >>> d2 = {'b': 3, 'c': 4}
            >>> added, removed, modified, same = DictUtils.compare(d1, d2)
            >>> added
            {'c'}
            >>> removed
            {'a'}
            >>> modified
            {'b'}
            >>> same
            set()
        """
        # 如果需要扁平化处理
        if flatten:
            flat_dict1 = DictUtils.flatten_dict(dict1)
            flat_dict2 = DictUtils.flatten_dict(dict2)
        else:
            flat_dict1 = dict1
            flat_dict2 = dict2
        
        # 获取所有键
        keys1 = set(flat_dict1.keys())
        keys2 = set(flat_dict2.keys())
        
        # 分类变化
        added = keys2 - keys1
        removed = keys1 - keys2
        common_keys = keys1 & keys2
        
        # 进一步分类修改和相同的键
        modified = {k for k in common_keys if flat_dict1[k] != flat_dict2[k]}
        same = common_keys - modified
        
        return added, removed, modified, same

    @staticmethod
    def find_differences(dict1: Dict[str, Any], dict2: Dict[str, Any], 
                        path: str = '') -> List[Tuple[str, Any, Any]]:
        """查找两个字典的具体差异
        
        Args:
            dict1: 第一个字典
            dict2: 第二个字典
            path: 当前路径前缀
            
        Returns:
            差异列表，每项为 (路径, dict1中的值, dict2中的值)
            
        Examples:
            >>> d1 = {'a': {'b': 1}, 'c': 2}
            >>> d2 = {'a': {'b': 3}, 'd': 4}
            >>> DictUtils.find_differences(d1, d2)
            [('a.b', 1, 3), ('c', 2, None), ('d', None, 4)]
        """
        differences = []
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            
            # 处理键只存在于一个字典的情况
            if key not in dict1:
                differences.append((current_path, None, dict2[key]))
                continue
            if key not in dict2:
                differences.append((current_path, dict1[key], None))
                continue
                
            # 两个字典都有这个键
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                nested_diffs = DictUtils.find_differences(dict1[key], dict2[key], current_path)
                differences.extend(nested_diffs)
            elif dict1[key] != dict2[key]:
                differences.append((current_path, dict1[key], dict2[key]))
        
        return differences

    @staticmethod
    def get_paths(d: Dict[str, Any], parent_path: str = '', 
                  include_values: bool = False) -> Union[List[str], Dict[str, Any]]:
        """获取字典中所有路径
        
        Args:
            d: 目标字典
            parent_path: 父路径前缀
            include_values: 是否包含值
            
        Returns:
            如果include_values为True，返回路径到值的映射字典
            否则返回路径列表
            
        Examples:
            >>> d = {'a': {'b': 1, 'c': 2}, 'd': 3}
            >>> DictUtils.get_paths(d)
            ['a.b', 'a.c', 'd']
            >>> DictUtils.get_paths(d, include_values=True)
            {'a.b': 1, 'a.c': 2, 'd': 3}
        """
        result = {} if include_values else []
        
        for key, value in d.items():
            current_path = f"{parent_path}.{key}" if parent_path else key
            
            if isinstance(value, dict):
                sub_result = DictUtils.get_paths(value, current_path, include_values)
                if include_values:
                    result.update(sub_result)
                else:
                    result.extend(sub_result)
            else:
                if include_values:
                    result[current_path] = value
                else:
                    result.append(current_path)
        
        return result

    @staticmethod
    def filter_keys(
        d: Dict[str, Any], 
        keys: Set[str],
        include: bool = True
    ) -> Dict[str, Any]:
        """根据键集合筛选字典
        
        Args:
            d: 要筛选的字典
            keys: 键集合
            include: True表示只保留keys中的键，False表示排除keys中的键
            
        Returns:
            Dict[str, Any]: 筛选后的新字典
        """
        if include:
            # 只保留keys中的键
            return {k: v for k, v in d.items() if k in keys}
        else:
            # 排除keys中的键
            return {k: v for k, v in d.items() if k not in keys}

    @staticmethod
    def transform_keys(d: Dict[str, Any], transform_func: callable, 
                      recursive: bool = True) -> Dict[str, Any]:
        """转换字典的键
        
        Args:
            d: 要转换的字典
            transform_func: 键转换函数
            recursive: 是否递归转换嵌套字典
            
        Returns:
            转换后的字典
            
        Examples:
            >>> d = {'a': {'b': 1}, 'c': 2}
            >>> DictUtils.transform_keys(d, str.upper)
            {'A': {'B': 1}, 'C': 2}
        """
        result = {}
        for key, value in d.items():
            new_key = transform_func(key)
            if recursive and isinstance(value, dict):
                result[new_key] = DictUtils.transform_keys(value, transform_func)
            else:
                result[new_key] = value
        return result

    @staticmethod
    def get_nested(
        d: Dict[str, Any], 
        path: str, 
        separator: str = '.', 
        default: Any = None
    ) -> Any:
        """获取嵌套字典中的值
        
        例如：get_nested({'a': {'b': 1}}, 'a.b') -> 1
        
        Args:
            d: 嵌套字典
            path: 键路径，用separator分隔
            separator: 路径分隔符
            default: 如果路径不存在，返回的默认值
            
        Returns:
            Any: 找到的值，或default
        """
        keys = path.split(separator)
        current = d
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
            
        return current
    
    @staticmethod
    def set_nested(
        d: Dict[str, Any], 
        path: str, 
        value: Any, 
        separator: str = '.',
        create_path: bool = True
    ) -> Dict[str, Any]:
        """在嵌套字典中设置值
        
        例如：set_nested({'a': {}}, 'a.b', 1) -> {'a': {'b': 1}}
        
        Args:
            d: 要修改的字典
            path: 键路径，用separator分隔
            value: 要设置的值
            separator: 路径分隔符
            create_path: 如果路径不存在，是否创建
            
        Returns:
            Dict[str, Any]: 修改后的字典
            
        Raises:
            KeyError: 如果路径不存在且create_path=False
        """
        keys = path.split(separator)
        current = d
        
        # 遍历到倒数第二层
        for i, key in enumerate(keys[:-1]):
            if key not in current:
                if not create_path:
                    raise KeyError(f"路径不存在: {separator.join(keys[:i+1])}")
                current[key] = {}
            elif not isinstance(current[key], dict):
                if not create_path:
                    raise KeyError(f"路径中的键不是字典: {separator.join(keys[:i+1])}")
                # 将非字典值转换为字典
                current[key] = {}
            
            current = current[key]
            
        # 设置最后一层的值
        current[keys[-1]] = value
        return d
