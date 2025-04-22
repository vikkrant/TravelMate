document.addEventListener('DOMContentLoaded', function() {
    // For proper progress tracking display
    let updateProgressDisplay = function() {
        // Update category counters
        document.querySelectorAll('.accordion-item').forEach(function(category) {
            const categoryId = category.querySelector('.accordion-header').id;
            const checkboxes = category.querySelectorAll('.toggle-packed');
            const totalItems = checkboxes.length;
            let packedItems = 0;
            
            checkboxes.forEach(function(checkbox) {
                if (checkbox.checked) {
                    packedItems++;
                }
            });
            
            // Update the badge in the header
            const badge = category.querySelector('.badge');
            if (badge) {
                badge.textContent = `${packedItems}/${totalItems}`;
                if (packedItems === totalItems && totalItems > 0) {
                    badge.classList.remove('bg-primary');
                    badge.classList.add('bg-success');
                } else {
                    badge.classList.remove('bg-success');
                    badge.classList.add('bg-primary');
                }
            }
        });
        
        // Update overall progress
        const allCheckboxes = document.querySelectorAll('.toggle-packed');
        const totalItems = allCheckboxes.length;
        let packedItems = 0;
        
        allCheckboxes.forEach(function(checkbox) {
            if (checkbox.checked) {
                packedItems++;
            }
        });
        
        // Update main badge and progress bar
        const progressBadge = document.querySelector('.card-body .badge');
        const progressBar = document.querySelector('.progress-bar');
        
        if (progressBadge && progressBar) {
            progressBadge.textContent = `${packedItems}/${totalItems} items packed`;
            
            if (packedItems === totalItems && totalItems > 0) {
                progressBadge.classList.remove('bg-primary');
                progressBadge.classList.add('bg-success');
                progressBar.classList.remove('bg-primary');
                progressBar.classList.add('bg-success');
            } else {
                progressBadge.classList.remove('bg-success');
                progressBadge.classList.add('bg-primary');
                progressBar.classList.remove('bg-success');
                progressBar.classList.add('bg-primary');
            }
            
            const percentage = totalItems > 0 ? (packedItems / totalItems) * 100 : 0;
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }
    };
    
    // Make entire item row clickable
    document.querySelectorAll('.item-row').forEach(function(row) {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function(event) {
            // Prevent clicking if we're on the delete button
            if (event.target.closest('.delete-btn') || event.target.closest('form')) {
                return;
            }
            
            // Find the checkbox within this row
            const checkbox = this.querySelector('.toggle-packed');
            
            // Toggle the checkbox
            checkbox.checked = !checkbox.checked;
            
            // Get data attributes
            const tripId = this.dataset.tripId;
            const itemId = this.dataset.itemId;
            const label = this.querySelector('.form-check-label');
            
            // Send the toggle request
            fetch(`/trips/packing-list/${tripId}/toggle/${itemId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
            })
            .then(response => response.json())
            .then(data => {
                // Update the UI immediately
                checkbox.checked = data.is_packed;
                
                if (data.is_packed) {
                    label.classList.add('text-decoration-line-through', 'text-muted');
                } else {
                    label.classList.remove('text-decoration-line-through', 'text-muted');
                }
                
                // Update progress tracking without page reload
                updateProgressDisplay();
            })
            .catch(error => {
                console.error('Error:', error);
                checkbox.checked = !checkbox.checked;
            });
        });
    });
    
    // Direct checkbox click handler
    document.querySelectorAll('.toggle-packed').forEach(function(checkbox) {
        // Prevent the click from bubbling up to the row
        checkbox.addEventListener('click', function(event) {
            event.stopPropagation();
            
            const tripId = this.dataset.tripId;
            const itemId = this.dataset.itemId;
            const label = this.parentElement.querySelector('.form-check-label');
            
            fetch(`/trips/packing-list/${tripId}/toggle/${itemId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
            })
            .then(response => response.json())
            .then(data => {
                // Update the UI immediately
                this.checked = data.is_packed;
                
                if (data.is_packed) {
                    label.classList.add('text-decoration-line-through', 'text-muted');
                } else {
                    label.classList.remove('text-decoration-line-through', 'text-muted');
                }
                
                // Update progress tracking without page reload
                updateProgressDisplay();
            })
            .catch(error => {
                console.error('Error:', error);
                this.checked = !this.checked;
            });
        });
    });
    
    // Initialize progress display on page load
    updateProgressDisplay();
}); 