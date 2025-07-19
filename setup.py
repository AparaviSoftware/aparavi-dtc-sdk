"""
Setup configuration for aparavi-dtc-sdk
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aparavi-dtc-sdk",
    version="0.1.0",
    author="Aparavi",
    author_email="your.email@example.com",
    description="Python SDK for Aparavi Data Toolchain API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/aparavi-dtc-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.991",
        ],
    },
    keywords="aparavi api sdk web services",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/aparavi-dtc-sdk/issues",
        "Source": "https://github.com/yourusername/aparavi-dtc-sdk",
    },
)

