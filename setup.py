from setuptools import setup, find_packages

setup(
    name="llm-dump-tool",
    version="1.0.0",
    description="A tool to dump various content sources into a single text file for LLM context",
    author="Adrian Obleton",
    author_email="obletonadrian@gmail.com",
    packages=find_packages(),
    py_modules=["llm_dump"],
    install_requires=[
        "pydantic",
        "pathspec"
    ],
    entry_points={
        "console_scripts": [
            "llm-dump=llm_dump:main"
        ]
    },
    python_requires=">=3.8",
)