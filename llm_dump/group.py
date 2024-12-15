import click
from llm_dump import __version__

@click.group()
@click.version_option(version=__version__, prog_name="llm-dump")
def cli():
    """Process various content sources for LLM context."""
    pass 