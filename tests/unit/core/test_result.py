"""Unit tests for Result type."""

import pytest

from bento.core.result import Err, Ok, Result


class TestResult:
    """Test suite for Result type."""

    def test_ok_result_creation(self):
        """Test creating an Ok result."""
        result = Ok(42)

        assert result.is_ok
        assert not result.is_err
        assert result.unwrap() == 42

    def test_err_result_creation(self):
        """Test creating an Err result."""
        result = Err("Error message")

        assert result.is_err
        assert not result.is_ok
        assert result.unwrap_err() == "Error message"

    def test_ok_unwrap(self):
        """Test unwrapping Ok result."""
        result = Ok("success")

        value = result.unwrap()
        assert value == "success"

    def test_err_unwrap_raises(self):
        """Test that unwrapping Err result raises an error."""
        result = Err("failure")

        with pytest.raises(RuntimeError, match="Unwrap error: failure"):
            result.unwrap()

    def test_ok_unwrap_err_raises(self):
        """Test that unwrap_err on Ok result raises an error."""
        result = Ok("success")

        with pytest.raises(RuntimeError, match="Tried to unwrap_err on Ok"):
            result.unwrap_err()

    def test_err_unwrap_err(self):
        """Test unwrapping error from Err result."""
        result = Err("error details")

        error = result.unwrap_err()
        assert error == "error details"

    def test_result_with_complex_ok_value(self):
        """Test Result with complex Ok value."""
        data = {"key": "value", "number": 123}
        result = Ok(data)

        assert result.is_ok
        assert result.unwrap() == data
        assert result.unwrap()["key"] == "value"

    def test_result_with_complex_err_value(self):
        """Test Result with complex Err value."""
        error = {"code": "ERR_001", "message": "Something went wrong"}
        result = Err(error)

        assert result.is_err
        assert result.unwrap_err() == error
        assert result.unwrap_err()["code"] == "ERR_001"

    def test_result_with_none_ok_value(self):
        """Test Result with None as Ok value."""
        result = Ok(None)

        assert result.is_ok
        assert result.unwrap() is None

    def test_result_with_none_err_value(self):
        """Test that Err with None might not work as expected."""
        # Note: This test documents current behavior
        # Err(None) would create a Result where _err is None, making it look like Ok
        result = Result(err=None)

        # This is a quirky behavior - it's technically "Ok" because err is None
        assert result.is_ok
        assert not result.is_err

    def test_result_type_annotations(self):
        """Test Result with different type annotations."""
        # String result
        str_result: Result[str, str] = Ok("hello")
        assert str_result.unwrap() == "hello"

        # Integer result
        int_result: Result[int, str] = Ok(42)
        assert int_result.unwrap() == 42

        # Error result
        err_result: Result[int, str] = Err("error")
        assert err_result.unwrap_err() == "error"

    def test_result_chain_behavior(self):
        """Test using Result in a chain of operations."""

        def divide(a: int, b: int) -> Result[float, str]:
            if b == 0:
                return Err("Division by zero")
            return Ok(a / b)

        result1 = divide(10, 2)
        assert result1.is_ok
        assert result1.unwrap() == 5.0

        result2 = divide(10, 0)
        assert result2.is_err
        assert result2.unwrap_err() == "Division by zero"

    def test_result_as_return_value(self):
        """Test using Result as function return value."""

        def validate_age(age: int) -> Result[int, str]:
            if age < 0:
                return Err("Age cannot be negative")
            if age > 150:
                return Err("Age too high")
            return Ok(age)

        assert validate_age(25).is_ok
        assert validate_age(25).unwrap() == 25

        assert validate_age(-5).is_err
        assert validate_age(-5).unwrap_err() == "Age cannot be negative"

        assert validate_age(200).is_err
        assert validate_age(200).unwrap_err() == "Age too high"

    def test_result_with_exception_as_error(self):
        """Test Result with Exception as error type."""
        exception = ValueError("Invalid value")
        result = Err(exception)

        assert result.is_err
        error = result.unwrap_err()
        assert isinstance(error, ValueError)
        assert str(error) == "Invalid value"

    def test_result_boolean_evaluation(self):
        """Test using Result in boolean context."""
        ok_result = Ok(42)
        err_result = Err("error")

        # Results themselves are truthy (they're objects)
        assert ok_result
        assert err_result

        # But their state can be checked
        assert ok_result.is_ok
        assert err_result.is_err
