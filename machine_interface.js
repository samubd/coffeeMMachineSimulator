document.addEventListener('DOMContentLoaded', () => {
    const groups = document.querySelectorAll('.group');

    groups.forEach((group, groupIndex) => {
        const display = group.querySelector('.center-display span');
        const buttons = group.querySelectorAll('.button');
        let timerInterval;
        let seconds = 0;

        buttons.forEach(button => {
            button.addEventListener('click', () => {
                const buttonId = button.textContent;

                if (timerInterval) {
                    clearInterval(timerInterval);
                }

                seconds = 0;
                display.textContent = `${buttonId}: ${seconds}sec`;

                timerInterval = setInterval(() => {
                    seconds++;
                    display.textContent = `${buttonId}: ${seconds}sec`;
                }, 1000);
            });
        });
    });
});
