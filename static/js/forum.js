/**
 * KalyanX - Forum JS
 * Handles forum-related functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Format dates
    formatForumDates();
    
    // Apply syntax highlighting to code blocks
    const codeBlocks = document.querySelectorAll('pre code');
    if (codeBlocks.length > 0 && window.hljs) {
        codeBlocks.forEach(block => {
            hljs.highlightBlock(block);
        });
    }
    
    // Comment form submission
    const commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            const commentContent = document.getElementById('content');
            if (!commentContent.value.trim()) {
                e.preventDefault();
                showToast('Error', 'Comment cannot be empty', 'danger');
            }
        });
    }
    
    // Reply buttons
    const replyButtons = document.querySelectorAll('.reply-btn');
    replyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const commentId = this.getAttribute('data-comment-id');
            const replyFormContainer = document.getElementById(`reply-form-${commentId}`);
            
            // Toggle reply form visibility
            if (replyFormContainer) {
                replyFormContainer.classList.toggle('d-none');
                
                // Focus on textarea if form is visible
                if (!replyFormContainer.classList.contains('d-none')) {
                    const textarea = replyFormContainer.querySelector('textarea');
                    if (textarea) {
                        textarea.focus();
                    }
                }
            }
        });
    });
    
    // Post form validation
    const postForm = document.getElementById('post-form');
    if (postForm) {
        postForm.addEventListener('submit', function(e) {
            const title = document.getElementById('title').value.trim();
            const content = document.getElementById('content').value.trim();
            const category = document.getElementById('category_id').value;
            
            if (!title || !content || !category) {
                e.preventDefault();
                showToast('Error', 'Please fill out all fields', 'danger');
            }
        });
    }
    
    // Initialize rich text editor if it exists
    const editorElement = document.getElementById('content');
    if (editorElement && window.ClassicEditor) {
        ClassicEditor
            .create(editorElement, {
                toolbar: ['heading', '|', 'bold', 'italic', 'link', 'bulletedList', 'numberedList', '|', 'code', 'blockQuote'],
                placeholder: 'Write your message here...'
            })
            .catch(error => {
                console.error(error);
            });
    }
    
    // Search form
    const searchForm = document.getElementById('forum-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('search-query');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                showToast('Error', 'Please enter a search query', 'danger');
            }
        });
    }
    
    // Handle pagination
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!this.getAttribute('href')) {
                e.preventDefault();
            }
        });
    });
});

/**
 * Format dates in forum pages
 */
function formatForumDates() {
    const dateElements = document.querySelectorAll('.forum-date');
    dateElements.forEach(element => {
        const dateString = element.getAttribute('data-date');
        if (dateString) {
            const date = new Date(dateString);
            element.textContent = timeAgo(date);
            element.setAttribute('title', formatDateTime(date));
        }
    });
}

/**
 * Quote a comment in the reply form
 * @param {number} commentId - The ID of the comment to quote
 */
function quoteComment(commentId) {
    const commentContent = document.querySelector(`#comment-${commentId} .comment-content`);
    const commentAuthor = document.querySelector(`#comment-${commentId} .comment-author`);
    
    if (commentContent && commentAuthor) {
        const content = commentContent.textContent.trim();
        const author = commentAuthor.textContent.trim();
        
        // Generate quoted text
        const quotedText = `> **${author} wrote:**\n> ${content.replace(/\n/g, '\n> ')}\n\n`;
        
        // Find the reply form textarea
        const replyForm = document.getElementById(`reply-form-${commentId}`);
        if (replyForm) {
            const textarea = replyForm.querySelector('textarea');
            if (textarea) {
                // Show the reply form if it's hidden
                replyForm.classList.remove('d-none');
                
                // Insert quoted text at cursor position or append to existing text
                if (textarea.selectionStart || textarea.selectionStart === 0) {
                    const startPos = textarea.selectionStart;
                    const endPos = textarea.selectionEnd;
                    textarea.value = textarea.value.substring(0, startPos) + quotedText + textarea.value.substring(endPos);
                    textarea.selectionStart = startPos + quotedText.length;
                    textarea.selectionEnd = startPos + quotedText.length;
                } else {
                    textarea.value += quotedText;
                }
                
                textarea.focus();
            }
        }
    }
}

/**
 * Like a post or comment
 * @param {string} type - The type of content (post or comment)
 * @param {number} id - The ID of the content
 * @param {HTMLElement} button - The like button element
 */
function likeContent(type, id, button) {
    fetch(`/forum/${type}/${id}/like`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update like count
            const likeCount = button.querySelector('.like-count');
            if (likeCount) {
                likeCount.textContent = data.likes;
            }
            
            // Toggle button state
            if (data.liked) {
                button.classList.add('liked');
                button.querySelector('i').classList.remove('far');
                button.querySelector('i').classList.add('fas');
            } else {
                button.classList.remove('liked');
                button.querySelector('i').classList.remove('fas');
                button.querySelector('i').classList.add('far');
            }
        } else {
            showToast('Error', data.message || 'Failed to like content', 'danger');
        }
    })
    .catch(error => {
        console.error('Error liking content:', error);
        showToast('Error', 'Failed to like content', 'danger');
    });
}

/**
 * Share forum post
 * @param {number} postId - The ID of the post to share
 * @param {string} title - The title of the post
 */
function sharePost(postId, title) {
    // Generate share URL
    const shareUrl = `${window.location.origin}/forum/post/${postId}`;
    
    // Check if Web Share API is available
    if (navigator.share) {
        navigator.share({
            title: title,
            text: `Check out this KalyanX forum post: ${title}`,
            url: shareUrl
        })
        .catch(error => {
            console.error('Error sharing post:', error);
            // Fallback to clipboard copy if sharing fails
            fallbackShareToClipboard(shareUrl, title);
        });
    } else {
        // Fallback for browsers that don't support Web Share API
        fallbackShareToClipboard(shareUrl, title);
    }
}

/**
 * Fallback share method - copy URL to clipboard
 * @param {string} url - The URL to share
 * @param {string} title - The title of the content
 */
function fallbackShareToClipboard(url, title) {
    copyToClipboard(url)
        .then(() => {
            showToast('Success', 'Link copied to clipboard!', 'success');
        })
        .catch(() => {
            showToast('Error', 'Failed to copy link', 'danger');
        });
}
