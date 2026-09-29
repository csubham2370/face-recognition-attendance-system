$(document).ready(function () {

    $("#recognizeFace").click(function (event) {

        // Prevent normal page reload
        event.preventDefault();
        const video = document.getElementById("camera");
        const canvas = document.getElementById("canvas");
        const context = canvas.getContext("2d");

        // -------------------------
        // Check webcam
        // -------------------------

        if (!video.srcObject) {
            $("#result").html(`
                <div class="alert alert-warning">
                    Please start the camera first.
                </div>
            `);

            return;
        }
        // -------------------------
        // Canvas dimensions
        // -------------------------

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        // -------------------------
        // Capture webcam image
        // -------------------------
        context.drawImage(video,0,0,canvas.width,canvas.height);
        $("#result").html(`
            <div class="alert alert-info">
                Recognizing face...
            </div>
        `);

        // -------------------------
        // Convert canvas to image
        // -------------------------

        canvas.toBlob(
            function (blob) {
                if (!blob) {
                    $("#result").html(`
                        <div class="alert alert-danger">
                            Unable to capture image.
                        </div>
                    `);

                    return;
                }
                // -------------------------
                // FormData
                // -------------------------
                let formData = new FormData();
                formData.append("image",blob,"capture.jpg");
                // -------------------------
                // CSRF Token
                // -------------------------

                let csrfToken = $("input[name='csrfmiddlewaretoken']").val();
                // -------------------------
                // Django URL
                // -------------------------

                let url = $("#recognizeFace").data("url");
                // -------------------------
                // jQuery AJAX
                // -------------------------

                $.ajax({
                    url: url,
                    type: "POST",
                    data: formData,
                    processData: false,
                    contentType: false,
                    headers: {"X-CSRFToken":csrfToken},
                    beforeSend: function () {
                        $("#recognizeFace").prop("disabled",true);
                        $("#result").html(`
                            <div class="alert alert-info">
                                Please wait...
                                Face recognition is running.
                            </div>
                        `);
                    },

                    success: function (response) {
                        if (response.success) {
                            let attendanceClass = response.attendance_created ? "alert-success" : "alert-warning";


                    $("#result").html(`
                    <div class="alert ${attendanceClass}">
                        <h4 class="alert-heading">Student Recognized</h4>
                        <hr>
                        <p><strong>Name:</strong> ${response.name}</p>
                        <p><strong>Student ID:</strong>${response.student_id}</p>
                        <p><strong>Email:</strong>${response.email}</p>
                        <p><strong>Confidence:</strong>${response.confidence}%</p>
                        <p><strong>Date:</strong>${response.date}</p>
                        <p><strong>Time:</strong>${response.time}</p>
                        <hr>
                        <strong>${response.attendance_message}</strong>
                    </div>
                
                `);
                        }
                        else 
                            {
                            let confidence = "";
                            if (response.confidence !== undefined) {
                                confidence = `
                                    <p class="mb-0">Confidence:
                                        ${Number(response.confidence).toFixed(2)}%</p>

                                `;
                            }

                            $("#result").html(`
                                <div class="alert alert-warning">
                                    <h5>${response.message}</h5>${confidence}</div>

                            `);

                        }},

                    error: function (xhr) {
                        console.log(xhr.responseText);
                        $("#result").html(`
                            <div class="alert alert-danger">
                                Something went wrong
                                during face recognition.
                            </div> `);
                    },
                    complete: function () {
                        if (video.srcObject) {
                            $("#recognizeFace").prop("disabled", false );
                        }
                    }
                });
            },

            "image/jpeg",0.9

        );

    });

});
