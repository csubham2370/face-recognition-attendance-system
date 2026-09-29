$(document).ready(function () {

    let video = document.getElementById("video");

    let canvas = document.getElementById("canvas");

    let context = canvas.getContext("2d");

    let cameraStream = null;

    const attendanceIsOpen = document.getElementById("studentAttendanceConfig").dataset.open === "true";
    if (!attendanceIsOpen) {
        $("#recognizeButton").prop("disabled", true).text("Attendance Closed");
        $("#recognitionMessage")
            .removeClass()
            .addClass("mt-3 alert alert-warning")
            .text("Attendance is currently closed. Please wait for an administrator to start it.");
        return;
    }

    function enableRecognition() {
        if (!cameraStream || !video.videoWidth || video.readyState < 2) return;
        $("#recognizeButton").prop("disabled", false).text("Recognize Face");
        $("#recognitionMessage")
            .removeClass()
            .addClass("mt-3 alert alert-success")
            .text("Camera is ready. Center your face and press Recognize Face.");
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        $("#recognitionMessage")
            .removeClass()
            .addClass("mt-3 alert alert-danger")
            .text("Camera access is not supported in this browser.");
        return;
    }

    video.addEventListener("loadedmetadata", enableRecognition);
    video.addEventListener("canplay", enableRecognition);

    navigator.mediaDevices.getUserMedia({ video: {facingMode: "user"}, audio: false})
    .then(function (stream) {

        cameraStream = stream;

        video.srcObject = stream;

        return video.play();

    })
    .then(function () {

        enableRecognition();

    })
    .catch(function (error) {

        console.error("Camera startup failed:", error);
        $("#recognitionMessage")
            .removeClass()
            .addClass("mt-3 alert alert-danger")
            .text("Unable to access camera. Allow camera permission and reload the page.");

    });

    $("#recognizeButton").click(function () {

        let button = $(this);

        let recognitionUrl = button.data("url");

        if (!cameraStream || video.readyState < 2 || !video.videoWidth) {
            $("#recognitionMessage")
                .removeClass()
                .addClass("mt-3 alert alert-warning")
                .text("The camera is not ready yet. Please wait and try again.");
            return;
        }

        canvas.width = video.videoWidth;

        canvas.height = video.videoHeight;


        context.drawImage(video,0,0,canvas.width,canvas.height);

        canvas.toBlob(function (blob) {

            if (!blob) {
                $("#recognitionMessage")
                    .removeClass()
                    .addClass("mt-3 alert alert-danger")
                    .text("Unable to capture a camera image. Please try again.");
                return;
            }

            let formData = new FormData();

            formData.append("image", blob,"student.jpg");


            formData.append("csrfmiddlewaretoken",
                $("input[name=csrfmiddlewaretoken]").val());

            button.prop("disabled", true).text("Recognizing...");

            function stopCamera() {

            if (cameraStream) {
        
                let tracks =
                    cameraStream.getTracks();
        
                tracks.forEach(function (track) {
        
                    track.stop();
        
                });

                video.pause();
        
                video.srcObject = null;
        
                cameraStream = null;
        
            }
        
        }        
            $.ajax({

                url: recognitionUrl,

                type: "POST",

                data: formData,

                processData: false,

                contentType: false,

                success: function (response) {

                    if (response.success) {

                        stopCamera();

                        $("#recognitionMessage")
                            .removeClass()
                            .addClass("mt-3 alert alert-success")
                            .text(response.attendance_message);

                        $(video).addClass("d-none");
                        $(canvas).addClass("d-none");
                        $("#cameraOffMessage").removeClass("d-none");

                        button
                            .prop("disabled", true)
                            .text("Attendance Completed");

                        $("#successStudentDetails")
                            .html(
                                "<strong>Name:</strong> " + response.name + "<br>" +
                                "<strong>Student ID:</strong> " + response.student_id + "<br>" +
                                "<strong>Confidence:</strong> " + response.confidence + "%<br>" +
                                "<strong>Date:</strong> " + response.date + "<br>" +
                                "<strong>Time:</strong> " + response.time
                            );

                        let successModal = new bootstrap.Modal(
                            document.getElementById("attendanceSuccessModal")
                        );

                        successModal.show();

                    } else {

                        $(canvas).addClass("d-none");
                        $(video).removeClass("d-none");

                        $("#recognitionMessage")
                            .removeClass()
                            .addClass(
                                "mt-3 alert alert-danger"
                            )
                            .text(
                                response.message
                            );

                        button
                            .prop("disabled", false)
                            .text("Recognize Face");
                    }

                },


                error: function (xhr) {

                    let message =
                        xhr.responseJSON?.message ||
                        "Recognition failed.";


                    $("#recognitionMessage")
                        .removeClass()
                        .addClass(
                            "mt-3 alert alert-danger"
                        )
                        .text(message);


                    button
                        .prop("disabled", false)
                        .text("Recognize Face");

                }

            });

        }, "image/jpeg");

    });

    window.addEventListener("beforeunload", function () {
        if (cameraStream) {
            cameraStream.getTracks().forEach(function (track) { track.stop(); });
        }
    });

});
