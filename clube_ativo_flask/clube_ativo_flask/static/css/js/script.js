// Imprime uma mensagem na consola do navegador para confirmar que o ficheiro foi carregado
console.log("Clube Ativo: JavaScript carregado com sucesso!");

// Exemplo de interatividade: Desativa o botão de submissão para evitar múltiplos cliques
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerText = 'A processar...';
            }
        });
    });
});