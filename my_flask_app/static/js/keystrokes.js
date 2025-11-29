let pressTimes = {};
let lastReleaseTime = null;

const input = document.getElementById("password");

input.addEventListener("keydown", e => {
    let code = e.code;
    pressTimes[code] = performance.now();
});

input.addEventListener("keyup", e => {
    let code = e.code;

    const release = performance.now();
    const press = pressTimes[code] || release;

    const dwell = release - press;
    const flight = lastReleaseTime ? press - lastReleaseTime : null;

    lastReleaseTime = release;

    // Only send during TRAINING
    sendKeystroke(dwell, flight);

    delete pressTimes[code];
});

function sendKeystroke(dwell, flight) {
    fetch("/log_keystroke", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ dwell, flight })
    })
    .catch(err => console.error(err));
}
