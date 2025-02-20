# AI-Powered GitHub Repository Generator

## Description
This Flask-based web application enables users to generate AI-assisted project structures and automatically create GitHub repositories. It leverages Google's Gemini AI model to generate project files based on user prompts and integrates with the GitHub API for repository creation and management.

## Features
- **AI-powered project generation**: Uses Google's Gemini AI model to create structured project files.
- **GitHub integration**: Automatically creates repositories on GitHub.
- **Custom repository preview**: Extracts metadata and images for GitHub repositories.
- **Sorting and searching**: Allows sorting and filtering repositories by name, stars, and creation date.
- **Docker support**: Includes Docker, Docker Compose, and Dockerfile for seamless deployment.
- **Privacy compliance**: Includes a dedicated privacy policy page.

## Installation
### Prerequisites
- Docker & Docker Compose installed
- GitHub account with a personal access token
- Google API key for Gemini AI

### Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```
2. Build and run the application using Docker:
   ```sh
   docker-compose up --build
   ```
3. Open the application in your browser:
   ```
   http://127.0.0.1:5000/
   ```

## API Endpoints
### `GET /api/repositories`
Fetches GitHub repositories with sorting and pagination.

### `POST /generate`
Generates project files based on user input and creates a GitHub repository.

### `GET /privacy`
Returns the privacy policy page.

## Deployment
To deploy this application, use any container-based platform such as AWS, DigitalOcean, or others that support Docker.

## License
This project is licensed under the MIT License.

## Contributing
Feel free to submit pull requests or open issues for suggestions and improvements.
