from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="python-pgsql-parser",
    version="0.1.0",
    author="Sunny Liu",
    author_email="sunnyliu2@gmail.com",
    description="WukongStack is a dynamic CLI tool that generates a full-stack web application skeleton",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/devsunny/wukong-stack",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",       
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: web application",
        "Topic :: developer tools",
    ],
    python_requires=">=3.7",
    keywords="sql parser postgresql ddl metadata schema analysis",
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0", "twine>=4.0", "coverage>=6.0"],
    },
    project_urls={
        "Documentation": "https://github.com/devsunny/wukong-stack/README.md",
        "Source": "https://github.com/devsunny/wukong-stack",
        "Tracker": "https://github.com/devsunny/wukong-stack",
    },
)