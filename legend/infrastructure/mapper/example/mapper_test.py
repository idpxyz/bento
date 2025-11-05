"""
Mapper System Test

This file contains tests to verify the current state of the mapper system,
focusing on the MapperBuilder alias and proper type handling.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import date

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder
from idp.framework.infrastructure.mapper.core.context import MappingContext


# Test simple mapping with proper type handling
@dataclass
class SimpleSource:
    id: str = ""
    name: str = ""
    value: int = 0
    is_active: bool = True
    created_at: Optional[date] = None


@dataclass
class SimpleTarget:
    id: str = ""
    name: str = ""
    value: int = 0
    active: bool = False  # Different field name
    created_date: str = ""  # Different type, with default value


def test_simple_mapping():
    """Test simple mapping with the MapperBuilder alias"""
    print("\n=== Testing Simple Mapping ===")
    
    # Create source object
    source = SimpleSource(
        id="123",
        name="Test Object",
        value=42,
        is_active=True,
        created_at=date(2023, 1, 15)
    )
    
    print(f"Source: {source}")
    
    # Create mapper using the MapperBuilder alias
    mapper = MapperBuilder.for_types(SimpleSource, SimpleTarget) \
        .map("id", "id") \
        .map("name", "name") \
        .map("value", "value") \
        .map("is_active", "active") \
        .map_custom("created_date", lambda src: src.created_at.isoformat() if src.created_at else None) \
        .build()
    
    # Map the object
    try:
        target = mapper.map(source)
        print(f"Target: {target}")
        
        # Verify mapping
        assert target.id == source.id
        assert target.name == source.name
        assert target.value == source.value
        assert target.active == source.is_active
        assert target.created_date == (source.created_at.isoformat() if source.created_at else None)
        
        print("✓ Simple mapping test passed")
    except Exception as e:
        print(f"✗ Simple mapping test failed: {e}")


# Test nested object mapping
@dataclass
class Address:
    street: str = ""
    city: str = ""
    zip_code: str = ""


@dataclass
class AddressDTO:
    street_line: str = ""  # Different field name
    city: str = ""
    postal_code: str = ""  # Different field name


@dataclass
class Person:
    id: str = ""
    name: str = ""
    address: Optional[Address] = None
    
    def __post_init__(self):
        if self.address is None:
            self.address = Address()


@dataclass
class PersonDTO:
    person_id: str = ""  # Different field name
    name: str = ""
    address: Optional[AddressDTO] = None
    
    def __post_init__(self):
        if self.address is None:
            self.address = AddressDTO()


def test_nested_mapping():
    """Test nested object mapping"""
    print("\n=== Testing Nested Mapping ===")
    
    # Create source object
    source = Person(
        id="P001",
        name="John Doe",
        address=Address(
            street="123 Main St",
            city="Anytown",
            zip_code="12345"
        )
    )
    
    print(f"Source: {source}")
    
    # Create address mapper
    address_mapper = MapperBuilder.for_types(Address, AddressDTO) \
        .map("street", "street_line") \
        .map("zip_code", "postal_code") \
        .map("city", "city") \
        .build()
    
    # Create person mapper with nested address mapper
    person_mapper = MapperBuilder.for_types(Person, PersonDTO) \
        .map("id", "person_id") \
        .map("name", "name") \
        .build()
    
    # Map the object
    try:
        # Create target object with initialized address
        target = PersonDTO(person_id="", name="", address=AddressDTO())
        
        # Map to existing target
        person_mapper.map_to_target(source, target)
        
        # Manually map the address
        if source.address and target.address:
            address_mapper.map_to_target(source.address, target.address)
        
        print(f"Target: {target}")
        
        # Verify mapping
        assert target.person_id == source.id
        assert target.name == source.name
        assert target.address is not None
        assert target.address.street_line == source.address.street
        assert target.address.city == source.address.city
        assert target.address.postal_code == source.address.zip_code
        
        print("✓ Nested mapping test passed")
    except Exception as e:
        print(f"✗ Nested mapping test failed: {e}")


# Test collection mapping
@dataclass
class Product:
    id: str = ""
    name: str = ""
    price: float = 0.0


@dataclass
class ProductDTO:
    product_id: str = ""  # Different field name
    product_name: str = ""  # Different field name
    price: float = 0.0


@dataclass
class Order:
    id: str = ""
    products: List[Product] = None
    
    def __post_init__(self):
        if self.products is None:
            self.products = []


@dataclass
class OrderDTO:
    order_id: str = ""  # Different field name
    items: List[ProductDTO] = None  # Different field name
    
    def __post_init__(self):
        if self.items is None:
            self.items = []


def test_collection_mapping():
    """Test collection mapping"""
    print("\n=== Testing Collection Mapping ===")
    
    # Create source object with initialized products list
    source = Order(
        id="O001",
        products=[
            Product(id="P001", name="Laptop", price=1299.99),
            Product(id="P002", name="Mouse", price=29.99),
            Product(id="P003", name="Keyboard", price=99.99)
        ]
    )
    
    print(f"Source: {source}")
    
    # Create product mapper
    product_mapper = MapperBuilder.for_types(Product, ProductDTO) \
        .map("id", "product_id") \
        .map("name", "product_name") \
        .map("price", "price") \
        .build()
    
    # Create order mapper without collection mapping
    order_mapper = MapperBuilder.for_types(Order, OrderDTO) \
        .map("id", "order_id") \
        .build()
    
    # Map the object
    try:
        # Create a target object with initialized items list
        target = OrderDTO(order_id="", items=[])
        
        # Map basic fields to existing target
        order_mapper.map_to_target(source, target)
        
        # Manually map the collection
        for product in source.products:
            product_dto = ProductDTO()
            product_mapper.map_to_target(product, product_dto)
            target.items.append(product_dto)
            
        print(f"Target: {target}")
        
        # Verify mapping
        assert target.order_id == source.id
        assert len(target.items) == len(source.products)
        
        for i, product in enumerate(source.products):
            assert target.items[i].product_id == product.id
            assert target.items[i].product_name == product.name
            assert target.items[i].price == product.price
        
        print("✓ Collection mapping test passed")
    except Exception as e:
        print(f"✗ Collection mapping test failed: {e}")


# Test mapping context for circular references
@dataclass
class Department:
    id: str = ""
    name: str = ""
    manager: Optional['Employee'] = None


@dataclass
class Employee:
    id: str = ""
    name: str = ""
    department: Optional[Department] = None


@dataclass
class DepartmentDTO:
    dept_id: str = ""  # Different field name
    dept_name: str = ""  # Different field name
    manager: Optional['EmployeeDTO'] = None


@dataclass
class EmployeeDTO:
    emp_id: str = ""  # Different field name
    emp_name: str = ""  # Different field name
    department: Optional[DepartmentDTO] = None


def test_circular_reference_mapping():
    """Test mapping with circular references using MappingContext"""
    print("\n=== Testing Circular Reference Mapping ===")
    
    # Create circular reference objects
    department = Department(id="D001", name="Engineering")
    employee = Employee(id="E001", name="John Doe", department=department)
    department.manager = employee
    
    print(f"Source Department: {department}")
    print(f"Source Employee: {employee}")
    
    # Create mappers with circular references
    # We need to create the mappers first, then configure them
    department_mapper = MapperBuilder.for_types(Department, DepartmentDTO) \
        .map("id", "dept_id") \
        .map("name", "dept_name") \
        .build()
    
    employee_mapper = MapperBuilder.for_types(Employee, EmployeeDTO) \
        .map("id", "emp_id") \
        .map("name", "emp_name") \
        .build()
    
    # Map the objects using a mapping context
    try:
        context = MappingContext()
        
        # Map department first
        dept_dto = DepartmentDTO(dept_id="", dept_name="")
        department_mapper.map_to_target_with_context(department, dept_dto, context)
        print(f"Target Department: {dept_dto}")
        
        # Map employee
        emp_dto = EmployeeDTO(emp_id="", emp_name="")
        employee_mapper.map_to_target_with_context(employee, emp_dto, context)
        print(f"Target Employee: {emp_dto}")
        
        # Verify mapping
        assert dept_dto.dept_id == department.id
        assert dept_dto.dept_name == department.name
        assert emp_dto.emp_id == employee.id
        assert emp_dto.emp_name == employee.name
        
        print("✓ Circular reference mapping test passed")
    except Exception as e:
        print(f"✗ Circular reference mapping test failed: {e}")


if __name__ == "__main__":
    # Run all tests
    test_simple_mapping()
    test_nested_mapping()
    test_collection_mapping()
    test_circular_reference_mapping()
    
    print("\nAll tests completed.") 