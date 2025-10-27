
loadDropdowns(); 


class CustomUserDropdown {
    constructor(dropdownElement) {
        this.dropdownElement = dropdownElement;
        this.listElement = document.getElementById('userDropdownList');
        this.hiddenInput = document.getElementById('selected-user-ids');
        this.selectedUserIds = [];
        this.init();
    }

    init() {
        this.loadUsers();
        this.setupOutsideClickListener();
    }

    async loadUsers() {
        try {
            const response = await fetch('/api/users');
            const users = await response.json();

            if (users.length === 0) {
                this.listElement.innerHTML = `
                    <div style="padding: 2rem; text-align: center; color: #718096;">
                        <i class="fas fa-users" style="font-size: 2rem; opacity: 0.3; margin-bottom: 0.5rem;"></i>
                        <p style="margin: 0;">No team members available</p>
                    </div>
                `;
            } else {
                this.renderUsers(users);
            }
            
            this.setupEventListeners();
        } catch (error) {
            console.error('Error loading users:', error);
            this.listElement.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #e53e3e;">
                    <i class="fas fa-exclamation-circle" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                    <p style="margin: 0;">Failed to load users</p>
                </div>
            `;
        }
    }

    renderUsers(users) {
        this.listElement.innerHTML = users.map(user => `
            <div class="dropdown-item-custom">
                <input 
                    type="checkbox" 
                    id="user-${user.id}" 
                    value="${user.id}"
                    onchange="customUserDropdown.updateSelectedUsers(this)"
                >
                <label for="user-${user.id}">${user.name}</label>
            </div>
        `).join('');
    }

    updateSelectedUsers(checkbox) {
        const userId = checkbox.value;

        if (checkbox.checked) {
            if (!this.selectedUserIds.includes(userId)) {
                this.selectedUserIds.push(userId);
            }
        } else {
            this.selectedUserIds = this.selectedUserIds.filter(id => id !== userId);
        }

        // Update hidden input
        this.hiddenInput.value = this.selectedUserIds.join(',');

        // Update dropdown header
        this.updateDropdownHeader();
    }

    updateDropdownHeader() {
        const headerElement = document.getElementById('dropdown-header-text');
        if (!headerElement) {
            // Fallback to old method if element not found
            const oldHeaderElement = this.dropdownElement.querySelector('.dropdown-header');
            if (this.selectedUserIds.length > 0) {
                oldHeaderElement.innerHTML = `
                    <span>Selected Users (${this.selectedUserIds.length})</span>
                    <span class="dropdown-arrow">▼</span>
                `;
            } else {
                oldHeaderElement.innerHTML = `
                    <span>Select Team Members</span>
                    <span class="dropdown-arrow">▼</span>
                `;
            }
            return;
        }
        
        if (this.selectedUserIds.length > 0) {
            headerElement.textContent = `Selected Users (${this.selectedUserIds.length})`;
        } else {
            headerElement.textContent = 'Select Team Members';
        }
    }
    setupEventListeners() {
       
    }

    setupOutsideClickListener() {
        document.addEventListener('click', (event) => {
            if (!this.dropdownElement.contains(event.target)) {
                this.listElement.classList.remove('show');
                this.listElement.style.display = 'none';
                this.dropdownElement.classList.remove('active');
            }
        });
    }
}

// Global function to toggle dropdown visibility
function toggleDropdown(event) {
    if (event) {
        event.stopPropagation(); // Prevent event bubbling
    }
    
    const dropdownList = document.getElementById('userDropdownList');
    const dropdownElement = document.querySelector('.custom-dropdown');
    const isVisible = dropdownList.classList.contains('show') || dropdownList.style.display === 'block';
    
    if (isVisible) {
        dropdownList.classList.remove('show');
        dropdownList.style.display = 'none';
        dropdownElement.classList.remove('active');
    } else {
        dropdownList.classList.add('show');
        dropdownList.style.display = 'block';
        dropdownElement.classList.add('active');
    }
}

// Close dropdown when clicking on a checkbox (optional - comment out if you want it to stay open)
function closeDropdownAfterSelection() {
    // Uncomment the lines below if you want the dropdown to close after each selection
    // const dropdownList = document.getElementById('userDropdownList');
    // const dropdownElement = document.querySelector('.custom-dropdown');
    // dropdownList.classList.remove('show');
    // dropdownList.style.display = 'none';
    // dropdownElement.classList.remove('active');
}

// Initialize dropdown when page loads
let customUserDropdown;
document.addEventListener('DOMContentLoaded', () => {
    const dropdownElement = document.querySelector('.custom-dropdown');
    customUserDropdown = new CustomUserDropdown(dropdownElement);
});


async function loadDropdowns() {
    try {
        // Fetch Product Owner data
        const response = await fetch('/api/product_owners');
        const productOwners = await response.json();

        const productOwnerSelect = document.getElementById('product-owner-id');
        productOwners.forEach(owner => {
            const option = document.createElement('option');
            option.value = owner.id; 
            option.textContent = owner.name; // Use a meaningful label
            productOwnerSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading dropdown data:', error);
    }
}

async function ScrumMasterDropdown(targetId) {
try {
    // Fetch Scrum Master data
    const response = await fetch('/api/scrum_masters');
    const scrumMasters = await response.json();

    const scrumMasterSelect = document.getElementById(targetId);
    scrumMasterSelect.innerHTML = `<option value="">Select Scrum Master</option>`; // Clear existing options

    scrumMasters.forEach(master => {
        const option = document.createElement('option');
        option.value = master.id; // Use the ID from the database
        option.textContent = master.name; // Use a meaningful label
        scrumMasterSelect.appendChild(option);
    });
    } 
    catch (error) {
        console.error('Error loading Scrum Master data:', error);
    }
}

async function populateAssigneeDropdowns() {
    try {
        // Get selected team member IDs from hidden input
        const selectedUserIds = document.getElementById('selected-user-ids').value;
        
        if (!selectedUserIds || selectedUserIds.trim() === '') {
            console.warn('No team members selected. Please select team members first.');
            return;
        }

        // Fetch all users
        const response = await fetch('/api/users');
        const allUsers = await response.json();

        // Filter to get only selected team members
        const selectedIds = selectedUserIds.split(',').map(id => id.trim());
        const selectedTeamMembers = allUsers.filter(user => selectedIds.includes(user.id.toString()));

        // Find all assignee dropdowns on the page
        const assigneeDropdowns = document.querySelectorAll('.assignee-dropdown');

        // Populate each dropdown with selected team members
        assigneeDropdowns.forEach(dropdown => {
            // Clear existing options except the first "Select Team Member"
            dropdown.innerHTML = '<option value="">Select Team Member</option>';

            // Add selected team members as options
            selectedTeamMembers.forEach(member => {
                const option = document.createElement('option');
                option.value = member.name; // Use name as value
                option.textContent = member.name; // Display name
                dropdown.appendChild(option);
            });
        });

        console.log(`✓ Populated ${assigneeDropdowns.length} assignee dropdowns with ${selectedTeamMembers.length} team members`);
    } catch (error) {
        console.error('Error populating assignee dropdowns:', error);
    }
}


function addSprintFields() {
    const numSprints = parseInt(document.getElementById("num-sprints").value);
    if (isNaN(numSprints) || numSprints < 1) {
        alert("Please enter a valid number of sprints.");
        return;
    }

    const sprintContainer = document.getElementById("sprint-container");
    sprintContainer.innerHTML = ""; // Clear previous content

    for (let i = 1; i <= numSprints; i++) {
        const sprintId = `scrum-master-id-${i}`; // Unique ID for each dropdown

        sprintContainer.innerHTML += `
            <div class="sprint-card">
                <h4>Sprint ${i}</h4>
                <div class="sprint-content">
                    <div class="sprint-fields-grid">
                        <div>
                            <label for="${sprintId}">Scrum Master</label>
                            <select id="${sprintId}" name="scrum_master_id_${i}" class="form-select" required>
                                <option value="">Select Scrum Master</option>
                            </select>
                        </div>

                        <div>
                            <label for="sprint-start-date-${i}">Start Date</label>
                            <input type="date" id="sprint-start-date-${i}" name="sprint_start_date_${i}" class="form-control" required>
                        </div>

                        <div>
                            <label for="sprint-end-date-${i}">End Date</label>
                            <input type="date" id="sprint-end-date-${i}" name="sprint_end_date_${i}" class="form-control" required>
                        </div>

                        <div>
                            <label for="sprint-velocity-${i}">Velocity</label>
                            <input type="number" id="sprint-velocity-${i}" name="sprint_velocity_${i}" min="0" class="form-control" placeholder="Velocity" required>
                        </div>

                        <div>
                            <button type="button" onclick="addUserStoryFields(${i})" class="btn btn-success w-100" style="margin-top: 1.85rem;">
                                <i class="fas fa-plus me-1"></i> Add User Stories
                            </button>
                        </div>
                    </div>

                    <div id="user-stories-${i}"></div>
                </div>
            </div>
        `;

        // Populate the Scrum Master dropdown for this sprint
        ScrumMasterDropdown(sprintId);
    }
}

function addUserStoryFields(sprintNum) {
    // Check if team members are selected
    const selectedUserIds = document.getElementById('selected-user-ids').value;
    if (!selectedUserIds || selectedUserIds.trim() === '') {
        alert("⚠️ Please select team members first from the 'Team Members' dropdown in Basic Information section.");
        return;
    }

    const numStories = prompt(`How many user stories for Sprint ${sprintNum}?`);
    if (isNaN(numStories) || numStories < 1) {
        alert("Please enter a valid number.");
        return;
    }

    const storyContainer = document.getElementById(`user-stories-${sprintNum}`);
    storyContainer.innerHTML = ""; // Clear previous content

    for (let i = 1; i <= numStories; i++) {
        storyContainer.innerHTML += `
            <div class="user-story-section">
                <h5>User Story ${i}</h5>
                
                <div class="row g-3">
                    <div class="col-md-4">
                        <label for="planned-sprint-${sprintNum}-${i}" class="form-label">Planned Sprint</label>
                        <input type="number" id="planned-sprint-${sprintNum}-${i}" name="planned_sprint_${sprintNum}_${i}" min="1" class="form-control" placeholder="Sprint #" required>
                    </div>

                    <div class="col-md-4">
                        <label for="actual-sprint-${sprintNum}-${i}" class="form-label">Actual Sprint</label>
                        <input type="number" id="actual-sprint-${sprintNum}-${i}" name="actual_sprint_${sprintNum}_${i}" min="1" class="form-control" placeholder="Sprint #" required>
                    </div>

                    <div class="col-md-4">
                        <label for="story-points-${sprintNum}-${i}" class="form-label">Story Points</label>
                        <input type="number" id="story-points-${sprintNum}-${i}" name="story_points_${sprintNum}_${i}" min="0" class="form-control" placeholder="Points" required>
                    </div>

                    <div class="col-md-12">
                        <label for="story-desc-${sprintNum}-${i}" class="form-label">Description</label>
                        <textarea id="story-desc-${sprintNum}-${i}" name="story_desc_${sprintNum}_${i}" class="form-control" rows="3" placeholder="As a [user type], I want to [action] so that [benefit]..." required></textarea>
                    </div>

                    <div class="col-md-4">
                        <label for="moscow-${sprintNum}-${i}" class="form-label">MoSCoW Priority</label>
                        <select id="moscow-${sprintNum}-${i}" name="moscow_${sprintNum}_${i}" class="form-select" required>
                            <option value="">Select Priority</option>
                            <option value="Must Have">Must Have</option>
                            <option value="Should Have">Should Have</option>
                            <option value="Could Have">Could Have</option>
                            <option value="Won't Have">Won't Have</option>
                        </select>
                    </div>

                    <div class="col-md-4">
                        <label for="assignee-${sprintNum}-${i}" class="form-label">Assignee</label>
                        <select id="assignee-${sprintNum}-${i}" name="assignee_${sprintNum}_${i}" class="form-select assignee-dropdown" required>
                            <option value="">Select Team Member</option>
                        </select>
                    </div>

                    <div class="col-md-4">
                        <label for="status-${sprintNum}-${i}" class="form-label">Status</label>
                        <select id="status-${sprintNum}-${i}" name="status_${sprintNum}_${i}" class="form-select" required>
                            <option value="">Select Status</option>
                            <option value="Not Started">Not Started</option>
                            <option value="In Progress">In Progress</option>
                            <option value="Completed">Completed</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Populate assignee dropdowns with selected team members
    populateAssigneeDropdowns();
}

function submitForm1() {
    // Collect basic form data
    const form = document.getElementById("project-form");
    const formData = new FormData(form);
    const jsonData = {};

    // Convert FormData to a plain object
    for (let [key, value] of formData.entries()) {
        jsonData[key] = value;
    }

    // Add selected user IDs
    const selectedUserIds = document.getElementById('selected-user-ids').value;
    jsonData['selected_user_ids'] = selectedUserIds;

    // Handle Sprint Data
    jsonData.sprints = [];
    const numSprints = parseInt(document.getElementById("num-sprints").value);

    for (let i = 1; i <= numSprints; i++) {
        const sprint = {
            start_date: document.getElementById(`sprint-start-date-${i}`)?.value,
            end_date: document.getElementById(`sprint-end-date-${i}`)?.value,
            scrum_master_id: document.getElementById(`scrum-master-id-${i}`)?.value,
            velocity: document.getElementById(`sprint-velocity-${i}`)?.value,
            user_stories: []
        };

        // Collect user stories for this sprint
        const storyContainer = document.getElementById(`user-stories-${i}`);
        if (storyContainer) {
            const userStorySections = storyContainer.querySelectorAll(".user-story-section");
            
            userStorySections.forEach((section, index) => {
                const story = {
                    planned_sprint: section.querySelector(`#planned-sprint-${i}-${index + 1}`)?.value,
                    actual_sprint: section.querySelector(`#actual-sprint-${i}-${index + 1}`)?.value,
                    description: section.querySelector(`#story-desc-${i}-${index + 1}`)?.value,
                    story_points: section.querySelector(`#story-points-${i}-${index + 1}`)?.value,
                    moscow: section.querySelector(`#moscow-${i}-${index + 1}`)?.value,
                    assignee: section.querySelector(`#assignee-${i}-${index + 1}`)?.value,
                    status: section.querySelector(`#status-${i}-${index + 1}`)?.value
                };
                sprint.user_stories.push(story);
            });
        }

        jsonData.sprints.push(sprint);
    }

    // Log the data for debugging
    console.log('Submission Data:', jsonData);

    // Send data to server
    fetch("/submit", {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        body: JSON.stringify(jsonData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Handle successful submission
        alert(data.message || "Project submitted successfully");
        // Optional: reset form or redirect
        form.reset();
        //document.getElementById('form-container').style.display = 'block';
        window.location.href = document.referrer;
    })
    .catch(error => {
        // Handle errors
        console.error("Error submitting form:", error);
        alert("Failed to submit project. Please try again.");
    });
}