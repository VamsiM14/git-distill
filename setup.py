from setuptools import setup, find_packages

setup(
    name="git-distill",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "git-distill=git_distill.cli:app",
            "gitdistill=git_distill.cli:app",
        ],
    },
)
