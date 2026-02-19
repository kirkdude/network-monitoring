#!/usr/bin/env python3
"""
InfluxDB Line Protocol Formatter
Converts collected data to InfluxDB line protocol format
"""

import time
from typing import Dict, Any, Optional


class InfluxDBFormatter:
    """Formats data as InfluxDB line protocol"""

    @staticmethod
    def format_line(measurement: str, tags: Dict[str, str], fields: Dict[str, Any],
                    timestamp: Optional[int] = None) -> str:
        """
        Format a single data point as InfluxDB line protocol

        Format: measurement,tag1=value1,tag2=value2 field1=value1,field2=value2 timestamp

        Args:
            measurement: Measurement name
            tags: Dictionary of tag key-value pairs
            fields: Dictionary of field key-value pairs
            timestamp: Optional Unix timestamp in nanoseconds (defaults to now)

        Returns:
            InfluxDB line protocol string
        """
        # Escape special characters in tags and measurements
        measurement = InfluxDBFormatter._escape_measurement(measurement)
        tag_str = ','.join([
            f"{InfluxDBFormatter._escape_tag_key(k)}={InfluxDBFormatter._escape_tag_value(v)}"
            for k, v in sorted(tags.items())
        ]) if tags else ''

        # Format fields
        field_parts = []
        for k, v in fields.items():
            field_key = InfluxDBFormatter._escape_field_key(k)
            field_value = InfluxDBFormatter._format_field_value(v)
            field_parts.append(f"{field_key}={field_value}")

        field_str = ','.join(field_parts)

        # Build line protocol string
        if tag_str:
            line = f"{measurement},{tag_str} {field_str}"
        else:
            line = f"{measurement} {field_str}"

        # Add timestamp if provided
        if timestamp:
            line += f" {timestamp}"
        else:
            # Default to current time in nanoseconds
            line += f" {int(time.time() * 1e9)}"

        return line

    @staticmethod
    def _escape_measurement(s: str) -> str:
        """Escape measurement name"""
        return s.replace(',', '\\,').replace(' ', '\\ ')

    @staticmethod
    def _escape_tag_key(s: str) -> str:
        """Escape tag key"""
        return s.replace(',', '\\,').replace('=', '\\=').replace(' ', '\\ ')

    @staticmethod
    def _escape_tag_value(s: str) -> str:
        """Escape tag value"""
        return str(s).replace(',', '\\,').replace('=', '\\=').replace(' ', '\\ ')

    @staticmethod
    def _escape_field_key(s: str) -> str:
        """Escape field key"""
        return s.replace(',', '\\,').replace('=', '\\=').replace(' ', '\\ ')

    @staticmethod
    def _format_field_value(v: Any) -> str:
        """
        Format field value according to type

        - Integers: append 'i' suffix
        - Floats: no suffix
        - Booleans: 't' or 'f'
        - Strings: wrap in quotes and escape
        """
        if isinstance(v, bool):
            return 't' if v else 'f'
        elif isinstance(v, int):
            return f"{v}i"
        elif isinstance(v, float):
            return str(v)
        elif isinstance(v, str):
            # Escape quotes and backslashes
            escaped = v.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        else:
            # Convert to string and treat as string
            escaped = str(v).replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
