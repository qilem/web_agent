document.addEventListener('DOMContentLoaded', () => {
  const pollQuestionEl = document.getElementById('poll-question');
  const usernameInput = document.getElementById('username');
  const usernameErrorEl = document.getElementById('username-error');
  const optionsContainer = document.getElementById('options-container');
  const resultsContainer = document.getElementById('results-container');
  const messageArea = document.getElementById('message-area');

  const USERNAME_KEY = 'vote_username';
  const USERNAME_REGEX = /^[a-z0-9_]{3,20}$/;

  // Load username from localStorage on startup
  const savedUsername = localStorage.getItem(USERNAME_KEY) || '';
  usernameInput.value = savedUsername;

  function getUsername() {
    return (usernameInput.value || '').trim().toLowerCase();
  }

  function isUsernameValid(username) {
    return USERNAME_REGEX.test(username);
  }

  function renderPoll(data) {
    const { poll, options, me } = data;

    pollQuestionEl.textContent = poll.question;

    // Clear previous state
    optionsContainer.innerHTML = '';
    resultsContainer.innerHTML = '';
    messageArea.textContent = '';
    usernameErrorEl.textContent = '';

    options.forEach(option => {
      // Render option button
      const button = document.createElement('button');
      button.className = 'option-button';
      button.textContent = option.label;
      button.dataset.optionId = option.id;
      optionsContainer.appendChild(button);

      // Render result line
      const resultItem = document.createElement('div');
      resultItem.className = 'result-item';
      resultItem.innerHTML = `<span>${option.label}</span><strong>${option.count}</strong>`;
      resultsContainer.appendChild(resultItem);
    });

    if (me.hasVoted) {
      const votedOption = options.find(opt => opt.id === me.optionId);
      if (votedOption) {
        messageArea.textContent = `You voted for: ${votedOption.label}`;
      }
      // Disable all buttons
      document.querySelectorAll('.option-button').forEach(btn => {
        btn.disabled = true;
      });
    }
  }

  async function loadPoll() {
    const username = getUsername();
    const url = `/api/poll?username=${encodeURIComponent(username)}`;

    try {
      const response = await fetch(url);
      const result = await response.json();
      if (result.ok) {
        renderPoll(result.data);
      } else {
        messageArea.textContent = `Error: ${result.error}`;
      }
    } catch (error) {
      messageArea.textContent = 'Failed to load poll data.';
      console.error('Fetch error:', error);
    }
  }

  async function handleVote(optionId) {
    const username = getUsername();

    if (!isUsernameValid(username)) {
      usernameErrorEl.textContent = 'Invalid username format.';
      return;
    }
    usernameErrorEl.textContent = '';

    try {
      const response = await fetch('/api/vote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, optionId }),
      });

      const result = await response.json();

      if (response.ok) {
        loadPoll(); // Refresh poll data to show new counts and disable UI
      } else if (response.status === 409) {
        messageArea.textContent = 'You have already voted in this poll.';
        loadPoll(); // Still refresh to disable UI
      } else {
        messageArea.textContent = `Error: ${result.error}`;
      }
    } catch (error) {
      messageArea.textContent = 'An error occurred while voting.';
      console.error('Vote error:', error);
    }
  }

  // Event Listeners
  usernameInput.addEventListener('input', () => {
    const username = getUsername();
    localStorage.setItem(USERNAME_KEY, username);
    if (isUsernameValid(username) || username === '') {
        usernameErrorEl.textContent = '';
    }
  });

  optionsContainer.addEventListener('click', (e) => {
    if (e.target.matches('.option-button')) {
      const optionId = parseInt(e.target.dataset.optionId, 10);
      handleVote(optionId);
    }
  });

  // Initial load
  loadPoll();
});
