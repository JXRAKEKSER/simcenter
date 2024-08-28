window.print();

setTimeout(() => {
    location.href = document.body.dataset.redirectUrl;
}, 10_000);