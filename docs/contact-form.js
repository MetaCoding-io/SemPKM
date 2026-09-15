(function () {
  'use strict';

  document.querySelectorAll('form[data-formspree]').forEach(function (form) {
    form.addEventListener('submit', async function (event) {
      if (!window.fetch) return;

      event.preventDefault();

      var button = form.querySelector('[type="submit"]');
      var status = form.querySelector('[data-form-status]');
      var originalLabel = button ? button.textContent : '';

      if (button) {
        button.disabled = true;
        button.textContent = 'Sending…';
      }
      if (status) {
        status.className = 'contact-form-status';
        status.textContent = 'Sending your message…';
      }
      form.classList.add('is-submitting');

      try {
        var response = await fetch(form.action, {
          method: form.method,
          body: new FormData(form),
          headers: { Accept: 'application/json' }
        });

        if (!response.ok) {
          var payload = await response.json().catch(function () { return {}; });
          var message = payload.errors && payload.errors.length
            ? payload.errors.map(function (error) { return error.message; }).join(' ')
            : 'Something went wrong. Please try again.';
          throw new Error(message);
        }

        form.reset();
        if (status) {
          status.className = 'contact-form-status is-success';
          status.textContent = 'Thanks — your message is on its way. I’ll follow up by email.';
        }
      } catch (error) {
        if (status) {
          status.className = 'contact-form-status is-error';
          status.textContent = error.message || 'Something went wrong. Please try again.';
        }
      } finally {
        form.classList.remove('is-submitting');
        if (button) {
          button.disabled = false;
          button.textContent = originalLabel;
        }
      }
    });
  });
})();
