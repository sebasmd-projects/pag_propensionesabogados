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

  document.querySelectorAll(".practice-card").forEach((card) => {
    card.addEventListener("click", function () {
      const subjectField = document.getElementById("contact_subject");

      if (subjectField) {
        subjectField.value = this.dataset.subject;
      }
    });
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
  // Misma historia: si algun dia una plantilla no trae el boton, que no se
  // caiga el resto del fichero.
  mobileNavToggleBtn?.addEventListener("click", mobileNavToogle);

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
    // Inicializar AOS apenas se cargue el DOM
    document.addEventListener("DOMContentLoaded", () => {
      AOS.init();
    });

    // Remover el preloader a los 1000ms como máximo
    const forceRemove = setTimeout(() => {
      if (preloader) preloader.remove();
    }, 3000);

    // Si la página carga antes, lo quitamos y cancelamos el timeout
    window.addEventListener("load", () => {
      if (preloader) preloader.remove();
      clearTimeout(forceRemove);
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
  // `scrollTop` no esta en todas las paginas --`terms-and-conditions` y
  // `privacy-policy` no lo traen--, y sin esta comprobacion la linea revienta
  // y se lleva por delante **todo lo que viene despues en este fichero**: el
  // menu movil, el scrollspy y la medida de la cabecera. La funcion de arriba
  // ya comprobaba `if (scrollTop)`; aqui faltaba.
  scrollTop?.addEventListener("click", (e) => {
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
    // El formulario de WhatsApp no esta en todas las paginas.
    sendMessageButton?.addEventListener("click", sendMessage);
    messageInput?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
      }
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    const whatsappButton = document.getElementById("whatsapp-button");

    function toggleWhatsappText() {
      // El boton flotante no esta en todas las paginas, y esto corre en cada
      // evento de scroll: sin la salida temprana era un error por cada pixel.
      if (!whatsappButton) {
        return;
      }
      whatsappButton.classList.toggle("scrolled", window.scrollY > 100);
    }

    // Escuchar eventos de scroll
    document.addEventListener("scroll", toggleWhatsappText);
    window.addEventListener("load", toggleWhatsappText);
  });

  /**
   * Animation on scroll function and init
   */
  function aosInit() {
    // AOS se carga solo en las paginas que lo declaran (la portada). En las
    // demas, `AOS` no existe y esto lanzaba un `ReferenceError`.
    if (typeof AOS === "undefined") {
      return;
    }
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

  /**
   * Publicar la altura real de la cabecera en `--header-height`.
   *
   * La cabecera es `fixed-top`, o sea que no ocupa sitio en el flujo, y las
   * paginas interiores se lo dejan con `.page-offset-header` (ver `main.css`).
   * Ese hueco tiene que valer exactamente lo que mide la cabecera, y lo que
   * mide depende de cosas que cambian solas: la tipografia --que viene de
   * Google Fonts y puede tardar, o no llegar--, el logo, el zoom del navegador
   * y si el menu se parte en dos lineas. Escribir el numero a mano acierta en
   * un sitio y falla en otro, y falla tapando el titulo.
   *
   * Medirlo quita la adivinanza. El CSS lleva un valor de reserva para antes
   * de que esto corra, asi que si el JavaScript falla la pagina se ve holgada,
   * no rota.
   */
  function publicarAlturaCabecera() {
    const cabecera = document.querySelector("#header");
    if (!cabecera) {
      return;
    }

    const aplicar = () => {
      const alto = Math.round(cabecera.getBoundingClientRect().height);
      if (alto > 0) {
        document.documentElement.style.setProperty(
          "--header-height",
          alto + "px"
        );
      }
    };

    aplicar();

    // Cuando la cabecera cambia de alto --la tipografia termina de cargar, se
    // gira el movil, se hace zoom, el menu se parte--, se vuelve a medir.
    //
    // `box: "border-box"` no es opcional: por defecto `ResizeObserver` mira
    // el `content-box`, y entonces un cambio en el relleno de la cabecera
    // --que si cambia lo que ocupa-- no dispara nada. Se vio probandolo.
    if (window.ResizeObserver) {
      new ResizeObserver(aplicar).observe(cabecera, { box: "border-box" });
    } else {
      window.addEventListener("resize", aplicar);
    }

    // `ResizeObserver` no existe en todos los navegadores viejos, y la carga
    // de una fuente no siempre dispara un cambio de tamano observable.
    window.addEventListener("load", aplicar);
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(aplicar);
    }
  }

  publicarAlturaCabecera();
})();
