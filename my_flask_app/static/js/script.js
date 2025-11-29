// تسجيل أي Click في الصفحة
document.addEventListener("click", function (event) {
    let action = "Clicked: " + event.target.tagName;
    fetch("/log_click", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ action: action })
    });
});
