from flask import Flask, render_template, request, redirect, url_for, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
from datetime import datetime
from generate_files import FileGenerator
from github_handler import GitHubHandler
import shutil
import requests
import mistralai
from mistralai import Mistral

load_dotenv()

app = Flask(__name__)

# Function to get the valid API key
def get_api_key():
    api_keys = {
        "GOOGLE_API_KEY": "gemini",
        "OPENAI_API_KEY": "openai",
        "MISTRAL_API_KEY": "mistral"
    }

    for env_var, api_name in api_keys.items():
        api_key = os.getenv(env_var)
        if api_key:
            print(f"Using {api_name} API with key from {env_var}")
            return api_key, api_name

    raise ValueError("No valid API key found in environment variables")

# Configure the selected API
api_key, api_name = get_api_key()

if api_name == "gemini":
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = 'gemini-pro'  # Define model for the gemini API
    generative_model = genai.GenerativeModel(model)
elif api_name == "openai":
    import openai
    openai.api_key = api_key
    model = "gpt-3.5-turbo"  # o "gpt-4" se hai accesso
    generative_model = openai.ChatCompletion
elif api_name == "mistral":
    from mistralai import Mistral
    model = "mistral-medium"  # o "mistral-small" o "mistral-large-latest"
    generative_model = Mistral(api_key=api_key)
else:
    raise ValueError("Unsupported API")

REPOS_PER_PAGE = 50

def is_repo_link_valid(repo_url):
    """
    Checks if a repository link is valid by making a HEAD request.
    Returns True if valid (status code 200-399), False if 404, and None for other errors.
    """
    try:
        response = requests.head(repo_url, allow_redirects=True, timeout=5)
        return 200 <= response.status_code < 400
    except requests.exceptions.RequestException:
        return None

def get_github_repo_info(repo_url):
    """
    Extracts repository information from GitHub API and tests different preview image URLs.
    """
    try:
        # Extract username and repository name from URL
        parts = repo_url.rstrip('/').split('github.com/')
        if len(parts) != 2:
            return None

        username_repo = parts[1].split('/')
        if len(username_repo) != 2:
            return None

        username, repo_name = username_repo

        # GitHub API endpoint
        api_url = f"https://api.github.com/repos/{username}/{repo_name}"

        # Add GitHub token if available
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        if 'GITHUB_TOKEN' in os.environ:
            headers['Authorization'] = f"token {os.getenv('GITHUB_TOKEN')}"

        # Make request to GitHub API
        response = requests.get(api_url, headers=headers, timeout=5)

        if response.status_code == 200:
            repo_data = response.json()

            # Try different approaches to get an image
            image_url = None

            # Lista di possibili URL per le preview images
            preview_urls = [
                f"https://opengraph.githubassets.com/1/{username}/{repo_name}",  # OG Image
                f"https://repository-images.githubusercontent.com/{repo_data['id']}/social",  # Social Card
                f"https://raw.githubusercontent.com/{username}/{repo_name}/master/preview.png",  # Custom preview
                repo_data['owner']['avatar_url'],  # Owner avatar
                "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"  # Default
            ]

            # Test each URL until we find one that works
            for url in preview_urls:
                try:
                    preview_response = requests.head(url, allow_redirects=True, timeout=2)
                    if preview_response.status_code == 200:
                        image_url = url
                        break
                except:
                    continue

            return {
                "title": repo_data['full_name'],
                "description": repo_data['description'] or "No description available.",
                "image": image_url,
                "stars": repo_data['stargazers_count'],
                "language": repo_data['language'],
                "forks": repo_data['forks_count']
            }
    except Exception as e:
        print(f"Error fetching GitHub repo info: {e}")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/repositories')
def get_repositories():
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'recent')
    search_term = request.args.get('search', '', type=str).lower()

    # Map frontend sort options to GitHub API parameters
    sort_mapping = {
        'recent': ('created', 'desc'),
        'name': ('full_name', 'asc'),
        'rating': ('stars', 'desc')  # Using stars as a proxy for rating
    }

    sort_param, direction = sort_mapping.get(sort_by, ('created', 'desc'))

    try:
        github_handler = GitHubHandler()
        result = github_handler.get_all_repositories(
            page=page,
            per_page=REPOS_PER_PAGE,
            sort=sort_param,
            direction=direction
        )

        if result is None:
            return jsonify({'error': 'Failed to fetch repositories'}), 500

        # Filter repositories by search term if provided
        if search_term:
            filtered_repos = [
                repo for repo in result['repositories']
                if search_term in repo['repo_name'].lower() or
                (repo['link_preview']['description'] and
                 search_term in repo['link_preview']['description'].lower())
            ]

            # Recalculate pagination for filtered results
            total_filtered = len(filtered_repos)
            total_pages = (total_filtered + REPOS_PER_PAGE - 1) // REPOS_PER_PAGE

            # Paginate filtered results
            start_idx = (page - 1) * REPOS_PER_PAGE
            end_idx = start_idx + REPOS_PER_PAGE
            paginated_repos = filtered_repos[start_idx:end_idx]

            return jsonify({
                'repositories': paginated_repos,
                'total_pages': total_pages,
                'current_page': page
            })

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error fetching repositories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate_code():
    try:
        user_prompt = request.form.get('prompt')
        if not user_prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        # Initialize the file generator with all necessary parameters
        file_generator = FileGenerator(
            generative_model=generative_model,
            api_name=api_name,
            model_name=model
        )
        output_dir = None  # Initialize output_dir here

        try:
            # Generate the project and separate output_dir and repo_title
            output_dir, repo_name = file_generator.generate_project(user_prompt)

            # Create the GitHub repository
            github_handler = GitHubHandler()
            repo_url = github_handler.create_repository(repo_name, output_dir)

            # Clean up the local directory
            shutil.rmtree(output_dir)

            # Get the repository details from GitHub
            repo_info = github_handler.get_repository_info(repo_name)

            # Return the newly created repository details
            return jsonify({
                'repo_name': repo_info['name'],
                'repo_url': repo_info['url'],
                'repo_timestamp': repo_info['created_at'].strftime('%B %d, %Y'),
                'repo_id': repo_name,
                'link_preview': {
                    'title': repo_info['name'],
                    'description': repo_info['description'],
                    'stars': repo_info['stars']
                }
            })

        except Exception as e:
            if output_dir and os.path.exists(output_dir):
                shutil.rmtree(output_dir)  # Clean up only if output_dir exists
            raise e

    except Exception as e:
        app.logger.error(f"Error generating code: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)

