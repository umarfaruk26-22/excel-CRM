/**
 * Reports & Visual Analytics Controller
 */

let outcomesChart = null;
let growthChart = null;

async function loadReports() {
  try {
    const exportBtn = document.querySelector('a[href*="/api/customers/export"]');
    if (exportBtn) {
      exportBtn.href = `${window.API_BASE || ''}/api/customers/export`;
    }

    // 1. KPI Summary
    const stats = await window.api.get("/api/reports/summary");
    document.getElementById("kpi-customers").textContent = stats.total_customers.toLocaleString();
    document.getElementById("kpi-calls").textContent = stats.completed_calls_count.toLocaleString();
    document.getElementById("kpi-pending").textContent = stats.pending_followups_count.toLocaleString();
    document.getElementById("kpi-overdue").textContent = stats.overdue_followups_count.toLocaleString();

    // 2. Call Outcomes Doughnut Chart
    const outcomesData = await window.api.get("/api/reports/outcomes");
    const outcomeLabels = outcomesData.map(o => o.outcome);
    const outcomeCounts = outcomesData.map(o => o.count);

    const outcomesCanvas = document.getElementById("outcomesChart");
    if (outcomesChart) outcomesChart.destroy();

    outcomesChart = new Chart(outcomesCanvas, {
      type: 'doughnut',
      data: {
        labels: outcomeLabels.length > 0 ? outcomeLabels : ["No calls logged"],
        datasets: [{
          data: outcomeCounts.length > 0 ? outcomeCounts : [1],
          backgroundColor: [
            "#2563eb", "#10b981", "#f59e0b", "#ef4444", 
            "#8b5cf6", "#ec4899", "#06b6d4", "#64748b"
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 12 } } }
        }
      }
    });

    // 3. Customer Growth Bar Chart
    const growthData = await window.api.get("/api/reports/growth");
    const growthLabels = growthData.map(g => g.label);
    const growthCounts = growthData.map(g => g.count);

    const growthCanvas = document.getElementById("growthChart");
    if (growthChart) growthChart.destroy();

    growthChart = new Chart(growthCanvas, {
      type: 'bar',
      data: {
        labels: growthLabels.length > 0 ? growthLabels : ["Current Month"],
        datasets: [{
          label: 'New Customers',
          data: growthCounts.length > 0 ? growthCounts : [stats.total_customers],
          backgroundColor: '#2563eb',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });

  } catch (err) {
    showToast(err.message || "Failed to load reports", "danger");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadReports();
});
