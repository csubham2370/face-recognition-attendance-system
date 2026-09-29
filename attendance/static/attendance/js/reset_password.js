$(document).ready(function () {
    $("#resetPasswordForm").submit(function (event) {
        event.preventDefault();

        let form = $(this);
        let button = $("#resetPasswordButton");

        button.prop("disabled", true).text("Resetting...");

        $.ajax({
            url: window.location.href,
            type: "POST",
            data: form.serialize(),
            success: function (response) {
                $("#resetPasswordMessage")
                    .removeClass()
                    .addClass("alert alert-success")
                    .text(response.message);
                form.remove();
            },
            error: function (xhr) {
                let message = xhr.responseJSON?.message || "Unable to reset password.";
                $("#resetPasswordMessage")
                    .removeClass()
                    .addClass("alert alert-danger")
                    .text(message);
                button.prop("disabled", false).text("Reset Password");
            }
        });
    });
});
