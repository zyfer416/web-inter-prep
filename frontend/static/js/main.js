/**
 * Web-Inter-Prep Main JavaScript File
 * Handles common functionality across the application
 */

// Global variables
let currentQuestion = null;
let timerInterval = null;
let sessionStartTime = null;

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    initializeMoreDropdown();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Add fade-in animation to cards
    addFadeInAnimation();
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.querySelector('.btn-close')) {
                const alertInstance = new bootstrap.Alert(alert);
                alertInstance.close();
            }
        });
    }, 5000);
}

/**
 * Initialize enhanced More dropdown functionality
 */
function initializeMoreDropdown() {
    const moreDropdown = document.getElementById('moreDropdown');
    const moreMenu = document.querySelector('.more-dropdown');
    
    if (moreDropdown && moreMenu) {
        // Add smooth animation when dropdown opens
        moreDropdown.addEventListener('show.bs.dropdown', function () {
            moreMenu.style.opacity = '0';
            moreMenu.style.transform = 'translateY(-10px)';
            
            setTimeout(() => {
                moreMenu.style.transition = 'all 0.3s ease-out';
                moreMenu.style.opacity = '1';
                moreMenu.style.transform = 'translateY(0)';
            }, 10);
        });

        // Add smooth animation when dropdown closes
        moreDropdown.addEventListener('hide.bs.dropdown', function () {
            moreMenu.style.transition = 'all 0.2s ease-in';
            moreMenu.style.opacity = '0';
            moreMenu.style.transform = 'translateY(-10px)';
        });

        // Add hover effects for menu items
        const menuItems = moreMenu.querySelectorAll('.dropdown-item');
        menuItems.forEach(item => {
            item.addEventListener('mouseenter', function() {
                this.style.transform = 'translateX(8px)';
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.transform = 'translateX(0)';
            });
        });

        // Add click handlers for menu items
        menuItems.forEach(item => {
            item.addEventListener('click', function(e) {
                const text = this.textContent.trim();
                
                // Add specific functionality for each menu item
                switch(text) {
                    case 'Company Prep':
                        // Show coming soon message and prevent default
                        e.preventDefault();
                        showMessage('Company preparation features coming soon!', 'info');
                        break;
                    case 'AI Interview':
                        // Show coming soon message and prevent default
                        e.preventDefault();
                        showMessage('AI Interview feature is coming soon! Stay tuned for updates.', 'info');
                        break;
                    case 'Resume':
                        // Show coming soon message and prevent default
                        e.preventDefault();
                        showMessage('Resume builder coming soon!', 'info');
                        break;
                    case 'Calendar':
                        // Show coming soon message and prevent default
                        e.preventDefault();
                        showMessage('Interview calendar features coming soon!', 'info');
                        break;
                    case 'DSA':
                        // DSA has direct link - allow normal navigation
                        showMessage('Opening DSA Practice...', 'info');
                        break;
                    case 'Resources':
                        // Resources has direct link - allow normal navigation
                        showMessage('Opening Resources...', 'info');
                        break;
                    case 'Career Roadmap':
                        // Career Roadmap has direct link - allow normal navigation
                        showMessage('Opening Career Roadmap...', 'info');
                        break;
                }
            });
        });
    }
}

/**
 * Add fade-in animation to cards
 */
function addFadeInAnimation() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });
}

/**
 * Show/hide hint for practice questions
 */
function toggleHint(questionId) {
    const hintElement = document.getElementById(`hint-${questionId}`);
    const hintButton = document.getElementById(`hint-btn-${questionId}`);
    
    if (hintElement.style.display === 'none' || hintElement.style.display === '') {
        hintElement.style.display = 'block';
        hintButton.innerHTML = '<i class="fas fa-eye-slash me-2"></i>Hide Hint';
        hintButton.className = 'btn btn-warning';
    } else {
        hintElement.style.display = 'none';
        hintButton.innerHTML = '<i class="fas fa-lightbulb me-2"></i>Show Hint';
        hintButton.className = 'btn btn-outline-warning';
    }
}

/**
 * Show/hide answer for practice questions
 */
function toggleAnswer(questionId) {
    const answerElement = document.getElementById(`answer-${questionId}`);
    const answerButton = document.getElementById(`answer-btn-${questionId}`);
    
    if (answerElement.style.display === 'none' || answerElement.style.display === '') {
        answerElement.style.display = 'block';
        answerButton.innerHTML = '<i class="fas fa-eye-slash me-2"></i>Hide Answer';
        answerButton.className = 'btn btn-success';
    } else {
        answerElement.style.display = 'none';
        answerButton.innerHTML = '<i class="fas fa-check-circle me-2"></i>Show Answer';
        answerButton.className = 'btn btn-outline-success';
    }
}

/**
 * Start a timer for mock interviews
 */
function startTimer(duration) {
    sessionStartTime = new Date();
    let timeRemaining = duration * 60; // Convert minutes to seconds
    
    const timerElement = document.getElementById('timer-display');
    if (!timerElement) return;
    
    timerInterval = setInterval(function() {
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        
        timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Change color when time is running low
        if (timeRemaining <= 300) { // 5 minutes
            timerElement.className = 'timer-display text-danger';
        } else if (timeRemaining <= 600) { // 10 minutes
            timerElement.className = 'timer-display text-warning';
        }
        
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            endMockInterview();
        }
        
        timeRemaining--;
    }, 1000);
}

/**
 * Stop the timer
 */
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

/**
 * End mock interview session
 */
function endMockInterview() {
    stopTimer();
    
    // Show completion message
    showMessage('Mock interview session completed!', 'info');
    
    // Redirect to results page after a short delay
    setTimeout(function() {
        window.location.href = '/mock/results';
    }, 2000);
}

