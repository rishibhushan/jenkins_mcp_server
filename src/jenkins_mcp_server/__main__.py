"""
Main entry point for running the Jenkins MCP Server as a module.
"""
#!/usr/bin/env python3
from __future__ import annotations

# Import the package attribute `main` from the package (relative import)
from . import main

if __name__ == "__main__":
    # If main is a function, call it directly.
    main()
