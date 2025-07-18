document.addEventListener('DOMContentLoaded', () => {
    // Lógica para o menu de navegação móvel
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Desativa o botão de submissão para evitar múltiplos cliques
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                // Adiciona um pequeno delay para garantir que a validação do navegador ocorra
                setTimeout(() => {
                    submitButton.disabled = true;
                    submitButton.innerHTML = `A processar...`;
                }, 50);
            }
        });
    });
});