document.addEventListener("DOMContentLoaded", () => {
    const config = document.getElementById("captureConfig");
    const video = document.getElementById("captureCamera");
    const canvas = document.getElementById("captureCanvas");
    const startButton = document.getElementById("startFaceCapture");
    const stopButton = document.getElementById("stopFaceCapture");
    const progress = document.getElementById("captureProgress");
    const message = document.getElementById("captureMessage");
    const doneLink = document.getElementById("captureDone");
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
    const target = Number(config.dataset.target);
    let stream = null;
    let capturing = false;
    let firstImage = true;
    let attempts = 0;

    function showMessage(text, type) {
        message.className = `alert alert-${type}`;
        message.textContent = text;
    }

    function updateProgress(count) {
        const percentage = Math.min(100, (count / target) * 100);
        progress.style.width = `${percentage}%`;
        progress.textContent = `${count}/${target}`;
        progress.parentElement.setAttribute("aria-valuenow", count);
    }

    function stopCamera() {
        capturing = false;
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
        video.srcObject = null;
        startButton.disabled = false;
        stopButton.disabled = true;
    }

    async function uploadFrame() {
        if (!capturing) return;
        if (video.videoWidth === 0 || video.videoHeight === 0) {
            window.setTimeout(uploadFrame, 200);
            return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
        const formData = new FormData();
        formData.append("image", blob, "camera.jpg");
        if (firstImage) formData.append("reset", "true");

        try {
            const response = await fetch(config.dataset.url, {
                method: "POST",
                headers: {"X-CSRFToken": csrfToken},
                body: formData,
            });
            const result = await response.json();
            attempts += 1;
            if (result.success) {
                firstImage = false;
                updateProgress(result.captured_count);
                showMessage(result.complete ? result.message : `Capturing… ${result.captured_count}/${target}`, result.complete ? "success" : "primary");
                if (result.complete) {
                    stopCamera();
                    doneLink.classList.remove("d-none");
                    return;
                }
            } else {
                showMessage(result.message || "Face was not detected. Adjust your position.", "warning");
            }
        } catch (error) {
            showMessage("The image could not be uploaded. Check the server connection.", "danger");
            stopCamera();
            return;
        }

        if (attempts >= 180) {
            showMessage("Capture paused. Improve the lighting and try again.", "warning");
            stopCamera();
            return;
        }
        window.setTimeout(uploadFrame, 180);
    }

    startButton.addEventListener("click", async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "user"}, audio: false});
            video.srcObject = stream;
            capturing = true;
            firstImage = true;
            attempts = 0;
            startButton.disabled = true;
            stopButton.disabled = false;
            doneLink.classList.add("d-none");
            showMessage("Camera started. Keep your face centered.", "primary");
            await video.play();
            uploadFrame();
        } catch (error) {
            showMessage("Camera access was denied or no camera is available.", "danger");
        }
    });

    stopButton.addEventListener("click", () => {
        stopCamera();
        showMessage("Capture stopped. Press Start Capture to begin a new set.", "secondary");
    });
    window.addEventListener("beforeunload", stopCamera);
});
