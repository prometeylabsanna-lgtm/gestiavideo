/* ========== Config ========== */
const FORM_ENDPOINT = ""; // TODO: set email collection endpoint (POST JSON {email}). Empty = no backend, only local success message.
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

function setStatus(message, isError) {
  statusEl.textContent = message;
  statusEl.classList.toggle("hero__status--error", Boolean(isError));
}

function clearStatus() {
  statusEl.textContent = "";
  statusEl.classList.remove("hero__status--error");
}

function handleReducedMotion() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce || !video) return;

  hero.classList.add("hero--reduced-motion");
  video.pause();
  video.removeAttribute("autoplay");
  video.remove();
}

function handleVideoFallback() {
  if (!video || hero.classList.contains("hero--reduced-motion")) return;

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
    return;
  }

  emailInput.setAttribute("aria-invalid", "false");
  submitBtn.disabled = true;

  try {
    if (FORM_ENDPOINT) {
      const res = await fetch(FORM_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        setStatus(FAIL_MSG, true);
        return;
      }
    } else {
      console.info(
        "[Gestia Home] FORM_ENDPOINT is empty — email not sent anywhere:",
        email
      );
    }

    setStatus(SUCCESS_MSG, false);
    form.reset();
  } catch {
    setStatus(FAIL_MSG, true);
  } finally {
    submitBtn.disabled = false;
  }
}

handleReducedMotion();
handleVideoFallback();
form.addEventListener("submit", onSubmit);
