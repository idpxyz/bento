"""Snowflake ID Generator

This module implements Twitter's Snowflake ID generation algorithm.
Each ID is composed of:
- 41 bits for timestamp in milliseconds
- 5 bits for datacenter ID
- 5 bits for worker ID
- 12 bits for sequence number

Reference: https://github.com/twitter-archive/snowflake
"""
import time, threading
from datetime import datetime
from typing import Dict, Tuple


class Flake:
    """Snowflake ID generator that generates unique 64-bit IDs."""
    
    def __init__(self, worker_id: int, datacenter_id: int) -> None:
        """Initialize the Snowflake generator.
        
        Args:
            worker_id: Worker ID (0-31)
            datacenter_id: Datacenter ID (0-31)
            
        Raises:
            ValueError: If worker_id or datacenter_id is out of valid range
        """
        if not 0 <= worker_id <= 31:
            raise ValueError("worker_id must be between 0 and 31")
        if not 0 <= datacenter_id <= 31:
            raise ValueError("datacenter_id must be between 0 and 31")
            
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        
        # Bit masks
        self.datacenter_id_mask = 31
        self.worker_id_mask = 31
        self.sequence_mask = 4095
        
        # Other properties
        self.sequence = 0
        self.last_timestamp = -1
        self.twepoch = 1288834974657  # Custom epoch (2010-11-04 01:42:54.657)
        
        # Bit shifts
        self.timestamp_left_shift = 22
        self.datacenter_id_shift = 17
        self.worker_id_shift = 12

    def _time_gen(self) -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)
    
    def _wait_next_millis(self, last_timestamp: int) -> int:
        """Wait until next millisecond.
        
        Args:
            last_timestamp: The last timestamp used
            
        Returns:
            New current timestamp in milliseconds
        """
        timestamp = self._time_gen()
        while timestamp <= last_timestamp:
            timestamp = self._time_gen()
        return timestamp

    def generate(self) -> Tuple[int, datetime]:
        """Generate a new unique ID.
        
        Returns:
            A tuple containing:
            - A 64-bit unique ID
            - The datetime object representing when the ID was generated
            
        Raises:
            Exception: If clock moves backwards
        """
        timestamp = self._time_gen()
        
        if timestamp < self.last_timestamp:
            raise Exception(
                f"Clock moved backwards. Refusing to generate id for "
                f"{self.last_timestamp - timestamp} milliseconds"
            )

        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            if self.sequence == 0:
                timestamp = self._wait_next_millis(self.last_timestamp)
        else:
            self.sequence = 0

        self.last_timestamp = timestamp
        
        snowflake_id = (
            ((timestamp - self.twepoch) << self.timestamp_left_shift) |
            (self.datacenter_id << self.datacenter_id_shift) |
            (self.worker_id << self.worker_id_shift) |
            self.sequence
        )
        
        # Convert timestamp to datetime
        dt = datetime.fromtimestamp(timestamp / 1000)
        
        return snowflake_id, dt
    
    def parse(self, id: int) -> Dict[str, int | datetime]:
        """Parse a Snowflake ID into its components.
        
        Args:
            id: The Snowflake ID to parse
            
        Returns:
            Dictionary containing timestamp (as datetime), datacenter_id, worker_id and sequence
        """
        timestamp_ms = (id >> self.timestamp_left_shift) + self.twepoch
        return {
            "timestamp": datetime.fromtimestamp(timestamp_ms / 1000),
            "timestamp_ms": timestamp_ms,
            "datacenter_id": (id >> self.datacenter_id_shift) & self.datacenter_id_mask,
            "worker_id": (id >> self.worker_id_shift) & self.worker_id_mask,
            "sequence": id & self.sequence_mask
        }

def test_flake() -> None:
    """Test the Snowflake ID generator."""
    # Test normal operation
    flake = Flake(1, 1)
    
    # Generate two sequential IDs
    id1, dt1 = flake.generate()
    id2, dt2 = flake.generate()
    
    # Test sequential generation
    assert id1 < id2, "Sequential IDs should be monotonically increasing"
    assert dt1 <= dt2, "Sequential timestamps should be monotonically increasing"
    
    # Test ID parsing
    components = flake.parse(id1)
    assert 0 <= components["worker_id"] <= 31, "Worker ID should be between 0 and 31"
    assert 0 <= components["datacenter_id"] <= 31, "Datacenter ID should be between 0 and 31"
    assert 0 <= components["sequence"] <= 4095, "Sequence should be between 0 and 4095"
    
    # Verify timestamp consistency
    time_diff_ms = abs((components["timestamp"] - dt1).total_seconds() * 1000)
    assert time_diff_ms < 2, "Generated and parsed timestamps should match within 1ms"
    
    print(f"Generated ID: {id1}")
    print(f"Generation time: {dt1.isoformat()}")
    print(f"Parsed components: {components}")
    print(f"Time difference: {time_diff_ms}ms")

if __name__ == "__main__":
    test_flake()