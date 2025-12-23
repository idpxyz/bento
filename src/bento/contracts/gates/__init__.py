"""Contract Gates - Startup Validation.

Gates are startup-time validators that ensure contracts are properly loaded
and valid before the application starts serving requests.

Usage:
    ```python
    from bento.contracts.gates import ContractGate

    # In application startup
    gate = ContractGate(contracts_root="./contracts")
    gate.validate()  # Raises if contracts are invalid/missing
    ```
"""

from bento.contracts.gates.contract_gate import ContractGate

__all__ = ["ContractGate"]
