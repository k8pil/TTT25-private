// Theme toggle functionality
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');
  
  // Define theme colors
  const themes = {
    light: {
      '--primary-color': '#6B6054', // Walnut brown
      '--secondary-color': '#A1B0AB', // Ash gray
      '--accent-color': '#C3DAC3', // Tea green
      '--light-color': '#D5ECD4', // Nyanza
      '--dark-color': '#333333',
      '--text-color': '#444444',
      '--background-color': '#D5ECD4',
      '--card-bg-color': 'rgba(255, 255, 255, 0.7)',
      '--border-color': 'rgba(107, 96, 84, 0.3)',
      '--shadow-color': 'rgba(107, 96, 84, 0.2)',
      '--hover-color': 'rgba(107, 96, 84, 0.1)'
    },
    dark: {
      '--primary-color': '#D5ECD4', // Nyanza (inverted)
      '--secondary-color': '#C3DAC3', // Tea green (inverted)
      '--accent-color': '#A1B0AB', // Ash gray (inverted)
      '--light-color': '#6B6054', // Walnut brown (inverted)
      '--dark-color': '#EEEEEE',
      '--text-color': '#E0E0E0',
      '--background-color': '#333333',
      '--card-bg-color': 'rgba(51, 51, 51, 0.8)',
      '--border-color': 'rgba(213, 236, 212, 0.3)',
      '--shadow-color': 'rgba(0, 0, 0, 0.4)',
      '--hover-color': 'rgba(213, 236, 212, 0.1)'
    }
  };
  
  // Check system preference and localStorage
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const savedTheme = localStorage.getItem('theme');
  let currentTheme = savedTheme || (prefersDark ? 'dark' : 'light');
  
  // Apply theme on page load
  applyTheme(currentTheme);

  // Toggle theme when button is clicked
  themeToggle?.addEventListener('click', () => {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyTheme(currentTheme);
    localStorage.setItem('theme', currentTheme);
  });
  
  // Function to apply theme
  function applyTheme(theme) {
    // Apply CSS variables
    const root = document.documentElement;
    
    for (const [property, value] of Object.entries(themes[theme])) {
      root.style.setProperty(property, value);
    }
    
    // Update classes on body
    if (theme === 'dark') {
      document.body.classList.add('dark-mode');
      document.body.classList.remove('light-mode');
      themeIcon?.classList.replace('fa-moon', 'fa-sun');
    } else {
      document.body.classList.add('light-mode');
      document.body.classList.remove('dark-mode');
      themeIcon?.classList.replace('fa-sun', 'fa-moon');
    }
  }
  
  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('theme')) {
      const newTheme = e.matches ? 'dark' : 'light';
      applyTheme(newTheme);
      currentTheme = newTheme;
    }
  });
});