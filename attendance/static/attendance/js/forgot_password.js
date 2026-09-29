$(document).ready(function () {

    $("#forgotPasswordForm").submit(function (event) {

        event.preventDefault();


        let form = $("#forgotPasswordForm");

        let button = $("#forgotPasswordButton");

        let requestUrl = form.data("url");


        button.prop("disabled", true).text("Sending...");

        $.ajax({

            url: requestUrl,

            type: "POST",

            data: form.serialize(),


            success: function (response) {

                $("#forgotPasswordMessage").removeClass().addClass("alert alert-success")
                    .text(response.message);

                button.prop("disabled", false).text("Send Reset Link");

            },


            error: function (xhr) {

                let message = xhr.responseJSON?.message || "Unable to send reset email.";


                $("#forgotPasswordMessage").removeClass().addClass("alert alert-danger").text(message);

                button.prop("disabled", false).text("Send Reset Link");

            }

        });

    });

});