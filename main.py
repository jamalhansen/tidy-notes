from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from agents import Agent, Runner
import asyncio
import frontmatter

class FileData(BaseModel):
    text: str
    path: Path
    creation_date: datetime

def get_file(file_path: Path) -> FileData:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    stat_info = file_path.stat()
    if hasattr(stat_info, 'st_birthtime'):
        # macOS and some modern Unix systems have birth time
        creation_time = stat_info.st_birthtime
    else:
        # Fall back to st_ctime (metadata change time) on other systems
        creation_time = stat_info.st_ctime

    creation_date = datetime.fromtimestamp(creation_time)
    
    with file_path.open('r', encoding='utf-8') as file:
        text = file.read()
    
    return FileData(text=text, path=file_path, creation_date=creation_date)

def describe_text(text: str, title: str) -> str:
    instructions = "You describe obsidian notes to capture the essence of their purpose, focusing on the main points and return a succinct file description under 100 characters. You should never start the description with the words 'File Description:' or use markdown formatting.s " 
    prompt = f"Please describe the note titled '{title}' with the following content:\n\n{text[:2000]}"
    agent = Agent(name="Summarizer", instructions=instructions, model="gpt-4o-mini")

    result = asyncio.run(Runner.run(agent, prompt))

    return result.final_output

def summarize_text(text: str, title: str) -> str:
    instructions = "You summarize text in obsidian notes, focusing on the main points and return a summary under 100 characters. " 
    prompt = f"Please summarize the note titled '{title}' with the following content:\n\n{text[:2000]}"
    agent = Agent(name="Summarizer", instructions=instructions, model="gpt-4o-mini")

    result = asyncio.run(Runner.run(agent, prompt))

    return result.final_output

def create_title(file_data: FileData) -> str:
    title = file_data.path.stem.title().replace('_', ' ')
    return title

def process_post(file_data: FileData) -> frontmatter.Post:
    post = frontmatter.loads(file_data.text)
    
    # Add creation date if not present
    if not post.metadata.get('Created'):
        post.metadata['Created'] = file_data.creation_date.strftime('%Y-%m-%d')

    title = post.metadata.get('Title', None)
    if not title:
        title = create_title(file_data)
        post.metadata['Title'] = title

    # Ensure title is a string
    if not isinstance(title, str):
        title = str(title) if title is not None else ""

    # Add description if not present
    if not post.metadata.get('Description'):
        post.metadata['Description'] = describe_text(file_data.text, title)


    return post

def save_file(file_path: Path, post: frontmatter.Post) -> None:
    # Solution 1: Use dumps() to get string, then write as text
    content = frontmatter.dumps(post)
    with file_path.open('w', encoding='utf-8') as file:
        file.write(content)

def md_files(folder_path: str | Path):
    """Generator that yields all .md files in a given folder"""
    folder = Path(folder_path)
    
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    
    if not folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder}")
    
    for file_path in folder.glob("*.md"):
        yield file_path

def process_file(file:str | Path):
    """Process a single markdown file"""
    file = file if isinstance(file, Path) else Path(file)
    
    try:
        file_data = get_file(file)
        post = process_post(file_data)
        save_file(file, post)
        print(f"Successfully processed: {file}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def main():
    folder_to_process = "/Users/jamalhansen/vaults/BrainSync/2024 PyTexas"
    folder_path = Path(folder_to_process)
    for file in md_files(folder_path):
        process_file(file)

if __name__ == "__main__":
    main()