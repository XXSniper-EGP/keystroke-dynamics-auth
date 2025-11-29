let pressTimes = {};
let samples = [];
let lastRelease = null;
let attempts = 0; // عدد مرات كتابة pass في جلسة التحقق

const input = document.getElementById("verifyInput");
const result = document.getElementById("result");

// تسجيل keystrokes
input.addEventListener("keydown", e => {
    const key = e.key;
    if (!pressTimes[key]) {
        pressTimes[key] = performance.now();
    }
});

input.addEventListener("keyup", e => {
    const key = e.key;
    const release = performance.now();
    const press = pressTimes[key] || release;
    const dwell = release - press;
    let flight = null;

    if (lastRelease !== null) {
        flight = press - lastRelease;
    }

    lastRelease = release;

    if (key.length === 1) {
        // نحفظ فقط [dwell, flight] زي ما model.py متوقع
        samples.push([dwell, flight]);
    }

    delete pressTimes[key];

    // تشغيل التحقق عند ضغط Enter
    if (e.key === "Enter") {
        document.getElementById("verifyBtn").click();
    }
});

// عند الضغط على زر Verify
document.getElementById("verifyBtn").addEventListener("click", () => {
    if (input.value !== "pass") {
        result.innerHTML = "<b style='color:red'>Password must be exactly: pass</b>";
        return;
    }

    attempts += 1;
    input.value = "";

    // لسه محتاج يكتب تاني
    if (attempts < 3) {
        const left = 3 - attempts;
        result.innerHTML = "<b>Type it again (" + left + " left)...</b>";
        return;
    }

    // هنا كتب pass 3 مرات → نبعث كل العينات مرة واحدة
    fetch("/verify_ml", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ samples: samples })
    })
    .then(r => r.json())
    .then(res => {
        if (res.valid) {
            result.innerHTML = "<b style='color:green'>User Verified ✔</b>";
        } else {
            result.innerHTML = "<b style='color:red'>Verification Failed ✖</b>";
        }
        // reset
        samples = [];
        attempts = 0;
        input.value = "";
        lastRelease = null;
    })
    .catch(err => {
        console.error(err);
        result.innerHTML = "<b style='color:red'>Error during verification</b>";
        samples = [];
        attempts = 0;
        input.value = "";
        lastRelease = null;
    });
});