/**
 * Submit an answer for a question
 */
function submitAnswer(questionId, isCorrect, userAnswer = '') {
    const data = {
        question_id: questionId,
        correct: isCorrect,
        user_answer: userAnswer
    };
    
    fetch('/submit-answer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showMessage('Answer submitted successfully!', 'success');
            
            // Update statistics if on dashboard
            updateDashboardStats();
        } else {
            showMessage('Failed to submit answer. Please try again.', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('An error occurred. Please try again.', 'error');
    });
}

/**
 * Update dashboard statistics
 */
function updateDashboardStats() {
    fetch('/api/stats')
    .then(response => response.json())
    .then(data => {
        // Update stats on the page
        const elements = {
            'total-attempted': data.total_attempted,
            'correct-answers': data.correct_answers,
            'accuracy': data.accuracy + '%',
            'weak-topics': data.weak_topics.length
        };
        
        Object.keys(elements).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = elements[id];
            }
        });
    })
    .catch(error => {
        console.error('Error updating stats:', error);
    });
}

/**
 * Show a message to the user
 */
function showMessage(message, type = 'info') {
    const alertClass = type === 'error' ? 'danger' : type;
    const alertHtml = `
        <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Find or create message container
    let messageContainer = document.getElementById('message-container');
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.id = 'message-container';
        messageContainer.className = 'container mt-3';
        
        // Insert after nav element
        const nav = document.querySelector('nav');
        if (nav && nav.parentNode) {
            nav.parentNode.insertBefore(messageContainer, nav.nextSibling);
        } else {
            // Fallback: insert at the beginning of body
            document.body.insertBefore(messageContainer, document.body.firstChild);
        }
    }
    
    messageContainer.innerHTML = alertHtml;
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        const alert = messageContainer.querySelector('.alert');
        if (alert) {
            const alertInstance = new bootstrap.Alert(alert);
            alertInstance.close();
        }
    }, 5000);
}

/**
 * Load next question in practice mode
 */
function loadNextQuestion() {
    showSpinner();
    
    fetch('/api/next-question')
    .then(response => response.json())
    .then(data => {
        hideSpinner();
        
        if (data.question) {
            currentQuestion = data.question;
            displayQuestion(data.question);
        } else {
            showMessage('No more questions available.', 'info');
        }
    })
    .catch(error => {
        hideSpinner();
        console.error('Error:', error);
        showMessage('Failed to load question. Please try again.', 'error');
    });
}

/**
 * Display a question on the page
 */
function displayQuestion(question) {
    const questionContainer = document.getElementById('question-container');
    if (!questionContainer) return;
    
    const questionHtml = `
        <div class="card question-card">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <span class="badge bg-${question.type === 'technical' ? 'primary' : 'success'} fs-6">
                        ${question.type.charAt(0).toUpperCase() + question.type.slice(1)}
                    </span>
                    <span class="badge bg-${getDifficultyColor(question.difficulty)} fs-6">
                        ${question.difficulty.charAt(0).toUpperCase() + question.difficulty.slice(1)}
                    </span>
                </div>
                
                <h4 class="card-title">${question.question}</h4>
                
                <div class="mt-4">
                    <button class="btn btn-outline-warning me-2" id="hint-btn-${question.id}" 
                            onclick="toggleHint(${question.id})">
                        <i class="fas fa-lightbulb me-2"></i>Show Hint
                    </button>
                    <button class="btn btn-outline-success me-2" id="answer-btn-${question.id}" 
                            onclick="toggleAnswer(${question.id})">
                        <i class="fas fa-check-circle me-2"></i>Show Answer
                    </button>
                    <button class="btn btn-primary" onclick="loadNextQuestion()">
                        <i class="fas fa-forward me-2"></i>Next Question
                    </button>
                </div>
                
                <div id="hint-${question.id}" class="hint-section" style="display: none;">
                    <h6><i class="fas fa-lightbulb me-2"></i>Hint:</h6>
                    <p>${question.hints}</p>
                </div>
                
                <div id="answer-${question.id}" class="answer-section" style="display: none;">
                    <h6><i class="fas fa-check-circle me-2"></i>Answer:</h6>
                    <p>${question.answer}</p>
                </div>
            </div>
        </div>
    `;
    
    questionContainer.innerHTML = questionHtml;
}

/**
 * Get color class for difficulty level
 */
function getDifficultyColor(difficulty) {
    switch (difficulty.toLowerCase()) {
        case 'easy': return 'success';
        case 'medium': return 'warning';
        case 'hard': return 'danger';
        default: return 'secondary';
    }
}

/**
 * Show loading spinner
 */
function showSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.id = 'loading-spinner';
    
    const container = document.querySelector('.container');
    if (container) {
        container.appendChild(spinner);
    }
}

/**
 * Hide loading spinner
 */
function hideSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showMessage('Copied to clipboard!', 'success');
    }, function(err) {
        console.error('Could not copy text: ', err);
        showMessage('Failed to copy to clipboard', 'error');
    });
}

/**
 * Format time duration
 */
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function loadMockQuestion() {
    showSpinner();
    fetch('/mock/question')
        .then(response => response.json())
        .then(data => {
            hideSpinner();
            if (data.question) {
                currentQuestion = data.question;
                displayQuestion(data.question);
            } else if (data.error) {
                showMessage(data.error, 'error');
            } else {
                showMessage('No questions available.', 'info');
            }
        })
        .catch(error => {
            hideSpinner();
            console.error('Error:', error);
            showMessage('Failed to load question. Please try again.', 'error');
        });
}

// // At the end of your JS file
// if (window.location.pathname === '/mock') {
//     document.addEventListener('DOMContentLoaded', function() {
//         loadMockQuestion();
//     });
// }
