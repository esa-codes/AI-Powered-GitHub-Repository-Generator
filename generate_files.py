import os
import re
from datetime import datetime
import json
from typing import List, Tuple, Dict, Optional

class FileGenerator:
    def __init__(self, model):
        self.model = model
        self.current_files: Dict[str, str] = {}
        self.output_dir: Optional[str] = None

    def get_directory_tree(self, user_prompt: str) -> Tuple[List[str], str]:
        """Get the directory tree and repository title from the AI model."""
        directory_prompt = f"""Based on this user request: "{user_prompt}"
        Generate a JSON response containing two keys: "files" and "title".
        - "files" should be a Python list of file paths needed for this project.
        - "title" should be a concise title for the repository, enclosed in <title> tags.

        The response should be in this exact JSON format:
        {{
          "files": ["file1.ext", "folder/file2.ext", "folder/subfolder/file3.ext"],
          "title": "<title>Repository Title</title>"
        }}
        Include ONLY the JSON, no explanations or other text."""

        response = self.model.generate_content(directory_prompt)
        try:
            response_json = json.loads(response.text.strip())
            file_list = response_json.get("files")
            repo_title = response_json.get("title", "<title>Default Repo Title</title>") # Default title if not provided
            if not isinstance(file_list, list):
                raise ValueError("Response 'files' is not a valid list")
            if not isinstance(repo_title, str):
                raise ValueError("Response 'title' is not a valid string")
            return file_list, repo_title
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to process directory tree response: {str(e)}")


    def generate_file(self, file_path: str, user_prompt: str) -> str:
        """Generate content for a single file, removing code block tags."""
        context = self._build_context(file_path, user_prompt)

        file_prompt = f"""Based on this context:
        - User Request: "{user_prompt}"
        - Project Files: {json.dumps(list(self.current_files.keys()))}
        - Current File: "{file_path}"

        {context}

        Generate ONLY the clean content for the file "{file_path}", without any markdown formatting like code blocks (e.g., ```python, ```html).
        Provide ONLY the file content, no explanations or markdown formatting.
        IMPORTANT: In case you received personal information like tokens, API, e-mails, telephone numbers or any kind of sensible datas, do not use it in code, use a general name instead."""

        response = self.model.generate_content(file_prompt)
        content = response.text.strip()

        # Remove markdown code block tags
        content = re.sub(r'```[\w\s]*\n', '', content) # Remove opening tags
        content = re.sub(r'```', '', content) # Remove closing tags

        return content

    def _build_context(self, current_file: str, user_prompt: str) -> str:
        """Build context string including relevant existing files."""
        context_parts = []

        # Add existing file contents as context
        for path, content in self.current_files.items():
            # Only include directly related files as context
            if self._are_files_related(current_file, path):
                context_parts.append(f"Content of {path}:\n{content}")

        return "\n\n".join(context_parts)

    def _are_files_related(self, file1: str, file2: str) -> bool:
        """Determine if two files are related and should be included in context."""
        # Files in the same directory are related
        if os.path.dirname(file1) == os.path.dirname(file2):
            return True

        # Files with similar extensions might be related
        ext1 = os.path.splitext(file1)[1]
        ext2 = os.path.splitext(file2)[1]
        if ext1 == ext2:
            return True

        # Add more relationship rules as needed
        return False

    def generate_project(self, user_prompt: str) -> Tuple[str, str]:
        """Generate the complete project structure and content."""
        file_list, repo_title_tag = self.get_directory_tree(user_prompt)

        # Estract title from AI response
        title_match = re.search(r'<title>(.*?)</title>', repo_title_tag)
        repo_title = title_match.group(1) if title_match else "AI Generated Project"

        # Convert title in a valid repository name
        repo_name = re.sub(r'[^\w\s-]', '', repo_title).strip().lower().replace(' ', '-')

        # Create folder based on the title
        self.output_dir = os.path.join('data', 'projects', repo_name)

        # If the folder already exist, use a timestamp to avoid conflicts
        if os.path.exists(self.output_dir):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            repo_name += f"-{timestamp}"
            self.output_dir = os.path.join('data', 'projects', repo_name)

        os.makedirs(self.output_dir, exist_ok=True)

        # Build file structure
        for file_path in file_list:
            full_path = os.path.join(self.output_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            content = self.generate_file(file_path, user_prompt)
            self.current_files[file_path] = content
            with open(full_path, 'w') as f:
                f.write(content)

        # Create README.md if not exist
        if "README.md" not in self.current_files:
            readme_content = self.generate_file("README.md", f"Create a README.md for the project: {repo_title}")
            self.current_files["README.md"] = readme_content
            with open(os.path.join(self.output_dir, "README.md"), 'w') as f:
                f.write(readme_content)

        return self.output_dir, repo_name


        # Generate README.md if not already included
        if "README.md" not in self.current_files and "readme.md" not in self.current_files and "Readme.md" not in self.current_files:
            readme_path = os.path.join(self.output_dir, "README.md")
            readme_content = self.generate_file("README.md", f"Create a detailed README.md file for the project described by the user prompt: '{user_prompt}'.  The README should explain what the project does, how to use it, and any other relevant information.  The repository title is: '{repo_title}'.")
            self.current_files["README.md"] = readme_content # Add to current_files for context in later files if needed
            with open(readme_path, 'w') as f:
                f.write(readme_content)
        elif "README.md" in self.current_files:
            readme_path = os.path.join(self.output_dir, "README.md")
            readme_content = self.current_files["README.md"]
            with open(readme_path, 'w') as f:
                f.write(readme_content)
        elif "readme.md" in self.current_files:
            readme_path = os.path.join(self.output_dir, "readme.md")
            readme_content = self.current_files["readme.md"]
            with open(readme_path, 'w') as f:
                f.write(readme_content)
        elif "Readme.md" in self.current_files:
            readme_path = os.path.join(self.output_dir, "Readme.md")
            readme_content = self.current_files["Readme.md"]
            with open(readme_path, 'w') as f:
                f.write(readme_content)


        return self.output_dir, repo_title # Return repo_title as well
