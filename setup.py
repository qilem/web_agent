from setuptools import setup, find_packages
from pathlib import Path

requirements_path = Path(__file__).parent / "requirements.txt"
with open(requirements_path, 'r') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="waa",
    version="0.1.0",
    description="Web-App Agent - An LLM-powered agent for building web applications",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "waa=waa.cli:main",
        ],
    },
)
