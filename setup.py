from setuptools import setup, find_packages

setup(
    name="llm-dump",
    version="0.3.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "pydantic",
        "pathspec",
    ],
    entry_points={
        "console_scripts": [
            "llm-dump=llm_dump.cli:cli",
        ],
    },
)