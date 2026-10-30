/* ========== Config ========== */
const FORM_ENDPOINT = "/subscribe/";
/* ============================ */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const SUCCESS_MSG =
  "Дякуємо! Ми повідомимо тебе першою, щойно бокси стануть доступними.";
const INVALID_MSG = "Будь ласка, введіть коректний e-mail";
const FAIL_MSG = "Не вдалося надіслати. Спробуйте пізніше.";

const form = document.getElementById("waitlist-form");
const emailInput = document.getElementById("email");
const statusEl = document.getElementById("form-status");
const submitBtn = form.querySelector('button[type="submit"]');
const hero = document.querySelector(".hero");
const video = document.querySelector(".hero__video");

function getCookie(name) {
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : "";
}

function getCsrfToken() {
  const input = form.querySelector('input[name="csrfmiddlewaretoken"]');
  if (input && input.value) return input.value;
  return getCookie("csrftoken");
}

function setStatus(message, isError) {
  statusEl.textContent = message;
  statusEl.classList.toggle("hero__status--error", Boolean(isError));
}

function clearStatus() {
  statusEl.textContent = "";
  statusEl.classList.remove("hero__status--error");
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function handleReducedMotion() {
  if (!prefersReducedMotion() || !video) return;

  hero.classList.add("hero--reduced-motion");
  video.pause();
  video.remove();
}

function initVideo() {
  if (!video || prefersReducedMotion()) return;

  const webm = video.getAttribute("data-webm");
  const mp4 = video.getAttribute("data-mp4");

  if (webm) {
    const sourceWebm = document.createElement("source");
    sourceWebm.src = webm;
    sourceWebm.type = "video/webm";
    video.appendChild(sourceWebm);
  }

  if (mp4) {
    const sourceMp4 = document.createElement("source");
    sourceMp4.src = mp4;
    sourceMp4.type = "video/mp4";
    video.appendChild(sourceMp4);
  }

  video.load();

  const fail = () => {
    hero.classList.add("hero--no-video");
    video.pause();
  };

  video.addEventListener("error", fail);

  const playPromise = video.play();
  if (playPromise && typeof playPromise.catch === "function") {
    playPromise.catch(fail);
  }
}

async function onSubmit(event) {
  event.preventDefault();
  clearStatus();

  const email = emailInput.value.trim();
  emailInput.value = email;

  const valid = EMAIL_RE.test(email) && emailInput.checkValidity();

  if (!valid) {
    emailInput.setAttribute("aria-invalid", "true");
    setStatus(INVALID_MSG, true);
    emailInput.focus();
    return;
  }

  emailInput.setAttribute("aria-invalid", "false");
  submitBtn.disabled = true;

  const endpoint = form.getAttribute("action") || FORM_ENDPOINT;
  const websiteInput = form.querySelector('input[name="website"]');
  const payload = {
    email,
    website: websiteInput ? websiteInput.value : "",
  };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });

    let data = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (res.status === 429) {
      setStatus((data && data.message) || FAIL_MSG, true);
      emailInput.focus();
      return;
    }

    if (!res.ok) {
      setStatus((data && data.message) || FAIL_MSG, true);
      emailInput.focus();
      return;
    }

    setStatus((data && data.message) || SUCCESS_MSG, false);
    form.reset();
  } catch {
    setStatus(FAIL_MSG, true);
    emailInput.focus();
  } finally {
    submitBtn.disabled = false;
  }
}

handleReducedMotion();
initVideo();
form.addEventListener("submit", onSubmit);
