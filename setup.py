#!/usr/bin/env python3
import os

from setuptools import find_packages, setup


def exec_file(path_segments):
    """Execute a single python file to get the variables defined in it"""
    result = {}
    code = read_file(path_segments)
    exec(code, result)
    return result


def read_file(path_segments):
    """Read a file from the package. Takes a list of strings to join to
    make the path"""
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), *path_segments)
    with open(file_path) as f:
        return f.read()


version = exec_file(("drawing_challenge_bot", "__init__.py"))["__version__"]
long_description = read_file(("README.md",))


setup(
    name="drawing-challenge-bot",
    version=version,
    url="https://github.com/anoadragon453/drawing-challenge-bot",
    description="A matrix bot to help you improve your art",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "matrix-nio[e2e]>=0.10.0",
        "Markdown>=3.1.1",
        "PyYAML>=5.1.2",
        "apscheduler>=3.6.3",
        "praw>=7.0.0",
    ],
    extras_require={
        "postgres": ["psycopg2>=2.8.5"],
        "dev": ["isort==4.3.21", "flake8==3.8.3", "black==19.10b0"],
    },
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    long_description=long_description,
    # Allow the user to run the bot with `drawing-challenge-bot ...`
    scripts=["drawing-challenge-bot"],
)
