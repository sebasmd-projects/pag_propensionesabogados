(function () {
  "use strict";

  /**
   * Don't display # in the URL when clicking on hash links
   */
  document.querySelectorAll('a[href*="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const href = this.getAttribute("href");
      const isSamePage =
        href.startsWith("#") ||
        new URL(href, window.location.origin).pathname ===
        window.location.pathname;

      if (isSamePage) {
        // Evitar el comportamiento por defecto y manejar navegación interna
        e.preventDefault();
        const targetID = href.split("#")[1];
        const targetElement = document.getElementById(targetID);

        if (targetElement) {
          window.scrollTo({
            top: targetElement.offsetTop,
            behavior: "smooth",
          });
        }

        // Actualizar la URL eliminando el hash
        const newURL = window.location.origin + window.location.pathname;
        window.history.pushState({}, "", newURL);
      } else {
        // Permitir la navegación a otras páginas (como Calendly)
        return;
      }
    });
  });

  /**
   * Set the value of the contact form subject field to the clicked service item
   */
  function setSubject(event) {
    const targetHref = event.target.getAttribute("href");
    if (!targetHref.includes("http") && !targetHref.includes("://")) {
      event.preventDefault();
      var subjectValue = event.target.innerText || event.target.textContent;
      var subjectField = document.getElementById("contact_subject");
      subjectField.value = subjectValue;
    }
  }
  document.querySelectorAll(".service-item a").forEach(function (link) {
    link.addEventListener("click", setSubject);
  });

  /**
   * Apply .scrolled class to the body as the page is scrolled down
   */
  function toggleScrolled() {
    const selectBody = document.querySelector("body");
    const selectHeader = document.querySelector("#header");

    if (
      !selectHeader.classList.contains("scroll-up-sticky") &&
      !selectHeader.classList.contains("sticky-top") &&
      !selectHeader.classList.contains("fixed-top")
    ) {
      return;
    }

    // Agregar clase 'scrolled' si el path no es '/'
    if (window.location.pathname !== "/") {
      selectBody.classList.add("scrolled");
    } else {
      window.scrollY > 100
        ? selectBody.classList.add("scrolled")
        : selectBody.classList.remove("scrolled");
    }
  }

  document.addEventListener("scroll", toggleScrolled);
  window.addEventListener("load", toggleScrolled);

  /**
   * Mobile nav toggle
   */
  const mobileNavToggleBtn = document.querySelector(".mobile-nav-toggle");

  function mobileNavToogle() {
    document.querySelector("body").classList.toggle("mobile-nav-active");
    mobileNavToggleBtn.classList.toggle("bi-list");
    mobileNavToggleBtn.classList.toggle("bi-x");
  }
  mobileNavToggleBtn.addEventListener("click", mobileNavToogle);

  /**
   * Hide mobile nav on same-page/hash links
   */
  document.querySelectorAll("#navmenu a").forEach((navmenu) => {
    navmenu.addEventListener("click", () => {
      if (document.querySelector(".mobile-nav-active")) {
        mobileNavToogle();
      }
    });
  });

  /**
   * Toggle mobile nav dropdowns
   */
  document.querySelectorAll(".navmenu .toggle-dropdown").forEach((navmenu) => {
    navmenu.addEventListener("click", function (e) {
      e.preventDefault();
      this.parentNode.classList.toggle("active");
      this.parentNode.nextElementSibling.classList.toggle("dropdown-active");
      e.stopImmediatePropagation();
    });
  });

  /**
   * Preloader
   */
  const preloader = document.querySelector("#preloader");
  if (preloader) {
    window.addEventListener("load", () => {
      preloader.remove();
    });
  }

  /**
   * Scroll top button
   */
  let scrollTop = document.querySelector(".scroll-top");

  function toggleScrollTop() {
    if (scrollTop) {
      window.scrollY > 100
        ? scrollTop.classList.add("active")
        : scrollTop.classList.remove("active");
    }
  }
  scrollTop.addEventListener("click", (e) => {
    e.preventDefault();
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  });

  window.addEventListener("load", toggleScrollTop);
  document.addEventListener("scroll", toggleScrollTop);

  /**
   * WhatsApp Chat Button
   */

  document.addEventListener("DOMContentLoaded", () => {
    const sendMessageButton = document.getElementById("sendMessage");
    const messageInput = document.getElementById("messageInput");

    const sendMessage = () => {
      const message = messageInput.value.trim();

      if (message) {
        const phoneNumber = "573012283818";
        const whatsappURL = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(
          message
        )}`;
        window.open(whatsappURL, "_blank");
        messageInput.value = "";
      } else {
        alert("Por favor, escribe un mensaje antes de enviarlo.");
      }
    };
    sendMessageButton.addEventListener("click", sendMessage);
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
      }
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    const whatsappButton = document.getElementById("whatsapp-button");

    function toggleWhatsappText() {
      if (window.scrollY > 100) {
        whatsappButton.classList.add("scrolled");
      } else {
        whatsappButton.classList.remove("scrolled");
      }
    }

    // Escuchar eventos de scroll
    document.addEventListener("scroll", toggleWhatsappText);
    window.addEventListener("load", toggleWhatsappText);
  });

  /**
   * Animation on scroll function and init
   */
  function aosInit() {
    AOS.init({
      duration: 600,
      easing: "ease-in-out",
      once: true,
      mirror: false,
    });
  }
  window.addEventListener("load", aosInit);

  /**
   * Frequently Asked Questions Toggle
   */
  document
    .querySelectorAll(".faq-item h3, .faq-item .faq-toggle")
    .forEach((faqItem) => {
      faqItem.addEventListener("click", () => {
        faqItem.parentNode.classList.toggle("faq-active");
      });
    });

  /**
   * Init swiper sliders
   */
  function initSwiper() {
    document.querySelectorAll(".init-swiper").forEach(function (swiperElement) {
      let config = JSON.parse(
        swiperElement.querySelector(".swiper-config").innerHTML.trim()
      );

      if (swiperElement.classList.contains("swiper-tab")) {
        initSwiperWithCustomPagination(swiperElement, config);
      } else {
        new Swiper(swiperElement, config);
      }
    });
  }

  window.addEventListener("load", initSwiper);

  /**
   * Correct scrolling position upon page load for URLs containing hash links.
   */
  window.addEventListener("load", function (e) {
    if (window.location.hash) {
      if (document.querySelector(window.location.hash)) {
        setTimeout(() => {
          let section = document.querySelector(window.location.hash);
          let scrollMarginTop = getComputedStyle(section).scrollMarginTop;
          window.scrollTo({
            top: section.offsetTop - parseInt(scrollMarginTop),
            behavior: "smooth",
          });
        }, 100);
      }
    }
  });

  /**
   * Navmenu Scrollspy
   */
  let navmenulinks = document.querySelectorAll(".navmenu a");

  function navmenuScrollspy() {
    navmenulinks.forEach((navmenulink) => {
      if (!navmenulink.hash) return;
      let section = document.querySelector(navmenulink.hash);
      if (!section) return;
      let position = window.scrollY + 200;
      if (
        position >= section.offsetTop &&
        position <= section.offsetTop + section.offsetHeight
      ) {
        document
          .querySelectorAll(".navmenu a.active")
          .forEach((link) => link.classList.remove("active"));
        navmenulink.classList.add("active");
      } else {
        navmenulink.classList.remove("active");
      }
    });
  }
  window.addEventListener("load", navmenuScrollspy);
  document.addEventListener("scroll", navmenuScrollspy);
})();
