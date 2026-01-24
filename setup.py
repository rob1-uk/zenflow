"""Setup configuration for ZenFlow CLI."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="zenflow",
    version="1.0.0",
    author="ZenFlow Contributors",
    description="A beautiful CLI productivity tool with task management, habit tracking, and gamification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dalonsogomez/zenflow",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "zenflow=zenflow.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "zenflow": ["py.typed"],
    },
)
