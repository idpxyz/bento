"""循环引用映射示例

本示例演示如何使用映射器处理循环引用的对象。
"""

from dataclasses import dataclass, field
from typing import List, Optional

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder
from idp.framework.infrastructure.mapper.registry.base import MapperRegistryImpl


# 源对象类
@dataclass
class DepartmentEntity:
    """部门实体"""
    id: int
    name: str
    employees: List['EmployeeEntity'] = field(default_factory=list)


@dataclass
class EmployeeEntity:
    """员工实体"""
    id: int
    name: str
    department: Optional[DepartmentEntity] = None


# 目标对象类
@dataclass
class DepartmentDTO:
    """部门DTO"""
    id: int = 0
    name: str = ""
    employees: List['EmployeeDTO'] = field(default_factory=list)


@dataclass
class EmployeeDTO:
    """员工DTO"""
    id: int = 0
    name: str = ""
    department: Optional[DepartmentDTO] = None


def circular_reference_mapping_example():
    """循环引用映射示例"""
    print("\n===== 循环引用映射示例 =====")
    
    try:
        # 创建源对象
        department = DepartmentEntity(id=1, name="Engineering")
        employee1 = EmployeeEntity(id=101, name="Alice")
        employee2 = EmployeeEntity(id=102, name="Bob")
        
        # 建立循环引用关系
        department.employees = [employee1, employee2]
        employee1.department = department
        employee2.department = department
        
        print(f"源对象: 部门 {department.name} 有 {len(department.employees)} 名员工")
        print(f"员工 {employee1.name} 属于部门 {employee1.department.name}")
        
        # 创建映射器注册表
        mapper_registry = MapperRegistryImpl()
        
        # 创建部门到部门DTO的映射器
        department_mapper_builder = MapperBuilder.for_types(DepartmentEntity, DepartmentDTO)
        department_mapper_builder.map("id", "id")
        department_mapper_builder.map("name", "name")
        
        # 创建员工到员工DTO的映射器
        employee_mapper_builder = MapperBuilder.for_types(EmployeeEntity, EmployeeDTO)
        employee_mapper_builder.map("id", "id")
        employee_mapper_builder.map("name", "name")
        
        # 构建映射器
        department_mapper = department_mapper_builder.build()
        employee_mapper = employee_mapper_builder.build()
        
        # 注册映射器到全局映射器注册表
        mapper_registry.register(DepartmentEntity, DepartmentDTO, department_mapper)
        mapper_registry.register(EmployeeEntity, EmployeeDTO, employee_mapper)
        
        # 手动执行映射
        department_dto = DepartmentDTO(id=department.id, name=department.name, employees=[])
        
        # 映射员工
        for employee in department.employees:
            employee_dto = EmployeeDTO(id=employee.id, name=employee.name, department=department_dto)
            department_dto.employees.append(employee_dto)
        
        print("映射后的对象:")
        print(f"目标对象: 部门 '{department_dto.name}' 有 {len(department_dto.employees)} 名员工")
        
        # 确保员工已正确映射
        if department_dto.employees and len(department_dto.employees) > 0:
            print(f"员工1: {department_dto.employees[0].name}, 所属部门: {department_dto.employees[0].department.name}")
            if len(department_dto.employees) > 1:
                print(f"员工2: {department_dto.employees[1].name}, 所属部门: {department_dto.employees[1].department.name}")
        
        # 验证循环引用是否正确处理
        print("\n验证循环引用处理:")
        print(f"部门对象 -> 员工1 -> 部门对象 是否为同一对象: {department_dto is department_dto.employees[0].department}")
        print(f"部门对象 -> 员工2 -> 部门对象 是否为同一对象: {department_dto is department_dto.employees[1].department}")
        
        # 不使用上下文的情况（会导致无限递归）
        try:
            print("\n尝试不使用上下文映射（会导致无限递归）:")
            # 注释掉以下代码以避免实际运行时的无限递归
            # department_dto_no_context = department_mapper.map(department)
            print("如果不使用映射上下文，将导致无限递归错误")
        except Exception as e:
            print(f"发生错误: {str(e)}")
        
        print("\n===== 循环引用映射示例结束 =====")
    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    circular_reference_mapping_example() 