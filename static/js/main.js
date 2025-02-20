// DOM Elements
const searchInput = document.getElementById('repo-search');
const sortSelect = document.getElementById('sort-select');
const repoGrid = document.querySelector('.repository-grid');
const loadingOverlay = document.getElementById('loading-overlay');
const generateForm = document.getElementById('generate-app-form');
const successModal = document.getElementById('success-modal');
const closeModalButton = document.getElementById('close-modal');
const repoLink = document.getElementById('repo-link');
const generateButton = document.getElementById('generateAppButton');

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Repository Manager Class
class RepositoryManager {
    constructor() {
        this.repositories = [];
        this.currentFilter = '';
        this.currentSort = 'recent';
        this.currentPage = 1;
        this.totalPages = 1;
        this.isLoadingMore = false;
    }

    async loadRepositories(page = 1, searchTerm = '', sortMethod = 'recent', shouldReplace = true) {
        if (this.isLoadingMore) return;
        this.isLoadingMore = true;

        try {
            const response = await fetch(
                `/api/repositories?page=${page}` +
                `&sort=${encodeURIComponent(sortMethod)}` +
                `&search=${encodeURIComponent(searchTerm)}`
            );

            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();

            // Reset grid when loading new data set
            if (shouldReplace || page === 1) {
                repoGrid.innerHTML = '';
                this.repositories = [];
            }

            this.appendRepositories(data.repositories);
            this.totalPages = data.total_pages;
            this.currentPage = data.current_page;

            this.updateNoResultsMessage(
                data.repositories.length === 0 &&
                page === 1
            );

        } catch (error) {
            console.error('Repository load error:', error);
            showNotification('Failed to load repositories', 'error');
        } finally {
            this.isLoadingMore = false;
        }
    }

