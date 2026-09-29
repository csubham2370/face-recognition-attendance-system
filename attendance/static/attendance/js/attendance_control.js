$(document).ready(function () {
    const control = $("#attendanceControl");
    if (!control.length) return;

    const startButton = $("#startAttendanceButton");
    const stopButton = $("#stopAttendanceButton");
    const status = $("#attendanceStatus");
    const message = $("#attendanceControlMessage");

    function updateState(isOpen) {
        control.data("open", isOpen);
        status
            .removeClass("text-bg-success text-bg-danger")
            .addClass(isOpen ? "text-bg-success" : "text-bg-danger")
            .text(isOpen ? "Open" : "Closed");
        startButton.prop("disabled", isOpen);
        stopButton.prop("disabled", !isOpen);
    }

    function changeAttendance(action) {
        startButton.prop("disabled", true);
        stopButton.prop("disabled", true);
        $.ajax({
            url: control.data("url"),
            type: "POST",
            data: {
                action: action,
                csrfmiddlewaretoken: $("#csrfForm input[name=csrfmiddlewaretoken]").val(),
            },
            success: function (response) {
                updateState(response.is_open);
                message.removeClass().addClass("px-3 pb-3 alert alert-success mb-0").text(response.message);
            },
            error: function (xhr) {
                updateState(control.data("open") === true);
                message.removeClass().addClass("px-3 pb-3 alert alert-danger mb-0").text(xhr.responseJSON?.message || "Unable to change attendance status.");
            },
        });
    }

    startButton.click(function () { changeAttendance("start"); });
    stopButton.click(function () { changeAttendance("stop"); });
});
