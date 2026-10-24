/**
 * Sidebar Navigation & Admin Session Controller
 */

function hexToHslOrDarken(hex, percent) {
  try {
    let num = parseInt(hex.replace("#", ""), 16);
    let amt = Math.round(2.55 * percent);
    let R = (num >> 16) + amt;
    let G = (num >> 8 & 0x00FF) + amt;
    let B = (num & 0x0000FF) + amt;
    return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
      (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
      (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
  } catch (e) {
    return hex;
  }
}

function applyFirmBranding(data) {
  if (!data) return;
  const brandName = data.firm_name || "CRM Follow-up";
  const brandLogo = data.firm_logo || "";
  const themeColor = data.theme_color || "";

  // Apply Theme Accent Colors
  if (themeColor && /^#[0-9A-Fa-f]{6}$/.test(themeColor)) {
    document.documentElement.style.setProperty('--primary', themeColor);
    document.documentElement.style.setProperty('--primary-hover', hexToHslOrDarken(themeColor, -15));
    document.documentElement.style.setProperty('--bg-sidebar-active', themeColor);
    document.documentElement.style.setProperty('--primary-subtle', themeColor + "18");
  }

  // Update brand name
  const brandSpan = document.querySelector(".brand-link span");
  if (brandSpan && brandName) {
    brandSpan.textContent = brandName;
  }

  // Update logo icon / image
  const brandLink = document.querySelector(".brand-link");
  if (brandLink) {
    let logoImg = brandLink.querySelector(".brand-logo-img");
    const brandIcon = brandLink.querySelector(".brand-logo-icon");

    if (brandLogo) {
      if (!logoImg) {
        logoImg = document.createElement("img");
        logoImg.className = "brand-logo-img";
        logoImg.style.cssText = "height:34px; max-width:44px; object-fit:contain; border-radius:6px; margin-right:8px; background:rgba(255,255,255,0.06); padding:2px;";
        if (brandIcon) {
          brandIcon.replaceWith(logoImg);
        } else {
          brandLink.prepend(logoImg);
        }
      }
      logoImg.src = brandLogo;
      logoImg.alt = brandName;
    } else {
      if (logoImg) {
        const iconDiv = document.createElement("div");
        iconDiv.className = "brand-logo-icon";
        iconDiv.textContent = brandName ? brandName[0].toUpperCase() : "C";
        logoImg.replaceWith(iconDiv);
      } else if (brandIcon && brandName) {
        brandIcon.textContent = brandName[0].toUpperCase();
      }
    }
  }

  // Update document title suffix
  if (document.title && brandName) {
    const parts = document.title.split(" - ");
    if (parts.length > 0) {
      document.title = `${parts[0]} - ${brandName}`;
    }
  }

  // Optional: Set favicon if logo exists
  if (brandLogo) {
    let favicon = document.querySelector("link[rel*='icon']");
    if (!favicon) {
      favicon = document.createElement("link");
      favicon.rel = "shortcut icon";
      document.head.appendChild(favicon);
    }
    favicon.href = brandLogo;
  }
}

// Global hook for other scripts to refresh branding
window.refreshFirmBranding = async function() {
  try {
    const apiBase = window.API_BASE || (window.location.pathname.startsWith('/excel-crm') ? '/excel-crm' : '');
    const res = await fetch(`${apiBase}/api/settings/public`);
    const firmData = await res.json();
    if (firmData && firmData.firm_name) {
      localStorage.setItem("crm_firm_branding", JSON.stringify(firmData));
      applyFirmBranding(firmData);
    }
  } catch (err) {
    console.error("Failed to refresh firm branding:", err);
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  // 0. Dynamic subpath support for links
  const apiBase = window.API_BASE || (window.location.pathname.startsWith('/excel-crm') ? '/excel-crm' : '');
  if (apiBase) {
    document.querySelectorAll("a[href^='/']").forEach(a => {
      const href = a.getAttribute("href");
      if (!href.startsWith(apiBase) && !href.startsWith("//")) {
        a.setAttribute("href", apiBase + href);
      }
    });
  }

  // 1. Instant cached branding load
  try {
    const cached = JSON.parse(localStorage.getItem("crm_firm_branding") || "null");
    if (cached) applyFirmBranding(cached);
  } catch (err) {}

  // 2. Fetch fresh branding from backend
  window.refreshFirmBranding();

  // Mobile drawer toggle
  const toggleBtn = document.querySelector(".mobile-toggle");
  const sidebar = document.querySelector(".app-sidebar");
  const backdrop = document.querySelector(".sidebar-backdrop");

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      if (backdrop) backdrop.classList.toggle("show");
    });
  }

  if (backdrop && sidebar) {
    backdrop.addEventListener("click", () => {
      sidebar.classList.remove("open");
      backdrop.classList.remove("show");
    });
  }

  // Active link detection
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".nav-item");
  navLinks.forEach(link => {
    const href = link.getAttribute("href");
    if (href && (currentPath === href || (currentPath === "/" && href.includes("index.html")) || currentPath.endsWith(href))) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Fetch current user and update sidebar badge counts
  if (window.api && !currentPath.includes("login")) {
    try {
      const user = await window.api.get("/api/auth/me");
      const nameEl = document.querySelector(".admin-name");
      const avatarEl = document.querySelector(".admin-avatar");
      if (nameEl && user) nameEl.textContent = user.full_name || user.email;
      if (avatarEl && user) avatarEl.textContent = (user.full_name || user.email)[0].toUpperCase();

      // Update sidebar counter badges
      const stats = await window.api.get("/api/dashboard/stats");
      const todayBadge = document.getElementById("sidebar-badge-today");
      const overdueBadge = document.getElementById("sidebar-badge-overdue");
      const dueSoonBadge = document.getElementById("sidebar-badge-due-soon");

      if (todayBadge && stats.today_followups_count > 0) {
        todayBadge.textContent = stats.today_followups_count;
        todayBadge.style.display = "inline-block";
      }
      if (overdueBadge && stats.overdue_followups_count > 0) {
        overdueBadge.textContent = stats.overdue_followups_count;
        overdueBadge.style.display = "inline-block";
      }
      if (dueSoonBadge && stats.due_soon_followups_count > 0) {
        dueSoonBadge.textContent = stats.due_soon_followups_count;
        dueSoonBadge.style.display = "inline-block";
      }
      if (stats.reminder_advance_days) {
        document.querySelectorAll(".advance-days-lbl").forEach(el => {
          el.textContent = stats.reminder_advance_days;
        });
      }
    } catch (e) {
      console.warn("Could not load user or badge stats:", e);
    }
  }

  // Logout handler
  const logoutBtn = document.querySelector(".logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      if (confirm("Are you sure you want to log out?")) {
        try {
          await window.api.post("/api/auth/logout");
        } catch (e) {
          // ignore
        }
        window.api.setToken(null);
        window.location.href = `${apiBase}/login.html`;
      }
    });
  }
});
