document.addEventListener('DOMContentLoaded', function () {
    // Lógica para o menu de navegação mobile
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');
    const userMenu = document.querySelector('.user-menu');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            if (userMenu) {
                // Garante que o submenu do usuário não fique aberto ao fechar o nav
                userMenu.classList.remove('active');
            }
        });
    }

    // Lógica para o submenu do usuário no mobile
    if (userMenu) {
        const userMenuTrigger = userMenu.querySelector('.user-menu-trigger');
        userMenuTrigger.addEventListener('click', (event) => {
            // Previne que o clique feche o menu principal no mobile
            if (window.innerWidth <= 768) {
                event.preventDefault();
                userMenu.classList.toggle('active');
            }
        });
    }
});