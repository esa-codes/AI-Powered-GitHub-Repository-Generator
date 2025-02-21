import os
import re
import json
from datetime import datetime
from typing import List, Tuple

class FileGenerator:
    def __init__(self, generative_model, api_name, model_name):
        self.generative_model = generative_model
        self.api_name = api_name
        self.model_name = model_name
        self.current_files = {}  # Stores content of files already generated
        self.output_dir = None

    def get_directory_tree(self, user_prompt: str) -> Tuple[List[str], str]:
        """
        Get the directory tree and repository title from the AI model.
        The expected JSON format is:
        {
          "files": ["file1.ext", "folder/file2.ext", "folder/subfolder/file3.ext"],
          "title": "<title>Repository Title</title>"
        }
        """
        directory_prompt = (
            f"Based on this user request: \"{user_prompt}\"\n"
            "Generate a JSON response containing two keys: \"files\" and \"title\".\n"
            "- \"files\" should be a Python list of file paths needed for this project.\n"
            "- \"title\" should be a concise title for the repository, enclosed in <title> tags.\n\n"
            "The response should be in this exact JSON format:\n"
            "{\n"
            "  \"files\": [\"file1.ext\", \"folder/file2.ext\", \"folder/subfolder/file3.ext\"],\n"
            "  \"title\": \"<title>Repository Title</title>\"\n"
            "}\n\n"
            "Include ONLY the JSON, no explanations or other text."
        )

        try:
            if self.api_name == "gemini":
                response = self.generative_model.generate_content(directory_prompt)
                response_text = response.text
            elif self.api_name == "openai":
                response = self.generative_model.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful code generator assistant."},
                        {"role": "user", "content": directory_prompt}
                    ]
                )
                response_text = response.choices[0].message.content
            elif self.api_name == "mistral":
                response = self.generative_model.chat.complete(
                    model=self.model_name,
                    messages=[{"role": "user", "content": directory_prompt}]
                )
                response_text = response.choices[0].message.content
            else:
                raise ValueError("Unsupported API")

            response_text = response_text.strip()
            print("DEBUG: Raw response text:", response_text)
            if not response_text:
                raise ValueError("API returned an empty response. Check your prompt or API configuration.")

            response_json = json.loads(response_text)
            file_list = response_json.get("files")
            repo_title = response_json.get("title", "<title>Default Repo Title</title>")

            if not isinstance(file_list, list):
                raise ValueError("Response 'files' is not a valid list")
            if not isinstance(repo_title, str):
                raise ValueError("Response 'title' is not a valid string")

            return file_list, repo_title

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to process directory tree response: {str(e)}")


    def _build_context(self, file_path: str, user_request: str, directory_tree: List[str]) -> str:
        """
        Builds the context for generating a file. It includes:
          - The original user request.
          - The complete directory tree (as JSON).
          - The contents of any previously generated files that are related.
        """
        context_parts = []
        context_parts.append(f"User Request: \"{user_request}\"")
        context_parts.append(f"Directory Tree: {json.dumps(directory_tree)}")

        # Add contents of previously generated files that are related.
        for path, content in self.current_files.items():
            if self._are_files_related(file_path, path):
                context_parts.append(f"Content of {path}:\n{content}")

        return "\n\n".join(context_parts)

    def _are_files_related(self, file1: str, file2: str) -> bool:
        """
        Two files are considered related if they are in the same directory
        or if they have the same file extension.
        """
        if os.path.dirname(file1) == os.path.dirname(file2):
            return True
        if os.path.splitext(file1)[1] == os.path.splitext(file2)[1]:
            return True
        return False

    def generate_file(self, file_path: str, user_request: str, directory_tree: List[str]) -> str:
        """
        Generates the content for a specific file using the user request,
        the directory tree, and any already generated files.
        """
        context = self._build_context(file_path, user_request, directory_tree)
        prompt = (
            f"Based on the following context:\n{context}\n\n"
            f"Generate the clean content for the file \"{file_path}\". "
            "Do not include any markdown formatting, code block tags, or additional explanations. "
            "Output only the raw file content."
        )

        if self.api_name == "gemini":
            response = self.generative_model.generate_content(prompt)
            content = response.text
        elif self.api_name == "openai":
            response = self.generative_model.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful code generator."},
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.choices[0].message.content
        elif self.api_name == "mistral":
            response = self.generative_model.chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
        else:
            raise ValueError("Unsupported API")

        # Remove any markdown formatting (e.g., ``` markers)
        content = content.strip()
        content = re.sub(r'```[\w\s]*\n', '', content)
        content = re.sub(r'```', '', content)
        return content

    def generate_project(self, user_request: str) -> Tuple[str, str]:
        """
        Generates an entire project iteratively.
          1. Generate the directory tree (JSON) based on the user request.
          2. For each file in the tree:
             - Generate the file content using the user request, the directory tree, and previously generated files.
             - Save the file in the output directory.
          3. If README.md was not generated, create it.
        Returns the output directory and the repository name.
        """
        # Step 1: Get the directory tree and repository title.
        file_list, title_tag = self.get_directory_tree(user_request)
        title_match = re.search(r'<title>(.*?)</title>', title_tag)
        repo_title = title_match.group(1) if title_match else "AI Generated Project"
        repo_name = re.sub(r'[^\w\s-]', '', repo_title).strip().lower().replace(' ', '-')

        self.output_dir = os.path.join('data', 'projects', repo_name)
        if os.path.exists(self.output_dir):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            repo_name = f"{repo_name}-{timestamp}"
            self.output_dir = os.path.join('data', 'projects', repo_name)
        os.makedirs(self.output_dir, exist_ok=True)

        # Step 2: Iteratively generate each file.
        for file_path in file_list:
            full_path = os.path.join(self.output_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            file_content = self.generate_file(file_path, user_request, file_list)
            self.current_files[file_path] = file_content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file_content)

        # Step 3: Generate a README.md if not already provided.
        if "README.md" not in self.current_files:
            readme_content = self.generate_file("README.md", f"Create a README.md for the project: {repo_title}", file_list)
            self.current_files["README.md"] = readme_content
            with open(os.path.join(self.output_dir, "README.md"), 'w', encoding='utf-8') as f:
                f.write(readme_content)

        return self.output_dir, repo_name