    // Remove the rating-related code and update createRepositoryElement
    createRepositoryElement(repo) {
        const article = document.createElement('article');
        article.className = 'repo-card bg-white rounded-lg shadow-md overflow-hidden transition-all duration-300';
        article.dataset.repoId = repo.repo_id;
        article.dataset.timestamp = repo.repo_timestamp;

        let linkPreviewHTML = '';
        if (repo.link_preview && repo.link_preview.title) {
            const preview = repo.link_preview;
            linkPreviewHTML = `
                <div class="border-b">
                    ${preview.image ?
                        `<div class="w-full">
                            <img src="${preview.image}"
                                 alt="${preview.title}"
                                 class="w-full h-48 object-cover rounded-t-lg"
                                 onerror="this.onerror=null; this.src='https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png';">
                        </div>` :
                        `<div class="w-full">
                            <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                                 alt="Default Repository Image"
                                 class="w-full h-48 object-contain rounded-t-lg">
                        </div>`}
                    <div class="p-4">
                        <h3 class="text-lg font-semibold">${preview.title}</h3>
                        <p class="text-gray-600 mt-1">${preview.description}</p>
                        ${preview.language ?
                            `<p class="text-sm text-gray-500 mt-2">
                                <span class="font-medium">Primary Language:</span> ${preview.language}
                            </p>` :
                            ''}
                        <div class="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                            <span><i class="fas fa-star text-yellow-400"></i> ${preview.stars || 0}</span>
                            <span><i class="fas fa-code-fork"></i> ${preview.forks || 0}</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            linkPreviewHTML = `
                <div class="p-4 text-center text-gray-500">
                    <p>Repository information unavailable</p>
                </div>
            `;
        }

        article.innerHTML = `
            <section>
                ${linkPreviewHTML}
            </section>
            <footer class="p-4 bg-gray-50 border-t flex justify-between items-center">
                <span class="text-sm text-gray-600">Created ${repo.repo_timestamp}</span>
                <a href="${repo.repo_url}"
                   target="_blank"
                   class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                    View Repo
                </a>
            </footer>
        `;

        return article;
    }

    appendRepositories(repositoriesData) {
        repositoriesData.forEach(repoData => {
            const repoElement = this.createRepositoryElement(repoData);
            repoGrid.appendChild(repoElement);
            this.repositories.push(repoElement);
        });
    }
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg ${
        type === 'error' ? 'bg-red-500' : 'bg-green-500'
    } text-white transform transition-all duration-300 translate-y-0 opacity-100`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Modified updateRepositoryGrid for GitHub sync
async function updateRepositoryGrid() {
    try {
        const response = await fetch(`/api/repositories?sort=${repoManager.currentSort}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const freshRepos = data.repositories.map(repo => ({
            repo_id: repo.id,
            repo_url: repo.html_url,
            repo_timestamp: new Date(repo.created_at).toLocaleDateString(),
            link_preview: {
                title: repo.full_name,
                description: repo.description,
                image: repo.owner?.avatar_url,
                stars: repo.stargazers_count,
                language: repo.language
            }
        }));

        const existingIds = new Set(
            Array.from(repoGrid.querySelectorAll('.repo-card'))
                .map(el => el.dataset.repoId)
        );

        // Add new repos silently
        freshRepos.forEach(repo => {
            if (!existingIds.has(repo.repo_id.toString())) {
                const repoElement = createRepositoryElement(repo);
                repoGrid.prepend(repoElement);
            }
        });

    } catch (error) {
        console.error('Silent update failed:', error);
    }
}

// Updated generateForm submit event listener to use a separate error modal
generateForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    loadingOverlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    generateButton.disabled = true;

    const promptText = document.getElementById('prompt').value;

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({ prompt: promptText }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const repoData = await response.json();

        repoLink.href = repoData.repo_url;
        repoLink.textContent = repoData.repo_url;

        loadingOverlay.style.display = 'none';
        successModal.style.display = 'flex';

        // Refresh the repository grid
        await repoManager.loadRepositories(1, '', 'recent', true);

    } catch (error) {
        console.error('Error generating application:', error);
        loadingOverlay.style.display = 'none';
        document.body.style.overflow = 'auto';
        showErrorModal("Uh oh! We encountered an error while generating your application. Please try again later.");
    } finally {
        generateButton.disabled = false;
    }
});

// New function to display an error modal using a separate errorModal element
function showErrorModal(message) {
    const errorModal = document.getElementById('error-modal');
    errorModal.innerHTML = `
        <div style="display: flex; align-items: center; padding: 20px;">
            <span style="font-size: 50px; margin-right: 20px;">😢</span>
            <div>
                <h2 style="margin: 0; font-size: 24px;">Error</h2>
                <p style="margin: 5px 0 0;">${message}</p>
            </div>
            <button id="close-error-modal" style="margin-left: auto; background: none; border: none; font-size: 20px;">&times;</button>
        </div>
    `;
    errorModal.classList.remove('hidden');
    errorModal.style.display = 'flex';

    // Add event listener to close the error modal when the close button is clicked
    document.getElementById('close-error-modal').addEventListener('click', () => {
        errorModal.style.display = 'none';
        document.body.style.overflow = 'auto';
    });
}


// Close modal button handler
closeModalButton.addEventListener('click', () => {
    successModal.style.display = 'none';
    document.body.style.overflow = 'auto';
    updateRepositoryGrid();});

// Close modal if clicking outside
successModal.addEventListener('click', (e) => {
    if (e.target === successModal) {
        successModal.style.display = 'none';
        document.body.style.overflow = 'auto';
        //updateRepositoryGrid();
    }
});

// Modified createRepositoryElement using GitHub data
function createRepositoryElement(repo) {
    const article = document.createElement('article');
    article.className = 'repo-card bg-white rounded-lg shadow-md overflow-hidden';
    article.dataset.repoId = repo.repo_id;

    const imageFallback = 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png';
    const preview = repo.link_preview;

    const imageHTML = preview.image ?
        `<img src="${preview.image}"
              alt="${preview.title}"
              class="w-full h-48 object-cover rounded-t-lg"
              onerror="this.src='${imageFallback}'">` :
        `<img src="${imageFallback}"
              alt="Default Repository Image"
              class="w-full h-48 object-contain rounded-t-lg">`;

    article.innerHTML = `
        <section class="border-b">
            <div class="w-full">${imageHTML}</div>
            <div class="p-4">
                <h3 class="text-lg font-semibold">${preview.title}</h3>
                <p class="text-gray-600 mt-1">${preview.description}</p>
                ${preview.language ?
                    `<p class="text-sm text-gray-500 mt-2">
                        <span class="font-medium">Language:</span> ${preview.language}
                    </p>` : ''}
                <div class="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                    <span><i class="fas fa-star text-yellow-400"></i> ${preview.stars}</span>
                    <span><i class="fas fa-code-fork"></i> ${preview.forks}</span>
                </div>
            </div>
        </section>
        <footer class="p-4 flex justify-between items-center">
            <span class="text-sm text-gray-500">${repo.repo_timestamp}</span>
            <a href="${repo.repo_url}"
               target="_blank"
               class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                View Repo
            </a>
        </footer>
    `;

    return article;
}

// Generate star rating HTML
function generateStarRatingHTML(rating, repoId) {
    let starsHTML = '';
    for (let i = 1; i <= 5; i++) {
        const starClass = i <= rating ? 'fa-solid starred' : 'fa-regular';
        starsHTML += `<i class="star-rating fa-star ${starClass}" data-rating="${i}" onclick="rateRepo('${repoId}', ${i})"></i>`;
    }
    return starsHTML;
}

// Initialize repository manager
const repoManager = new RepositoryManager();

// Event listeners
closeModalButton.addEventListener('click', () => {
    // Hide the modal by removing the "active" class
    successModal.classList.remove('active');
});

searchInput.addEventListener('input', debounce(() => {
    repoManager.filter(searchInput.value);
}, 300));

sortSelect.addEventListener('change', (e) => {
    repoManager.sort(e.target.value);
});

// Infinite scroll
window.addEventListener('scroll', debounce(() => {
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 5) {
        repoManager.loadMore();
    }
}, 100));

// Initial repository load
document.addEventListener('DOMContentLoaded', () => {
    repoManager.loadRepositories();

    const repos = document.querySelectorAll('.repo-card');
    repos.forEach((repo, index) => {
        setTimeout(() => {
            repo.style.opacity = '1';
            repo.style.transform = 'translateY(0)';
        }, index * 100);
    });
});
