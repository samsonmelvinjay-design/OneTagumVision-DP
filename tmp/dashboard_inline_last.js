
document.addEventListener('DOMContentLoaded', function() {
  // Login Success Modal
  
  
  if (typeof window.engineerModalSetup === 'undefined') {
    window.engineerModalSetup = true;
    // Engineer modal logic
    const engineerProjectsModal = document.getElementById('engineer-projects-modal');
    const closeEngineerProjectsModal = document.getElementById('close-engineer-projects-modal');
    const engineerModalTitle = document.getElementById('engineer-modal-title');
    const engineerModalProjectList = document.getElementById('engineer-modal-project-list');
    const engineerModalGraph = document.getElementById('engineer-modal-graph');
    const engineerAvatar = document.getElementById('engineer-avatar');
    let engineerChart = null;

    window.showEngineerProjectsModal = function(engineer) {
      if (!engineerModalTitle || !engineerAvatar || !engineerProjectsModal || !engineerModalProjectList || !engineerModalGraph) {
        console.error("Engineer modal elements not found in DOM!");
        return;
      }
      engineerModalTitle.textContent = `${engineer.full_name || engineer.username}'s Projects`;
      const initials = (engineer.full_name || engineer.username).split(' ').map(n => n[0]).join('').toUpperCase();
      engineerAvatar.textContent = initials;
      engineerProjectsModal.classList.remove('hidden');
      fetch(`/api/engineer-projects/${engineer.id}/`)
        .then(res => res.json())
        .then(data => {
          const projects = data.projects || [];
          engineerModalProjectList.innerHTML = '';
          if (projects.length > 0) {
            const projectsByStatus = projects.reduce((acc, project) => {
              const status = project.status || 'Unknown';
              if (!acc[status]) acc[status] = [];
              acc[status].push(project);
              return acc;
            }, {});
            const statusOrder = ['ongoing', 'in_progress', 'planned', 'pending', 'completed', 'delayed', 'cancelled', 'Unknown'];
            let projectsHtml = '';
            statusOrder.forEach(status => {
              const projectsInStatus = projectsByStatus[status];
              if (projectsInStatus && projectsInStatus.length > 0) {
                const statusDisplay = status.replace('_', ' ').charAt(0).toUpperCase() + status.replace('_', ' ').slice(1);
                projectsHtml += `
                  <div class="bg-white rounded-lg shadow px-4 py-3 border border-gray-200 flex items-center justify-between mb-3 mt-2">
                    <div class="text-lg font-semibold text-blue-900">${statusDisplay}</div>
                    <span class="text-lg font-bold text-gray-700">${projectsInStatus.length}</span>
                  </div>
                `;
              }
            });
            engineerModalProjectList.innerHTML = projectsHtml;
          } else {
            engineerModalProjectList.innerHTML = `
              <div class="flex flex-col items-center py-8">
                <svg class="w-16 h-16 text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 8v4l3 3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <div class="text-gray-500">No projects assigned.</div>
              </div>
            `;
          }
          const statusCounts = data.status_counts || {};
          const statuses = Object.keys(statusCounts);
          const counts = statuses.map(s => statusCounts[s]);
          if (engineerChart) engineerChart.destroy();
          engineerChart = new Chart(engineerModalGraph, {
            type: 'bar',
            data: {
              labels: statuses,
              datasets: [{
                label: 'Projects by Status',
                data: counts,
                backgroundColor: ['#3B82F6', '#F59E42', '#10B981', '#FBBF24'],
              }]
            },
            options: {
              responsive: true,
              plugins: { legend: { display: false } },
              scales: { y: { beginAtZero: true, precision: 0 } }
            }
          });
          // Update total and delayed projects
          document.getElementById('total-projects').textContent = projects.length;
          const delayedCount = (projectsByStatus['delayed'] || []).length;
          document.getElementById('delayed-projects').textContent = delayedCount;
        });
    };

    if (closeEngineerProjectsModal) {
      closeEngineerProjectsModal.addEventListener('click', () => {
        engineerProjectsModal.classList.add('hidden');
        if (engineerChart) engineerChart.destroy();
      });
    }
  }

  // Engineers Dropdown logic
  const engineersDropdownButton = document.querySelector(
    '.flex.items-center.gap-2.py-2.px-4.rounded.hover\\:bg-gray-800.w-full.text-left.focus\\:outline-none'
  );
  const engineersDropdownContent = document.getElementById('engineers-dropdown-content');
  let engineersLoaded = false;

  if (engineersDropdownButton && engineersDropdownContent) {
    engineersDropdownButton.addEventListener('click', function(e) {
      e.stopPropagation();
      engineersDropdownContent.classList.toggle('hidden');
      if (!engineersLoaded) {
        fetch('/projeng/api/engineers/')
          .then(res => res.json())
          .then(engineers => {
            engineersDropdownContent.innerHTML = '';
            if (engineers.length > 0) {
              engineers.forEach(engineer => {
                if (engineer.username === "headeng") return; // Skip headeng
                const link = document.createElement('a');
                link.href = 'javascript:void(0);';
                link.className = 'block px-4 py-2 text-sm text-green-50 hover:bg-green-800';
                link.textContent = engineer.full_name || engineer.username;
                link.onclick = () => window.showEngineerProjectsModal(engineer);
                engineersDropdownContent.appendChild(link);
              });
            } else {
              engineersDropdownContent.innerHTML = '<div class="px-4 py-2 text-green-100">No engineers found.</div>';
            }
            engineersLoaded = true;
          });
      }
    });
    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
      if (!engineersDropdownContent.classList.contains('hidden')) {
        engineersDropdownContent.classList.add('hidden');
      }
    });
    // Prevent closing when clicking inside
    engineersDropdownContent.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  }

  var bell = document.getElementById('notification-bell');
  var panel = document.getElementById('notification-panel');
  var closeBtn = document.getElementById('close-notification-panel');
  if (bell && panel) {
    bell.addEventListener('click', function(e) {
      e.stopPropagation();
      panel.classList.toggle('hidden');
    });
    if (closeBtn) {
      closeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        panel.classList.add('hidden');
      });
    }
    document.addEventListener('click', function() {
      panel.classList.add('hidden');
    });
    panel.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  }
});
