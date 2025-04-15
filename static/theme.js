// Theme toggle functionality
document.addEventListener('DOMContentLoaded', () => {
  // Check for saved theme preference or use default (light)
  const savedTheme = localStorage.getItem('theme') || 'light';
  
  // Apply the saved theme
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  // Update toggle button icon based on current theme
  updateThemeToggleIcon(savedTheme);
  
  // Add event listener to theme toggle buttons
  const themeToggles = document.querySelectorAll('.theme-toggle');
  themeToggles.forEach(toggle => {
    toggle.addEventListener('click', toggleTheme);
  });
});

// Toggle between light and dark themes
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  
  // Update theme attribute
  document.documentElement.setAttribute('data-theme', newTheme);
  
  // Save preference to localStorage
  localStorage.setItem('theme', newTheme);
  
  // Update toggle button icon
  updateThemeToggleIcon(newTheme);
}

// Update the theme toggle icon based on current theme
function updateThemeToggleIcon(theme) {
  const themeToggles = document.querySelectorAll('.theme-toggle');
  
  themeToggles.forEach(toggle => {
    // Clear existing content
    toggle.innerHTML = '';
    
    // Add appropriate icon based on theme
    if (theme === 'dark') {
      // Sun icon for dark mode (to switch to light)
      toggle.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41.39.39 1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41.39.39 1.03.39 1.41 0l1.06-1.06z"/>
        </svg>
      `;
    } else {
      // Moon icon for light mode (to switch to dark)
      toggle.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>
        </svg>
      `;
    }
  });
}