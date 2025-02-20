document.addEventListener('DOMContentLoaded', function() {
  const modal = document.getElementById('infoModal');
  const modalAgreeBtn = document.getElementById('modalAgreeBtn');
  const acceptPrivacy = document.getElementById('acceptPrivacy');
  const generateForm = document.getElementById('generate-app-form');
  const loadingOverlay = document.getElementById('loading-overlay');
  const closeButton = document.querySelector('.close-button');

  // Function to open the modal by adding the "active" class
  function openModal() {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent page scrolling
  }

  // Function to close the modal by removing the "active" class
  function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = 'auto'; // Restore page scrolling
  }

  // Open the modal immediately on page load
  openModal();

  // Close modal when the close button (×) is clicked.
  closeButton.addEventListener('click', closeModal);

  // Close modal when clicking outside the modal content.
  window.addEventListener('click', function(e) {
    if (e.target === modal) {
      closeModal();
    }
  });

  // Enable the modal's "Agree" button only if the privacy checkbox is checked.
  acceptPrivacy.addEventListener('change', function() {
    if (this.checked) {
      modalAgreeBtn.removeAttribute('disabled');
    } else {
      modalAgreeBtn.setAttribute('disabled', 'true');
    }
  });

  // When the modal's agree button is clicked:
  // Close the modal, show the loading overlay, and submit the form.
  modalAgreeBtn.addEventListener('click', function() {
    closeModal();
    // Show the loading overlay immediately
    loadingOverlay.classList.remove('hidden');
    // Submit the form – using requestSubmit if available; fallback to submit()
    if (typeof generateForm.requestSubmit === 'function') {
      generateForm.requestSubmit();
    } else {
      generateForm.submit();
    }
  });
});
