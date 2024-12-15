from pydantic import BaseModel, DirectoryPath, FilePath
from typing import Optional

class FileContent(BaseModel):
    file_path: FilePath
    content: str

class FolderTraversalInput(BaseModel):
    folder_path: DirectoryPath
    output_file: str

class ObsidianTraversalInput(BaseModel):
    start_file: str
    output_file: str
    max_depth: int = 2
    base_folder: Optional[DirectoryPath] = None