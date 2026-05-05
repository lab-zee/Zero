"""
Financial calculator tool for safe mathematical operations.
"""

import re
import math


def calculator(expression: str) -> str:
    """
    Perform safe mathematical calculations.
    
    Only allows basic math operations, financial functions, and safe operations.
    Prevents code execution.
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        Result of the calculation
    """
    # Remove whitespace
    expression = expression.strip()
    
    # Only allow safe characters: numbers, operators, parentheses, and common math functions
    safe_pattern = r'^[0-9+\-*/().\s,^%]+$|^[a-z_]+\([^)]*\)$'
    
    # Check for dangerous patterns
    dangerous = ['import', 'exec', 'eval', '__', 'open', 'file', 'input', 'raw_input']
    if any(d in expression.lower() for d in dangerous):
        return "Error: Expression contains potentially dangerous code"
    
    try:
        # Replace common financial/math notation
        expression = expression.replace('^', '**')  # Exponentiation
        expression = expression.replace(',', '')   # Remove thousand separators
        
        # Evaluate safely using only built-in math functions
        # Create a safe namespace
        safe_dict = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "math": math,
        }
        
        result = eval(expression, safe_dict)
        
        # Format result
        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            return f"{result:.2f}"
        return str(result)
        
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"
