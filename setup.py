#!/usr/bin/env python3
"""
tt-cli: Unified command-line interface for Tenstorrent development
Built on tt-jukebox foundations, eliminating throwaway scripts.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else __doc__

setup(
    name='tt-cli',
    version='0.1.0',
    description='Unified CLI for Tenstorrent hardware development',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Tenstorrent',
    url='https://github.com/tenstorrent/tt-cli',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        # Zero core dependencies - stdlib only!
    ],
    extras_require={
        'tui': [
            'textual>=0.47.0',
            'rich>=13.7.0',
        ],
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'ruff>=0.1.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'tt=tt.core.cli:main',
            'tt-tui=tt.tui.app:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
