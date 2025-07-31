"""
Setup configuration for aparavi-dtc-sdk
"""

import os
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


requirements = []
req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(req_path):
    with open(req_path, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aparavi-dtc-sdk",
    version="1.0.0",
    author="Aparavi",
    author_email="support@aparavi.com",
    description="Python SDK for Aparavi Data Toolchain API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://dtc-dev.aparavi.com",
    packages=find_packages(),
    package_data={"aparavi_dtc_sdk": ["pipelines/*.json"]},
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
    keywords="aparavi dtc data toolchain api sdk web services",
    project_urls={
        "Bug Reports": "https://github.com/AparaviSoftware/aparavi-dtc-sdk/issues",
        "Source": "https://github.com/AparaviSoftware/aparavi-dtc-sdk",
    },
)

