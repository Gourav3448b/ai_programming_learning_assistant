(function () {
  const menuButton = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');

  if (menuButton && sidebar) {
    menuButton.addEventListener('click', () => sidebar.classList.toggle('sidebar-open'));
    document.addEventListener('click', (event) => {
      if (window.innerWidth <= 860 && sidebar.classList.contains('sidebar-open') &&
          !sidebar.contains(event.target) && !menuButton.contains(event.target)) {
        sidebar.classList.remove('sidebar-open');
      }
    });
  }

  document.querySelectorAll('.flash-close').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });

  document.querySelectorAll('form[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll('[data-copy-target]').forEach((button) => {
    button.addEventListener('click', async () => {
      const target = document.querySelector(button.dataset.copyTarget);
      if (!target) return;
      try {
        await navigator.clipboard.writeText(target.innerText);
        const original = button.innerText;
        button.innerText = 'Copied';
        window.setTimeout(() => { button.innerText = original; }, 1400);
      } catch (_error) {
        button.innerText = 'Copy unavailable';
      }
    });
  });

  const chatMessages = document.getElementById('chat-messages');
  if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;

  const chatInput = document.getElementById('question');
  if (chatInput) {
    chatInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        chatInput.form.requestSubmit();
      }
    });
    document.querySelectorAll('.chat-chips span').forEach((chip) => {
      chip.addEventListener('click', () => {
        chatInput.value = chip.textContent === 'Explain recursion'
          ? 'Explain recursion with a simple example.'
          : chip.textContent === 'Help with a bug'
            ? 'Help me debug this code. What information should I share?'
            : 'Give me a DSA practice problem and a small hint.';
        chatInput.focus();
      });
    });
  }
})();
