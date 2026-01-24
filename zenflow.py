#!/usr/bin/env python3
"""Entry point script for ZenFlow CLI application.

This script serves as the main entry point for running ZenFlow from the command line.
It imports and executes the Click CLI group defined in zenflow.cli.
"""

from zenflow.cli import main

if __name__ == "__main__":
    main()
