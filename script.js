let attempt = 0;
const maxAttempts = 30;

let keyEvents = [];
let startTime = null;

document.getElementById("password").addEventListener("keydown", (e) => {
    if (!startTime) startTime = performance.now();
    keyEvents.push({
        key: e.key,
        time: performance.now() - startTime,
        type: "down"
    });
});

document.getElementById("password").addEventListener("keyup", (e) => {
    keyEvents.push({
        key: e.key,
        time: performance.now() - startTime,
        type: "up"
    });
});

document.getElementById("collectForm").addEventListener("submit", (e) => {
    e.preventDefault();

    if (attempt >= maxAttempts) {
        document.getElementById("message").innerText = "All attempts completed.";
        return;
    }

    attempt++;
    document.getElementById("attemptCounter").innerText = `Attempt: ${attempt} / ${maxAttempts}`;

    const data = {
        user: document.getElementById("user").value,
        password: document.getElementById("password").value,
        attempt: attempt,
        events: keyEvents
    };

    console.log("Captured data:", data);

    // Reset for next round
    keyEvents = [];
    startTime = null;
    document.getElementById("password").value = "";
    document.getElementById("message").innerText = "Attempt saved!";
});
