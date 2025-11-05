"""Order status value object."""

from enum import Enum


class OrderStatus(str, Enum):
    """Order status enumeration.
    
    Represents the current state of an order in its lifecycle.
    """
    
    PENDING = "pending"
    """Order created but not paid"""
    
    PAID = "paid"
    """Order paid successfully"""
    
    CANCELLED = "cancelled"
    """Order cancelled"""
    
    SHIPPED = "shipped"
    """Order shipped to customer"""
    
    DELIVERED = "delivered"
    """Order delivered to customer"""
    
    REFUNDED = "refunded"
    """Order refunded"""
    
    def can_transition_to(self, new_status: "OrderStatus") -> bool:
        """Check if transition to new status is allowed.
        
        Args:
            new_status: Target status
            
        Returns:
            True if transition is allowed
            
        Example:
            ```python
            current = OrderStatus.PENDING
            can_pay = current.can_transition_to(OrderStatus.PAID)  # True
            can_ship = current.can_transition_to(OrderStatus.SHIPPED)  # False
            ```
        """
        # Define allowed transitions
        transitions = {
            OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
            OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.REFUNDED},
            OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
            OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
            OrderStatus.CANCELLED: set(),  # Terminal state
            OrderStatus.REFUNDED: set(),  # Terminal state
        }
        
        return new_status in transitions.get(self, set())

