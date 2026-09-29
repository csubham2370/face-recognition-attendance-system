$(document).ready(function () {

    $("#createAdminForm").submit(function (event) {

        event.preventDefault();


        let form = $("#createAdminForm");

        let createUrl = form.data("url");

        let button = $("#createAdminButton");


        button.prop("disabled", true).text("Creating...");


        $.ajax({

            url: createUrl,

            type: "POST",

            data: form.serialize(),


            success: function (response) {

                $("#adminMessage").removeClass().addClass("alert alert-success")
                    .text(response.message);

                form[0].reset();

                if (response.redirect_url) {
                    window.location.href = response.redirect_url;
                    return;
                }

                button.prop("disabled", false).text("Create Admin");

            },


            error: function (xhr) {

                let message = xhr.responseJSON?.message || "Unable to create admin.";

                $("#adminMessage").removeClass().addClass("alert alert-danger");


                if (typeof message === "object") {

                    let errorText = "";

                    for (let field in message) {

                        message[field].forEach(
                            function (error) {
                                errorText += error.message + " ";

                            }
                        );

                    }

                    $("#adminMessage").text(errorText);

                }

                else {

                    $("#adminMessage").text(message);

                }

                button.prop("disabled", false).text("Create Admin");

            }

        });

    });

});
