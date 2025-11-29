let pressTimes = {};
let strokes = [];
let attempt = 0;
let lastReleaseTime = null;

const pwd = document.getElementById("password");
const counter = document.getElementById("attemptCounter");
const message = document.getElementById("message");
const goTraining = document.getElementById("goTraining");

// تسجيل أزمنة الضغط
pwd.addEventListener("keydown", e => {
    const key = e.key;
    if (!pressTimes[key]) {
        pressTimes[key] = performance.now();
    }
});

pwd.addEventListener("keyup", e => {
    const key = e.key;
    const release = performance.now();
    const press = pressTimes[key] || release;
    const dwell = release - press;
    let flight = null;

    if (lastReleaseTime !== null) {
        flight = press - lastReleaseTime;
    }
    lastReleaseTime = release;

    // نسجل الحروف الفعلية فقط
    if (key.length === 1) {
        strokes.push({
            key: key,
            press: press,
            release: release,
            dwell: dwell,
            flight: flight
        });
    }

    delete pressTimes[key];
});

document.getElementById("collectForm").addEventListener("submit", e => {
    e.preventDefault();

    if (pwd.value !== "pass") {
        message.innerHTML = "<b style='color:red'>Password must be exactly: pass</b>";
        return;
    }

    fetch("/save_keystrokes", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(strokes)
    })
    .then(r => r.json())
    .then(data => {
        attempt++;
        counter.innerText = `Attempt: ${attempt} / 30`;
        message.innerHTML = "<span style='color:green'>Attempt saved</span>";
        strokes = [];
        pwd.value = "";
        lastReleaseTime = null;

        if (attempt >= 30) {
            message.innerHTML = "<b style='color:blue'>You collected enough data. Go to Training page.</b>";
            if (goTraining) {
                goTraining.style.display = "block";
            }
            document.getElementById("send").disabled = true;
        }
    })
    .catch(err => {
        console.error(err);
        message.innerHTML = "<b style='color:red'>Error while saving attempt</b>";
    });
});
