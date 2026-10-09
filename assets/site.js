// Newsletter form: posts the email to /subscribe.php (PHP + SQLite on the same server).
(function () {
  var forms = document.querySelectorAll('form.notify');
  Array.prototype.forEach.call(forms, function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = form.querySelector('input[type="email"]');
      var button = form.querySelector('button');
      var note = form.querySelector('.form-note');
      var email = (input.value || '').trim();
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        note.textContent = 'That email looks off. Mind checking it?';
        return;
      }
      button.disabled = true;
      note.textContent = 'Saving…';
      fetch(form.getAttribute('data-endpoint'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      })
        .then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (r) {
          if (r.ok && r.data.ok) {
            note.textContent = 'Thank you. You are on the list.';
            input.value = '';
          } else if (r.data && r.data.error === 'invalid_email') {
            note.textContent = 'That email looks off. Mind checking it?';
          } else {
            note.textContent = 'Something went wrong. Please try again in a moment.';
          }
        })
        .catch(function () {
          note.textContent = 'Could not reach the server. Please try again shortly.';
        })
        .then(function () { button.disabled = false; });
    });
  });
})();
