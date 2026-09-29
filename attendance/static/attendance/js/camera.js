$(document).ready(function () {

    let cameraStream = null;
    const video = document.getElementById("camera");

    // Start camera
    $("#startCamera").click(async function () {
        try {

            cameraStream = await navigator.mediaDevices.getUserMedia({video: true,audio: false});
            video.srcObject =cameraStream;

            $("#startCamera").prop("disabled",true);
            $("#stopCamera").prop("disabled",false);
            $("#recognizeFace").prop("disabled",false);
            $("#result").html(`
                <div class="alert alert-success">
                    Camera started successfully.
                </div>
            `);
        }

        catch (error) {
            console.log(error);
            $("#result").html(`
                <div class="alert alert-danger">
                    Unable to access camera.
                </div>
            `);
        }

    });

    // Stop camera
    $("#stopCamera").click(function () {
        if (cameraStream) {
            cameraStream.getTracks().forEach(function (track) {
                    track.stop();
                });}

        video.srcObject = null;
        cameraStream = null;
        $("#startCamera").prop("disabled",false);
        $("#stopCamera").prop("disabled",true);
        $("#recognizeFace").prop("disabled",true);
        $("#result").html(`
            <div class="alert alert-warning">
                Camera stopped.
            </div>
        `);

    });

});