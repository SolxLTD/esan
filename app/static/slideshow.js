(() => {
  const carousel = document.querySelector("[data-service-carousel]");
  if (!carousel) return;

  const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
  const indicators = Array.from(carousel.querySelectorAll("[data-carousel-indicator]"));
  const previous = carousel.querySelector("[data-carousel-previous]");
  const next = carousel.querySelector("[data-carousel-next]");

  if (slides.length < 2 || indicators.length !== slides.length || !previous || !next) {
    return;
  }

  let activeIndex = 0;
  let timer;

  const showSlide = (index) => {
    activeIndex = (index + slides.length) % slides.length;
    slides.forEach((slide, slideIndex) => {
      slide.hidden = slideIndex !== activeIndex;
      indicators[slideIndex].setAttribute(
        "aria-pressed",
        String(slideIndex === activeIndex),
      );
    });
  };

  const stop = () => {
    window.clearInterval(timer);
  };

  const start = () => {
    stop();
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      timer = window.setInterval(() => showSlide(activeIndex + 1), 5000);
    }
  };

  previous.addEventListener("click", () => {
    showSlide(activeIndex - 1);
    start();
  });
  next.addEventListener("click", () => {
    showSlide(activeIndex + 1);
    start();
  });
  indicators.forEach((indicator, index) => {
    indicator.addEventListener("click", () => {
      showSlide(index);
      start();
    });
  });

  carousel.addEventListener("mouseenter", stop);
  carousel.addEventListener("mouseleave", start);
  carousel.addEventListener("focusin", stop);
  carousel.addEventListener("focusout", (event) => {
    if (!carousel.contains(event.relatedTarget)) start();
  });

  showSlide(0);
  start();
})();
